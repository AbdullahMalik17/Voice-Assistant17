"""
Intent Classification Service
Classifies user queries into intent types (INFORMATIONAL, TASK_BASED, CONVERSATIONAL)
Supports both LLM-based and rule-based classification with disambiguation.
"""

import json
import re
import time
from dataclasses import dataclass, field
from typing import Dict, Any, Tuple, List, Optional
from uuid import UUID

from ..core.config import Config
from ..models.intent import Intent, IntentType, ActionType
from ..models.voice_command import VoiceCommand
from ..utils.logger import EventLogger, MetricsLogger


@dataclass
class IntentCandidate:
    """A candidate intent with confidence score"""
    intent_type: IntentType
    action_type: Optional[ActionType]
    confidence: float
    entities: Dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""


# LLM prompt for intent classification
INTENT_CLASSIFICATION_PROMPT = '''Classify the following user input into one of these intent types:

**TASK_BASED** - User wants to execute a specific action:
- Launch application (open, start, run)
- System status (check CPU, memory, battery)
- Email operations (send, check, search email)
- Drive operations (access files, upload, download)
- Browser automation (navigate, search, screenshot)
- System control (volume, brightness, media, power, files, windows)
- File operations (create, delete, copy, move)

**INFORMATIONAL** - User is asking for information:
- Questions starting with what, when, where, who, why, how
- Weather, time, date, news queries
- Calculations, conversions, translations
- Search requests

**CONVERSATIONAL** - General conversation:
- Greetings (hello, hi, good morning)
- Small talk (how are you, thank you)
- Requests for jokes, stories, chat

For TASK_BASED intents, also specify the action type: LAUNCH_APP, SYSTEM_STATUS, EMAIL_ACCESS, DRIVE_ACCESS, BROWSER_AUTOMATION, SYSTEM_CONTROL, FILE_OPERATION

User input: "{text}"

Return JSON with:
{{
  "intent_type": "TASK_BASED|INFORMATIONAL|CONVERSATIONAL",
  "action_type": "action type if TASK_BASED, otherwise null",
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation",
  "entities": {{"key": "value"}}
}}'''


