"""
Language Model (LLM) Service
Generates responses to user queries using Gemini API with Ollama fallback
Includes intelligent response caching with TTL-based expiration.
"""

import time
import os
from typing import List, Optional, Dict, Any

# Gemini API import
try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# Ollama import
try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

from ..core.config import Config
from ..models.intent import Intent, IntentType
from ..models.conversation_context import ConversationContext
from ..utils.logger import EventLogger, MetricsLogger
from ..agents.tools import ToolRegistry, create_default_registry
from .llm_cache import get_llm_cache, LLMCache


class LLMService:
    """
    Language Model service with hybrid architecture
    Primary: Gemini API
    Fallback: Ollama (local)
    """

    def __init__(
        self,
        config: Config,
        logger: EventLogger,
        metrics_logger: MetricsLogger
    ):
        self.config = config
        self.logger = logger
        self.metrics_logger = metrics_logger
        self.mode = config.llm.primary_mode

        # Initialize Gemini API
        self.gemini_client = None
        if GEMINI_AVAILABLE and config.gemini_api_key and self.mode in ["api", "hybrid"]:
            self.gemini_client = genai.Client(api_key=config.gemini_api_key)

        # Ollama is initialized per-request (no persistent connection needed)
        self.ollama_available = OLLAMA_AVAILABLE and self.mode in ["local", "hybrid"]

        # Initialize LLM response cache with configurable settings
        cache_ttl = int(os.environ.get("LLM_CACHE_TTL", "1800"))  # 30 min default
        cache_enabled = os.environ.get("LLM_CACHE_ENABLED", "true").lower() == "true"
        use_redis = os.environ.get("LLM_CACHE_REDIS", "false").lower() == "true"

        self.cache: Optional[LLMCache] = None
        if cache_enabled:
            try:
                self.cache = get_llm_cache(ttl_seconds=cache_ttl, use_redis=use_redis)
                self.logger.info(
                    event='LLM_CACHE_INITIALIZED',
                    message=f'LLM cache enabled (TTL={cache_ttl}s, Redis={use_redis})'
                )
            except Exception as e:
                self.logger.warning(
                    event='LLM_CACHE_INIT_FAILED',
                    message=f'Failed to initialize LLM cache: {e}'
                )
                self.cache = None

        # Initialize tool registry for function calling
        self.tool_registry = create_default_registry()
        self.logger.info(
            event='TOOL_REGISTRY_INITIALIZED',
            message=f'Loaded {len(self.tool_registry._tools)} tools for function calling'
        )

    def is_ready(self) -> bool:
        """Check if the LLM service is ready to generate responses"""
        if self.mode in ["api", "hybrid"]:
            return self.gemini_client is not None
        elif self.mode == "local":
            return OLLAMA_AVAILABLE
        return False

    def generate_response(
        self,
        query: str,
        intent: Optional[Intent] = None,
        context: Optional[ConversationContext] = None
    ) -> str:
        """
        Generate response to user query with intelligent caching.

        Returns: Generated response text
        """
        if not query or len(query.strip()) == 0:
            raise ValueError("Query must not be empty")

        start_time = time.time()
        response_text = ""
        success = False
        mode_used = self.mode
        from_cache = False

        try:
            # Check cache first if enabled
            if self.cache:
                context_str = None
                if context and context.exchanges:
                    # Use last exchange as context for cache key
                    context_str = "|".join([
                        f"{e.user_input}:{e.assistant_response}"
                        for e in context.exchanges[-2:]  # Last 2 exchanges
                    ])

                intent_str = intent.intent_type.value if intent else None
                cached_response = self.cache.get(query, context_str, intent_str)

                if cached_response:
                    response_text = cached_response
                    from_cache = True
                    mode_used = "cache"
                    success = True
                    self.logger.info(
                        event='LLM_CACHE_HIT',
                        message=f'Cache hit for query: "{query[:50]}..."'
                    )
                    self.metrics_logger.record_metric('llm_cache_hit', 1)
                    # Skip to finally block to log metrics
                    return response_text

            # Cache miss or disabled - build prompt with context
            full_prompt = self._build_prompt(query, intent, context)

            if self.mode == "api":
                response_text = self._generate_api(full_prompt)
                mode_used = "api"
                success = True
            elif self.mode == "local":
                response_text = self._generate_local(full_prompt)
                mode_used = "local"
                success = True
            else:  # hybrid mode
                try:
                    response_text = self._generate_api(full_prompt)
                    mode_used = "api"
                    success = True
                except Exception as api_error:
                    self.logger.warning(
                        event='LLM_API_FALLBACK',
                        message=f'API LLM failed, falling back to local: {str(api_error)}'
                    )
                    response_text = self._generate_local(full_prompt)
                    mode_used = "local"
                    success = True

        except Exception as e:
            self.logger.error(
                event='LLM_GENERATION_FAILED',
                message=f'LLM response generation failed: {str(e)}',
                error=str(e)
            )
            raise

        finally:
            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)

            # Cache the response if it was generated (not from cache)
            if not from_cache and success and response_text and self.cache:
                try:
                    context_str = None
                    if context and context.exchanges:
                        context_str = "|".join([
                            f"{e.user_input}:{e.assistant_response}"
                            for e in context.exchanges[-2:]
                        ])

                    intent_str = intent.intent_type.value if intent else None
                    metadata = {
                        "mode": mode_used,
                        "query_length": len(query),
                        "response_length": len(response_text),
                        "generation_time_ms": duration_ms
                    }

                    self.cache.set(query, response_text, context_str, intent_str, metadata)
                    self.logger.debug(
                        event='LLM_CACHE_STORED',
                        message=f'Response cached for query: "{query[:50]}..."'
                    )
                    self.metrics_logger.record_metric('llm_cache_miss', 1)
                except Exception as cache_error:
                    self.logger.warning(
                        event='LLM_CACHE_STORE_FAILED',
                        message=f'Failed to cache response: {cache_error}'
                    )

            # Log event
            log_event = 'LLM_CACHE_HIT' if from_cache else 'LLM_RESPONSE_GENERATED'
            self.logger.info(
                event=log_event,
                message=f'Response {"retrieved from cache" if from_cache else "generated"}: "{response_text[:50]}..."',
                query_length=len(query),
                response_length=len(response_text),
                processing_time_ms=duration_ms,
                mode=mode_used,
                intent_type=intent.intent_type.value if intent else None,
                success=success,
                from_cache=from_cache
            )

            # Record metrics
            metric_key = 'llm_cache_latency_ms' if from_cache else 'llm_latency_ms'
            self.metrics_logger.record_metric(metric_key, duration_ms)
            self.metrics_logger.record_metric('llm_response_length', len(response_text))

        return response_text

    def _build_prompt(
        self,
        query: str,
        intent: Optional[Intent] = None,
        context: Optional[ConversationContext] = None
    ) -> str:
        """Build complete prompt with system instructions and context"""
        prompt_parts = []

        # System prompt
        prompt_parts.append(self.config.llm.system_prompt)
        prompt_parts.append("")  # Blank line

        # Add context if available
        if context and context.exchanges:
            prompt_parts.append("Previous conversation:")
            for exchange in context.exchanges[-3:]:  # Last 3 exchanges
                prompt_parts.append(f"User: {exchange.user_input}")
                prompt_parts.append(f"Assistant: {exchange.assistant_response}")
            prompt_parts.append("")  # Blank line

        # Add intent type guidance
        if intent:
            if intent.intent_type == IntentType.INFORMATIONAL:
                prompt_parts.append("This is an informational query. Provide factual, concise information.")
            elif intent.intent_type == IntentType.TASK_BASED:
                prompt_parts.append("This is a task request. Confirm the action you'll take.")
            elif intent.intent_type == IntentType.CONVERSATIONAL:
                prompt_parts.append("This is casual conversation. Be friendly and engaging.")
            prompt_parts.append("")  # Blank line

        # Current query
        prompt_parts.append(f"User: {query}")
        prompt_parts.append("Assistant:")

        return "\n".join(prompt_parts)

    def _tools_to_gemini_format(self) -> List[types.Tool]:
        """Convert tool registry tools to Gemini function declarations"""
        tools_list = []

        for tool in self.tool_registry._tools.values():
            desc = tool.get_description()

            # Build properties with proper handling of array types
            properties = {}
            for param in desc.parameters:
                prop = {
                    "type": param.type,
                    "description": param.description
                }

                # For array types, add items field (required by Gemini API)
                if param.type == "array" and hasattr(param, 'items_type') and param.items_type:
                    prop["items"] = {
                        "type": param.items_type
                    }

                properties[param.name] = prop

            # Build function declaration
            function_declaration = types.FunctionDeclaration(
                name=desc.name,
                description=desc.description,
                parameters={
                    "type": "object",
                    "properties": properties,
                    "required": [p.name for p in desc.parameters if p.required]
                }
            )

            tools_list.append(types.Tool(function_declarations=[function_declaration]))

        return tools_list

    def _execute_tool(self, function_name: str, arguments: Dict[str, Any]) -> str:
        """Execute a tool and return result as string"""
        tool = self.tool_registry.get(function_name)
        if not tool:
            return f"Error: Tool '{function_name}' not found"

        try:
            result = tool.execute(arguments)
            if result.success:
                return str(result.data) if result.data else "Action completed successfully"
            else:
                return f"Error: {result.error}"
        except Exception as e:
            return f"Error executing {function_name}: {str(e)}"

    def _generate_api(self, prompt: str) -> str:
        """Generate response using Gemini API with function calling"""
        if not GEMINI_AVAILABLE:
            raise RuntimeError("Gemini library not available")

        if self.gemini_client is None:
            raise RuntimeError("Gemini client not initialized (check API key)")

        try:
            # Get tools in Gemini format
            gemini_tools = self._tools_to_gemini_format()

            # Generate response with tools
            response = self.gemini_client.models.generate_content(
                model=self.config.llm.api_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=self.config.llm.temperature,
                    max_output_tokens=self.config.llm.max_tokens,
                    tools=gemini_tools
                )
            )

            # Check if there are function calls
            if hasattr(response, 'candidates') and len(response.candidates) > 0:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                    for part in candidate.content.parts:
                        if hasattr(part, 'function_call') and part.function_call:
                            # Execute the function call
                            function_name = part.function_call.name
                            function_args = dict(part.function_call.args) if part.function_call.args else {}

                            self.logger.info(
                                event='TOOL_CALLED',
                                message=f'Executing tool: {function_name}',
                                function_name=function_name,
                                arguments=function_args
                            )

                            # Execute tool
                            tool_result = self._execute_tool(function_name, function_args)

                            # Call Gemini again with the function result
                            response = self.gemini_client.models.generate_content(
                                model=self.config.llm.api_model,
                                contents=[
                                    {"role": "user", "parts": [{"text": prompt}]},
                                    {"role": "model", "parts": [{"function_call": part.function_call}]},
                                    {"role": "function", "parts": [{"function_response": {
                                        "name": function_name,
                                        "response": {"result": tool_result}
                                    }}]}
                                ],
                                config=types.GenerateContentConfig(
                                    temperature=self.config.llm.temperature,
                                    max_output_tokens=self.config.llm.max_tokens,
                                )
                            )

            # Extract text from final response
            if response.text:
                return response.text.strip()
            else:
                # Handle safety filters or empty responses
                self.logger.warning(
                    event='LLM_EMPTY_RESPONSE',
                    message='Gemini returned empty response (possibly filtered)',
                    finish_reason=getattr(response, 'finish_reason', 'unknown')
                )
                return "I'm sorry, I couldn't generate a response to that."

        except Exception as e:
            raise RuntimeError(f"Gemini API error: {str(e)}")

    def _generate_local(self, prompt: str) -> str:
        """Generate response using Ollama (local)"""
        if not OLLAMA_AVAILABLE:
            raise RuntimeError("Ollama library not available")

        try:
            # Generate response with Ollama
            response = ollama.chat(
                model=self.config.llm.local_model,
                messages=[
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                options={
                    'temperature': self.config.llm.temperature,
                    'num_predict': self.config.llm.max_tokens,
                }
            )

            # Extract message from response
            if 'message' in response and 'content' in response['message']:
                return response['message']['content'].strip()
            else:
                self.logger.warning(
                    event='LLM_EMPTY_RESPONSE',
                    message='Ollama returned empty or malformed response'
                )
                return "I'm sorry, I couldn't generate a response to that."

        except Exception as e:
            raise RuntimeError(f"Ollama error: {str(e)}")

    def generate_confirmation(self, action_description: str) -> str:
        """Generate confirmation message for task execution"""
        prompt = f"{self.config.llm.system_prompt}\n\nGenerate a brief confirmation (1 sentence) for this action: {action_description}"

        try:
            if self.mode in ["api", "hybrid"] and self.gemini_client:
                return self._generate_api(prompt)
            else:
                return self._generate_local(prompt)
        except Exception as e:
            # Fallback to simple template
            self.logger.warning(
                event='LLM_CONFIRMATION_FALLBACK',
                message=f'Using template confirmation due to error: {str(e)}'
            )
            return f"I'll {action_description}."

    def generate_summarized_response(
        self,
        query: str,
        tool_name: str,
        tool_result: Any,
        context: Optional[ConversationContext] = None
    ) -> str:
        """
        Generate a natural language summary of a tool execution result.
        """
        prompt = f"""You are a helpful voice assistant. 
The user asked: "{query}"
You executed the tool "{tool_name}" and got this result: {str(tool_result)}

Based on this result, provide a helpful, natural, and detailed response to the user.
If the tool was successful, explain what was done or provide the information requested.
If there was an error, explain it politely.
Do not just repeat the raw data; speak like a human.
"""
        try:
            if self.mode in ["api", "hybrid"] and self.gemini_client:
                # Use simplified API call for summary
                response = self.gemini_client.models.generate_content(
                    model=self.config.llm.api_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.7,
                        max_output_tokens=self.config.llm.max_tokens,
                    )
                )
                return response.text.strip() if response.text else "I've completed the action."
            else:
                return self._generate_local(prompt)
        except Exception as e:
            self.logger.error(event='SUMMARY_GENERATION_FAILED', message=str(e))
            return f"I've executed the {tool_name} tool. The result is: {str(tool_result)}"

    def test_service(self) -> bool:
        """Test LLM service with a simple query"""
        try:
            test_query = "What is 2 plus 2?"
            response = self.generate_response(test_query)

            self.logger.info(
                event='LLM_TEST_COMPLETED',
                message=f'LLM service test completed: "{response}"'
            )

            return True

        except Exception as e:
            self.logger.error(
                event='LLM_TEST_FAILED',
                message=f'LLM service test failed: {str(e)}',
                error=str(e)
            )
            return False

    # ============================================================================
    # Streaming Response Support (Phase 2B)
    # ============================================================================

    def generate_response_stream(
        self,
        query: str,
        intent: Optional[Intent] = None,
        context: Optional[ConversationContext] = None
    ):
        """
        Generate streaming response using generator pattern.
        Yields text chunks as they are generated by the LLM.

        This reduces perceived latency by sending first token in 200-500ms
        instead of waiting 2-5s for complete response.

        Args:
            query: User query
            intent: Optional detected intent
            context: Optional conversation context

        Yields:
            Text chunks as they are generated by the LLM
        """
        if not query or len(query.strip()) == 0:
            raise ValueError("Query must not be empty")

        # Check cache first - if cached, return full response at once
        if self.cache:
            try:
                context_str = None
                if context and context.exchanges:
                    context_str = "|".join([
                        f"{e.user_input}:{e.assistant_response}"
                        for e in context.exchanges[-2:]
                    ])

                intent_str = intent.intent_type.value if intent else None
                cached_response = self.cache.get(query, context_str, intent_str)

                if cached_response:
                    # Yield cached response as one chunk
                    self.logger.info(
                        event='LLM_STREAM_CACHE_HIT',
                        message=f'Stream cache hit for query: "{query[:50]}..."'
                    )
                    self.metrics_logger.record_metric('llm_stream_cache_hit', 1)
                    yield cached_response
                    return
            except Exception as e:
                self.logger.warning(
                    event='LLM_STREAM_CACHE_ERROR',
                    message=f'Cache lookup error in streaming: {e}'
                )

        # Build prompt
        full_prompt = self._build_prompt(query, intent, context)

        start_time = time.time()
        full_response = ""
        success = False
        mode_used = "stream_" + self.mode

        try:
            if self.mode == "api":
                # Stream from Gemini API
                for chunk in self._generate_api_stream(full_prompt):
                    full_response += chunk
                    yield chunk
                success = True
            elif self.mode == "local":
                # Stream from Ollama
                for chunk in self._generate_local_stream(full_prompt):
                    full_response += chunk
                    yield chunk
                success = True
            else:  # hybrid mode
                try:
                    # Try API first
                    for chunk in self._generate_api_stream(full_prompt):
                        full_response += chunk
                        yield chunk
                    success = True
                    mode_used = "stream_api"
                except Exception as api_error:
                    self.logger.warning(
                        event='LLM_STREAM_API_FALLBACK',
                        message=f'API streaming failed, falling back to local: {str(api_error)}'
                    )
                    # Fall back to local streaming
                    full_response = ""
                    for chunk in self._generate_local_stream(full_prompt):
                        full_response += chunk
                        yield chunk
                    success = True
                    mode_used = "stream_local"

        except Exception as e:
            self.logger.error(
                event='LLM_STREAM_GENERATION_FAILED',
                message=f'Streaming generation failed: {str(e)}',
                error=str(e)
            )
            yield f"\nError: {str(e)}"
            return

        finally:
            # Log streaming metrics
            duration_ms = int((time.time() - start_time) * 1000)

            # Cache the complete response if streaming succeeded
            if success and full_response and self.cache:
                try:
                    context_str = None
                    if context and context.exchanges:
                        context_str = "|".join([
                            f"{e.user_input}:{e.assistant_response}"
                            for e in context.exchanges[-2:]
                        ])

                    intent_str = intent.intent_type.value if intent else None
                    metadata = {
                        "mode": mode_used,
                        "query_length": len(query),
                        "response_length": len(full_response),
                        "streaming_time_ms": duration_ms
                    }

                    self.cache.set(query, full_response, context_str, intent_str, metadata)
                except Exception as cache_error:
                    self.logger.warning(
                        event='LLM_STREAM_CACHE_STORE_FAILED',
                        message=f'Failed to cache streaming response: {cache_error}'
                    )

            self.logger.info(
                event='LLM_STREAM_COMPLETED',
                message=f'Streaming completed: "{full_response[:50]}..."',
                query_length=len(query),
                response_length=len(full_response),
                processing_time_ms=duration_ms,
                mode=mode_used,
                success=success
            )

            self.metrics_logger.record_metric('llm_stream_latency_ms', duration_ms)
            self.metrics_logger.record_metric('llm_stream_response_length', len(full_response))

    def _generate_api_stream(self, prompt: str):
        """
        Stream response from Gemini API using generator pattern.

        Args:
            prompt: Complete prompt to send to Gemini

        Yields:
            Text chunks from the API response
        """
        if not GEMINI_AVAILABLE or not self.gemini_client:
            raise RuntimeError("Gemini API not available for streaming")

        try:
            gemini_tools = self._tools_to_gemini_format()

            # Use streaming API (generate_content is already streaming-compatible)
            response = self.gemini_client.models.generate_content(
                model=self.config.llm.api_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=self.config.llm.temperature,
                    max_output_tokens=self.config.llm.max_tokens,
                    tools=gemini_tools
                ),
                stream=True  # Enable streaming
            )

            # Iterate through response chunks
            for chunk in response:
                if hasattr(chunk, 'text') and chunk.text:
                    yield chunk.text

        except Exception as e:
            raise RuntimeError(f"Gemini API streaming error: {str(e)}")

    def _generate_local_stream(self, prompt: str):
        """
        Stream response from Ollama (local) using generator pattern.

        Args:
            prompt: Complete prompt to send to Ollama

        Yields:
            Text chunks from the model response
        """
        if not OLLAMA_AVAILABLE:
            raise RuntimeError("Ollama not available for streaming")

        try:
            # Use Ollama streaming API
            response = ollama.generate(
                model=self.config.llm.local_model,
                prompt=prompt,
                stream=True,
                options={
                    "temperature": self.config.llm.temperature,
                    "top_p": 0.9,
                    "top_k": 40
                }
            )

            # Iterate through response chunks
            for chunk in response:
                if 'response' in chunk and chunk['response']:
                    yield chunk['response']

        except Exception as e:
            raise RuntimeError(f"Ollama streaming error: {str(e)}")


def create_llm_service(
    config: Config,
    logger: EventLogger,
    metrics_logger: MetricsLogger
) -> LLMService:
    """Factory function to create LLM service"""
    service = LLMService(
        config=config,
        logger=logger,
        metrics_logger=metrics_logger
    )
    return service
