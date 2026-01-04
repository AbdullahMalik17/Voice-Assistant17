"""
Intent Classification Service
Classifies user queries into intent types (INFORMATIONAL, TASK_BASED, CONVERSATIONAL)
"""

import re
import time
from typing import Dict, Any, Tuple
from uuid import UUID

from ..core.config import Config
from ..models.intent import Intent, IntentType, ActionType
from ..models.voice_command import VoiceCommand
from ..utils.logger import EventLogger, MetricsLogger


class IntentClassifier:
    """
    Intent classification service
    Uses rule-based classification with keyword matching
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

    def classify(self, text: str, voice_command_id: UUID) -> Intent:
        """
        Classify text into intent type
        Returns: Intent object with classification and confidence
        """
        if not text or len(text.strip()) == 0:
            raise ValueError("Text must not be empty")

        start_time = time.time()
        text_lower = text.lower().strip()

        # Classify intent
        intent_type, action_type, confidence, entities = self._classify_text(text_lower)

        # Determine network requirement
        requires_network = self._requires_network(intent_type, action_type, text_lower)

        # Create Intent object
        intent = Intent(
            voice_command_id=voice_command_id,
            intent_type=intent_type,
            action_type=action_type,
            entities=entities,
            confidence_score=confidence,
            requires_network=requires_network
        )

        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)

        # Log event
        self.logger.info(
            event='INTENT_CLASSIFIED',
            message=f'Intent classified: {intent_type.value}',
            text=text[:100],
            intent_type=intent_type.value,
            action_type=action_type.value if action_type else None,
            confidence=confidence,
            processing_time_ms=duration_ms
        )

        # Record metrics
        self.metrics_logger.record_metric('intent_classification_latency_ms', duration_ms)
        self.metrics_logger.record_metric('intent_confidence', confidence)

        return intent

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

        elif action_type == ActionType.BROWSER_AUTOMATION:
            # Extract target or action details
            groups = [g for g in match.groups() if g]
            if groups:
                entities['target'] = groups[-1]

        return entities

    def _score_keywords(self, text: str, keywords: list) -> float:
        """Score text based on keyword presence"""
        matches = 0
        for keyword in keywords:
            if keyword in text:
                matches += 1

        # Normalize score
        if len(keywords) > 0:
            return min(matches / len(keywords) * 2.0, 1.0)  # Amplify score slightly
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
            # Browser automation might need network
            if action_type == ActionType.BROWSER_AUTOMATION:
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
    metrics_logger: MetricsLogger
) -> IntentClassifier:
    """Factory function to create intent classifier"""
    classifier = IntentClassifier(
        config=config,
        logger=logger,
        metrics_logger=metrics_logger
    )
    return classifier
