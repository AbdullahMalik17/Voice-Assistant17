"""
Language Model (LLM) Service
Generates responses to user queries using Gemini API with Ollama fallback
"""

import time
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

    def generate_response(
        self,
        query: str,
        intent: Optional[Intent] = None,
        context: Optional[ConversationContext] = None
    ) -> str:
        """
        Generate response to user query
        Returns: Generated response text
        """
        if not query or len(query.strip()) == 0:
            raise ValueError("Query must not be empty")

        start_time = time.time()
        response_text = ""
        success = False
        mode_used = self.mode

        try:
            # Build prompt with context
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

            # Log event
            self.logger.info(
                event='LLM_RESPONSE_GENERATED',
                message=f'Response generated: "{response_text[:50]}..."',
                query_length=len(query),
                response_length=len(response_text),
                processing_time_ms=duration_ms,
                mode=mode_used,
                intent_type=intent.intent_type.value if intent else None,
                success=success
            )

            # Record metrics
            self.metrics_logger.record_metric('llm_latency_ms', duration_ms)
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

    def _generate_api(self, prompt: str) -> str:
        """Generate response using Gemini API"""
        if not GEMINI_AVAILABLE:
            raise RuntimeError("Gemini library not available")

        if self.gemini_client is None:
            raise RuntimeError("Gemini client not initialized (check API key)")

        try:
            # Generate response with Gemini
            response = self.gemini_client.models.generate_content(
                model=self.config.llm.api_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=self.config.llm.temperature,
                    max_output_tokens=self.config.llm.max_tokens,
                )
            )

            # Extract text from response
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