class IntentClassifier:
    """
    Intent classification service.
    Uses LLM for primary classification with rule-based fallback.
    Supports disambiguation when confidence is low or multiple candidates exist.
    """

    def __init__(
        self,
        config: Config,
        logger: EventLogger,
        metrics_logger: MetricsLogger,
        llm_service=None
    ):
        self.config = config
        self.logger = logger
        self.metrics_logger = metrics_logger
        self.llm_service = llm_service
        self.use_llm = llm_service is not None

        # Disambiguation threshold - if top 2 candidates are within this range, ask user
        self.disambiguation_threshold = 0.15

        # Define classification patterns
        self._task_patterns = {
            ActionType.LAUNCH_APP: [
                r'\b(open|launch|start|run)\s+(\w+)',
                r'\b(open|show)\s+(my|the)?\s*(\w+)\s*(app|application)',
            ],
            ActionType.SYSTEM_STATUS: [
                r'\b(check|show|what\'?s?)\s+(my|the)?\s*(cpu|memory|disk|battery|temperature|status)',
                r'\b(how\s+much|how\s+many)\s+(memory|ram|disk\s+space)',
            ],
            ActionType.EMAIL_ACCESS: [
                r'\b(open|check|show|read)\s+(my\s+)?(email|gmail|inbox|mail)',
                r'\b(check|show|list)\s+(my\s+)?messages',
                r'\b(send|write|compose)\s+(an?\s+)?email',
                r'\b(search|find)\s+(in\s+)?(my\s+)?(email|gmail)',
            ],
            ActionType.DRIVE_ACCESS: [
                r'\b(open|show|access)\s+(my\s+)?(google\s+)?drive',
                r'\b(list|show)\s+(my\s+)?files',
                r'\b(find|search)\s+(file|document|folder)',
                r'\b(download|upload)\s+(file|document)',
            ],
            ActionType.BROWSER_AUTOMATION: [
                r'\b(navigate|go|browse)\s+to\s+(.+)',
                r'\b(search|google|look\s+up)\s+(for\s+)?(.+)',
                r'\b(open|visit)\s+(website|page|url)',
                r'\b(take|capture)\s+(a\s+)?(screenshot|screen\s+shot)',
            ],
            ActionType.SYSTEM_CONTROL: [
                r'\b(find|locate|search\s+for)\s+(file|folder)',
                r'\b(take|capture)\s+(a\s+)?(screenshot|screen\s+capture)',
                r'\b(minimize|maximize|close)\s+(window|all)',
                r'\b(switch|change)\s+to\s+(.+)',
                r'\b(turn|set|change|increase|decrease|mute|unmute)\s+(the\s+)?(volume|sound|audio)',
                r'\b(turn|set|change|increase|decrease)\s+(the\s+)?(brightness|screen)',
                r'\b(play|pause|stop|next|previous)\s+(music|media|song|track)',
                r'\b(shutdown|restart|reboot|sleep|lock)\s+(the\s+)?(computer|pc|system|laptop)',
            ],
            ActionType.FILE_OPERATION: [
                r'\b(create|make|new)\s+(file|folder|directory)',
                r'\b(delete|remove)\s+(file|folder)',
                r'\b(copy|move)\s+(.+)\s+to\s+(.+)',
            ],
        }

        self._informational_keywords = [
            'what', 'when', 'where', 'who', 'why', 'how',
            'tell me', 'show me', 'explain', 'describe',
            'weather', 'time', 'date', 'news', 'search',
            'calculate', 'convert', 'translate'
        ]

        self._conversational_keywords = [
            'hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening',
            'how are you', 'thank you', 'thanks', 'goodbye', 'bye',
            'joke', 'story', 'chat', 'talk',
            # Multi-language greetings
            'assalamu alaikum', 'salam', 'namaste', 'bonjour', 'hola',
            'kaise ho', 'ka haal', 'haal', 'theek', 'acha'
        ]

    def classify(self, text: str, voice_command_id: UUID, use_llm: bool = True) -> Intent:
        """
        Classify text into intent type.

        Args:
            text: The text to classify
            voice_command_id: ID of the voice command
            use_llm: Whether to use LLM classification (defaults to True if available)

        Returns:
            Intent object with classification and confidence
        """
        if not text or len(text.strip()) == 0:
            raise ValueError("Text must not be empty")

        start_time = time.time()
        text_lower = text.lower().strip()

        # Get multiple candidates
        candidates = self._get_intent_candidates(text_lower, use_llm)

        # Check if disambiguation is needed
        needs_disambiguation = self._needs_disambiguation(candidates)

        if needs_disambiguation:
            # Return most confident candidate with disambiguation flag
            best_candidate = candidates[0]
            self.logger.info(
                event='INTENT_DISAMBIGUATION_NEEDED',
                message=f'Multiple candidates with similar confidence',
                candidates=[{
                    'intent': c.intent_type.value,
                    'action': c.action_type.value if c.action_type else None,
                    'confidence': c.confidence
                } for c in candidates[:2]]
            )
        else:
            best_candidate = candidates[0]

        # Determine network requirement
        requires_network = self._requires_network(
            best_candidate.intent_type,
            best_candidate.action_type,
            text_lower
        )

        # Create Intent object
        intent = Intent(
            voice_command_id=voice_command_id,
            intent_type=best_candidate.intent_type,
            action_type=best_candidate.action_type,
            entities=best_candidate.entities,
            confidence_score=best_candidate.confidence,
            requires_network=requires_network
        )

        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)

        # Log event
        self.logger.info(
            event='INTENT_CLASSIFIED',
            message=f'Intent classified: {best_candidate.intent_type.value}',
            text=text[:100],
            intent_type=best_candidate.intent_type.value,
            action_type=best_candidate.action_type.value if best_candidate.action_type else None,
            confidence=best_candidate.confidence,
            processing_time_ms=duration_ms,
            llm_used=use_llm and self.use_llm
        )

        # Record metrics
        self.metrics_logger.record_metric('intent_classification_latency_ms', duration_ms)
        self.metrics_logger.record_metric('intent_confidence', best_candidate.confidence)

        return intent

    def _get_intent_candidates(self, text: str, use_llm: bool = True) -> List[IntentCandidate]:
        """
        Get ranked intent candidates.

        Returns:
            List of IntentCandidate objects sorted by confidence (descending)
        """
        candidates = []

        # Try LLM classification first if available and requested
        if use_llm and self.use_llm:
            try:
                llm_candidate = self._classify_with_llm(text)
                candidates.append(llm_candidate)
            except Exception as e:
                self.logger.warning(
                    event='LLM_CLASSIFICATION_FAILED',
                    message=f'LLM classification failed, using rule-based fallback: {str(e)}'
                )

        # Always get rule-based classification as fallback/validation
        rule_candidates = self._classify_with_rules(text)

        # Merge candidates, avoiding duplicates
        for rule_cand in rule_candidates:
            # Check if similar candidate from LLM exists
            is_duplicate = any(
                c.intent_type == rule_cand.intent_type and
                c.action_type == rule_cand.action_type
                for c in candidates
            )
            if not is_duplicate:
                candidates.append(rule_cand)

        # Sort by confidence
        candidates.sort(key=lambda c: c.confidence, reverse=True)

        return candidates if candidates else [self._get_default_candidate()]

    def _classify_with_llm(self, text: str) -> IntentCandidate:
        """Classify using LLM with structured output"""
        prompt = INTENT_CLASSIFICATION_PROMPT.format(text=text)

        response = self.llm_service.generate(
            prompt=prompt,
            max_tokens=300,
            temperature=0.1  # Low temperature for consistent classification
        )

        # Parse JSON response
        try:
            # Extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())

                intent_type = IntentType(data.get('intent_type', 'CONVERSATIONAL'))
                action_type = None
                if data.get('action_type'):
                    try:
                        action_type = ActionType(data['action_type'])
                    except ValueError:
                        pass

                return IntentCandidate(
                    intent_type=intent_type,
                    action_type=action_type,
                    confidence=float(data.get('confidence', 0.7)),
                    entities=data.get('entities', {}),
                    reasoning=data.get('reasoning', '')
                )
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            self.logger.warning(
                event='LLM_RESPONSE_PARSE_ERROR',
                message=f'Failed to parse LLM response: {str(e)}'
            )

        # Return default if parsing fails
        return self._get_default_candidate()

    def _classify_with_rules(self, text: str) -> List[IntentCandidate]:
        """Get candidate intents using rule-based classification"""
        candidates = []

        # Check for task-based intents first (most specific)
        for action_type, patterns in self._task_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    entities = self._extract_entities(match, action_type)
                    candidates.append(IntentCandidate(
                        intent_type=IntentType.TASK_BASED,
                        action_type=action_type,
                        confidence=0.85,  # High confidence for pattern match
                        entities=entities
                    ))
                    break  # Only add one candidate per action type

        # Check for conversational intents
        conversational_score = self._score_keywords(text, self._conversational_keywords)
        if conversational_score > 0.5:
            candidates.append(IntentCandidate(
                intent_type=IntentType.CONVERSATIONAL,
                action_type=None,
                confidence=conversational_score
            ))

        # Check for informational intents
        informational_score = self._score_keywords(text, self._informational_keywords)
        if informational_score > 0.4:
            candidates.append(IntentCandidate(
                intent_type=IntentType.INFORMATIONAL,
                action_type=None,
                confidence=informational_score
            ))

        return candidates if candidates else [self._get_default_candidate()]

    def _needs_disambiguation(self, candidates: List[IntentCandidate]) -> bool:
        """Check if disambiguation is needed based on candidate confidence scores"""
        if len(candidates) < 2:
            return False

        # Check if top 2 candidates have similar confidence
        confidence_diff = candidates[0].confidence - candidates[1].confidence
        return confidence_diff < self.disambiguation_threshold

    def disambiguate(
        self,
        text: str,
        candidates: List[IntentCandidate],
        max_options: int = 2
    ) -> str:
        """
        Generate disambiguation question for user.

        Args:
            text: Original user input
            candidates: List of intent candidates
            max_options: Maximum number of options to present

        Returns:
            Disambiguation question string
        """
        top_candidates = candidates[:max_options]

        question_parts = [
            "I'm not sure what you want to do. Did you mean:"
        ]

        for i, candidate in enumerate(top_candidates, 1):
            if candidate.intent_type == IntentType.TASK_BASED:
                action_desc = self._get_action_description(candidate.action_type, candidate.entities)
                question_parts.append(f"{i}. {action_desc}")
            elif candidate.intent_type == IntentType.INFORMATIONAL:
                question_parts.append(f"{i}. Get information about: {text}")
            else:
                question_parts.append(f"{i}. Have a conversation")

        return "\n".join(question_parts)

    def _get_action_description(self, action_type: ActionType, entities: Dict[str, Any]) -> str:
        """Get human-readable description of an action"""
        descriptions = {
            ActionType.LAUNCH_APP: f"Launch {entities.get('app_name', 'an application')}",
            ActionType.SYSTEM_STATUS: f"Check {entities.get('status_type', 'system status')}",
            ActionType.EMAIL_ACCESS: f"{entities.get('action', 'Access').capitalize()} email",
            ActionType.DRIVE_ACCESS: f"{entities.get('action', 'Access').capitalize()} Google Drive",
            ActionType.BROWSER_AUTOMATION: f"Navigate to {entities.get('target', 'a website')}",
            ActionType.SYSTEM_CONTROL: f"Control {entities.get('target', 'the system')}",
            ActionType.FILE_OPERATION: "Perform file operation"
        }
        return descriptions.get(action_type, f"Perform {action_type.value}")

    def _get_default_candidate(self) -> IntentCandidate:
        """Get default candidate when classification fails"""
        return IntentCandidate(
            intent_type=IntentType.CONVERSATIONAL,
            action_type=None,
            confidence=0.3
        )

    def _classify_text(self, text: str) -> Tuple[IntentType, ActionType, float, Dict[str, Any]]:
        """
        Core classification logic
        Returns: (intent_type, action_type, confidence, entities)
        """
        entities = {}

        # Check for task-based intents first (most specific)
        for action_type, patterns in self._task_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    # Extract entities from regex groups
                    if match.groups():
                        entities = self._extract_entities(match, action_type)

                    # High confidence for pattern match
                    return IntentType.TASK_BASED, action_type, 0.9, entities

        # Check for conversational intents
        conversational_score = self._score_keywords(text, self._conversational_keywords)
        if conversational_score > 0.6:
            return IntentType.CONVERSATIONAL, None, conversational_score, entities

        # Check for informational intents
        informational_score = self._score_keywords(text, self._informational_keywords)
        if informational_score > 0.5:
            return IntentType.INFORMATIONAL, None, informational_score, entities

        # Default to conversational with lower confidence
        # If no clear pattern, treat as conversation
        return IntentType.CONVERSATIONAL, None, 0.4, entities

    def _extract_entities(self, match: re.Match, action_type: ActionType) -> Dict[str, Any]:
        """Extract entities from regex match based on action type"""
        entities = {}

        if action_type == ActionType.LAUNCH_APP:
            # Extract app name from groups
            groups = [g for g in match.groups() if g]
            if groups:
                entities['app_name'] = groups[-1]  # Last group is usually the app name

        elif action_type == ActionType.SYSTEM_STATUS:
            # Extract status type
            groups = [g for g in match.groups() if g]
            for group in groups:
                if group in ['cpu', 'memory', 'ram', 'disk', 'battery', 'temperature']:
                    entities['status_type'] = group

        elif action_type == ActionType.EMAIL_ACCESS:
            # Extract email-related entities
            groups = [g for g in match.groups() if g]
            if 'send' in match.string.lower() or 'compose' in match.string.lower():
                entities['action'] = 'compose'
            elif 'search' in match.string.lower() or 'find' in match.string.lower():
                entities['action'] = 'search'
            else:
                entities['action'] = 'list'

        elif action_type == ActionType.DRIVE_ACCESS:
            # Extract Drive-related entities
            groups = [g for g in match.groups() if g]
            if 'download' in match.string.lower():
                entities['action'] = 'download'
            elif 'upload' in match.string.lower():
                entities['action'] = 'upload'
            elif 'search' in match.string.lower() or 'find' in match.string.lower():
                entities['action'] = 'search'
            else:
                entities['action'] = 'list'

        elif action_type == ActionType.BROWSER_AUTOMATION:
            # Extract target or action details
            groups = [g for g in match.groups() if g]
            if groups:
                entities['target'] = groups[-1]

        elif action_type == ActionType.SYSTEM_CONTROL:
            # Extract system control details
            groups = [g for g in match.groups() if g]
            
            # Check for specific control types based on keywords
            text = match.string.lower()
            
            if any(k in text for k in ['volume', 'sound', 'audio']):
                entities['control_type'] = 'volume'
                if 'mute' in text: entities['action'] = 'mute'
                elif 'unmute' in text: entities['action'] = 'unmute'
                elif 'increase' in text or 'up' in text: entities['action'] = 'up'
                elif 'decrease' in text or 'down' in text: entities['action'] = 'down'
                elif 'set' in text: entities['action'] = 'set'
                
                # Try to find a number for 'set'
                num_match = re.search(r'\b(\d+)\b', text)
                if num_match:
                    entities['level'] = int(num_match.group(1))

            elif any(k in text for k in ['brightness', 'screen']):
                entities['control_type'] = 'brightness'
                if 'increase' in text or 'up' in text: entities['level'] = 100 # simplified
                elif 'decrease' in text or 'down' in text: entities['level'] = 0 # simplified
                elif 'set' in text: 
                    num_match = re.search(r'\b(\d+)\b', text)
                    if num_match:
                        entities['level'] = int(num_match.group(1))

            elif any(k in text for k in ['media', 'music', 'song', 'track']):
                entities['control_type'] = 'media'
                if 'play' in text or 'pause' in text: entities['action'] = 'play_pause'
                elif 'next' in text: entities['action'] = 'next'
                elif 'previous' in text: entities['action'] = 'previous'
                elif 'stop' in text: entities['action'] = 'stop'

            elif any(k in text for k in ['shutdown', 'restart', 'reboot', 'sleep', 'lock']):
                entities['control_type'] = 'power'
                if 'shutdown' in text: entities['action'] = 'shutdown'
                elif 'restart' in text or 'reboot' in text: entities['action'] = 'restart'
                elif 'sleep' in text: entities['action'] = 'sleep'
                elif 'lock' in text: entities['action'] = 'lock'

            elif groups:
                entities['target'] = groups[-1]

        return entities

    def _score_keywords(self, text: str, keywords: list) -> float:
        """Score text based on keyword presence"""
        text_lower = text.lower()
        for keyword in keywords:
            # Check for exact word match or phrase match
            # Add word boundaries for short keywords to avoid false positives
            if len(keyword.split()) == 1 and len(keyword) < 4:
                if re.search(r'\b' + re.escape(keyword) + r'\b', text_lower):
                    return 0.85
            else:
                if keyword in text_lower:
                    return 0.85
        return 0.0

    def _requires_network(
        self,
        intent_type: IntentType,
        action_type: ActionType,
        text: str
    ) -> bool:
        """Determine if intent requires network connectivity"""
        # Task-based intents usually don't require network (local actions)
        if intent_type == IntentType.TASK_BASED:
            # These actions require network
            if action_type in [
                ActionType.BROWSER_AUTOMATION,
                ActionType.EMAIL_ACCESS,
                ActionType.DRIVE_ACCESS
            ]:
                return True
            return False

        # Informational queries usually require network
        if intent_type == IntentType.INFORMATIONAL:
            # Check for network-dependent keywords
            network_keywords = ['weather', 'news', 'search', 'online', 'internet', 'web']
            for keyword in network_keywords:
                if keyword in text:
                    return True
            # Default to requiring network for info queries
            return True

        # Conversational might or might not need network
        # For baseline, assume local LLM can handle it
        return False

    def classify_voice_command(self, voice_command: VoiceCommand) -> Intent:
        """
        Classify a VoiceCommand that has been transcribed
        Returns: Intent object
        """
        if voice_command.transcribed_text is None:
            raise ValueError("VoiceCommand must be transcribed before classification")

        return self.classify(voice_command.transcribed_text, voice_command.id)

    def is_actionable(self, intent: Intent) -> bool:
        """Check if intent has sufficient confidence to act upon"""
        threshold = self.config.intent.confidence_threshold
        return intent.is_actionable(threshold)

    def test_service(self) -> bool:
        """Test intent classifier with sample queries"""
        try:
            from uuid import uuid4

            test_cases = [
                ("What time is it?", IntentType.INFORMATIONAL),
                ("Open Spotify", IntentType.TASK_BASED),
                ("Hello, how are you?", IntentType.CONVERSATIONAL),
            ]

            all_passed = True
            for text, expected_type in test_cases:
                intent = self.classify(text, uuid4())
                if intent.intent_type != expected_type:
                    self.logger.warning(
                        event='INTENT_TEST_MISMATCH',
                        message=f'Expected {expected_type}, got {intent.intent_type}',
                        text=text
                    )
                    all_passed = False

            self.logger.info(
                event='INTENT_CLASSIFIER_TEST_COMPLETED',
                message=f'Intent classifier test completed: {"PASSED" if all_passed else "FAILED"}'
            )

            return all_passed

        except Exception as e:
            self.logger.error(
                event='INTENT_CLASSIFIER_TEST_FAILED',
                message=f'Intent classifier test failed: {str(e)}',
                error=str(e)
            )
            return False


def create_intent_classifier(
    config: Config,
    logger: EventLogger,
    metrics_logger: MetricsLogger,
    llm_service=None
) -> IntentClassifier:
    """
    Factory function to create intent classifier.

    Args:
        config: Configuration object
        logger: Event logger
        metrics_logger: Metrics logger
        llm_service: Optional LLM service for advanced classification

    Returns:
        IntentClassifier instance
    """
    classifier = IntentClassifier(
        config=config,
        logger=logger,
        metrics_logger=metrics_logger,
        llm_service=llm_service
    )
    return classifier
