"""
Advanced Voice Command Understanding Service
Provides intelligent command parsing with fuzzy matching, intent classification,
and multi-word command support.

Reference: https://github.com/jamesturk/cachetools
"""

import logging
import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

# Try to import fuzzywuzzy (optional)
try:
    from fuzzywuzzy import fuzz
    FUZZY_AVAILABLE = True
except ImportError:
    FUZZY_AVAILABLE = False
    logger.warning("fuzzywuzzy not installed. Install with: pip install fuzzywuzzy python-Levenshtein")


class CommandIntent(str, Enum):
    """Categories of voice commands"""
    SEARCH = "search"
    SEND_MESSAGE = "send_message"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    RETRIEVE = "retrieve"
    NAVIGATE = "navigate"
    EXECUTE_ACTION = "execute_action"
    SCHEDULE = "schedule"
    QUERY = "query"
    UNKNOWN = "unknown"


@dataclass
class ParsedCommand:
    """Parsed voice command with metadata"""
    intent: CommandIntent
    command: str
    parameters: Dict[str, str]
    confidence: float
    raw_input: str
    matched_pattern: Optional[str] = None
    alternatives: Optional[List[Tuple[CommandIntent, str]]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "intent": self.intent.value,
            "command": self.command,
            "parameters": self.parameters,
            "confidence": self.confidence,
            "raw_input": self.raw_input,
            "matched_pattern": self.matched_pattern,
            "alternatives": [
                (alt[0].value, alt[1]) for alt in (self.alternatives or [])
            ]
        }


class VoiceCommandPattern:
    """Pattern definition for voice commands"""

    def __init__(
        self,
        intent: CommandIntent,
        patterns: List[str],
        parameter_extractor: Optional[callable] = None,
        min_confidence: float = 0.7
    ):
        """
        Initialize command pattern.

        Args:
            intent: Intent this pattern matches
            patterns: List of regex patterns or literal strings
            parameter_extractor: Optional function to extract parameters
            min_confidence: Minimum confidence threshold for fuzzy matching
        """
        self.intent = intent
        self.patterns = patterns
        self.parameter_extractor = parameter_extractor
        self.min_confidence = min_confidence
        self.compiled_patterns = [re.compile(p, re.IGNORECASE) for p in patterns]

    def match(self, text: str, use_fuzzy: bool = True) -> Optional[Tuple[float, Dict[str, str]]]:
        """
        Try to match text against pattern.

        Args:
            text: Text to match
            use_fuzzy: Whether to use fuzzy matching

        Returns:
            Tuple of (confidence, parameters) or None if no match
        """
        # Try regex patterns first (high confidence)
        for pattern in self.compiled_patterns:
            match = pattern.search(text)
            if match:
                parameters = {}
                if self.parameter_extractor:
                    parameters = self.parameter_extractor(text, match)

                return (0.95, parameters)

        # Try fuzzy matching if enabled
        if use_fuzzy and FUZZY_AVAILABLE:
            for pattern_str in self.patterns:
                # Remove regex special characters for fuzzy matching
                clean_pattern = re.sub(r'[\\()\[\]?*+^$|.]', '', pattern_str)

                ratio = fuzz.token_set_ratio(text.lower(), clean_pattern.lower())
                confidence = ratio / 100.0

                if confidence >= self.min_confidence:
                    parameters = {}
                    if self.parameter_extractor:
                        parameters = self.parameter_extractor(text, None)

                    return (confidence, parameters)

        return None


class AdvancedVoiceCommandParser:
    """
    Professional voice command parser with fuzzy matching and intent classification.
    """

    def __init__(self, use_fuzzy: bool = True):
        """
        Initialize voice command parser.

        Args:
            use_fuzzy: Whether to enable fuzzy matching
        """
        self.use_fuzzy = use_fuzzy and FUZZY_AVAILABLE
        self.patterns: Dict[CommandIntent, List[VoiceCommandPattern]] = {}
        self._initialize_patterns()

        logger.info(
            f"AdvancedVoiceCommandParser initialized "
            f"(fuzzy={'enabled' if self.use_fuzzy else 'disabled'})"
        )

    def _initialize_patterns(self) -> None:
        """Initialize default command patterns"""

        # Search commands
        search_patterns = [
            r"(?:search|find|look(?:\s+up)?|google)\s+(?:for\s+)?(.+)",
            r"what\s+(?:is|are)\s+(.+)",
            r"tell\s+me\s+about\s+(.+)",
            r"(?:find|get).*information.*(?:about|on)\s+(.+)"
        ]

        def search_extractor(text: str, match):
            if match:
                return {"query": match.group(1)}
            # Fallback: extract after keywords
            keywords = ["search", "find", "look", "google", "what", "tell", "information"]
            for keyword in keywords:
                idx = text.lower().find(keyword)
                if idx != -1:
                    query = text[idx + len(keyword):].strip()
                    # Remove common prefixes
                    query = re.sub(r"^(?:for|about|on|in)\s+", "", query)
                    return {"query": query}
            return {}

        self.add_pattern(
            CommandIntent.SEARCH,
            search_patterns,
            search_extractor
        )

        # Send message commands
        send_patterns = [
            r"(?:send|post)\s+(?:a\s+)?(?:message|msg)\s+to\s+([#@]?\w+):\s*(.+)",
            r"(?:slack|discord)\s+([#@]?\w+):\s*(.+)",
            r"message\s+([#@]?\w+):\s*(.+)",
            r"email\s+(\S+):\s*(.+)"
        ]

        def send_extractor(text: str, match):
            if match:
                return {
                    "recipient": match.group(1),
                    "message": match.group(2)
                }
            return {}

        self.add_pattern(
            CommandIntent.SEND_MESSAGE,
            send_patterns,
            send_extractor
        )

        # Create commands
        create_patterns = [
            r"create\s+(?:a\s+)?([^:]+)(?::\s*(.+))?",
            r"make\s+(?:a\s+)?([^:]+)(?::\s*(.+))?",
            r"new\s+([^:]+)(?::\s*(.+))?",
            r"add\s+(?:a\s+)?([^:]+)(?::\s*(.+))?"
        ]

        def create_extractor(text: str, match):
            if match:
                return {
                    "item_type": match.group(1),
                    "details": match.group(2) or ""
                }
            return {}

        self.add_pattern(
            CommandIntent.CREATE,
            create_patterns,
            create_extractor
        )

        # Update commands
        update_patterns = [
            r"update\s+([^:]+)(?:to\s+(.+))?",
            r"change\s+([^:]+)\s+to\s+(.+)",
            r"set\s+([^:]+)\s+to\s+(.+)",
            r"modify\s+([^:]+)(?:to\s+(.+))?"
        ]

        def update_extractor(text: str, match):
            if match:
                return {
                    "target": match.group(1),
                    "new_value": match.group(2) or ""
                }
            return {}

        self.add_pattern(
            CommandIntent.UPDATE,
            update_patterns,
            update_extractor
        )

        # Delete commands
        delete_patterns = [
            r"delete\s+([^.!?]+)",
            r"remove\s+([^.!?]+)",
            r"(?:erase|clear)\s+([^.!?]+)",
            r"(?:cancel|undo)\s+([^.!?]+)"
        ]

        def delete_extractor(text: str, match):
            if match:
                return {"target": match.group(1)}
            return {}

        self.add_pattern(
            CommandIntent.DELETE,
            delete_patterns,
            delete_extractor
        )

        # Navigate commands
        navigate_patterns = [
            r"(?:go\s+to|navigate\s+to|open)\s+(.+)",
            r"visit\s+(.+)",
            r"take\s+me\s+to\s+(.+)",
            r"browse\s+(.+)"
        ]

        def navigate_extractor(text: str, match):
            if match:
                return {"destination": match.group(1)}
            return {}

        self.add_pattern(
            CommandIntent.NAVIGATE,
            navigate_patterns,
            navigate_extractor
        )

        # Schedule commands
        schedule_patterns = [
            r"schedule\s+([^:]+)\s+(?:for|on|at)\s+(.+)",
            r"remind\s+me\s+(?:to\s+)?([^:]+)\s+(?:on|at)\s+(.+)",
            r"book\s+([^:]+)\s+(?:for|on|at)\s+(.+)"
        ]

        def schedule_extractor(text: str, match):
            if match:
                return {
                    "event": match.group(1),
                    "time": match.group(2)
                }
            return {}

        self.add_pattern(
            CommandIntent.SCHEDULE,
            schedule_patterns,
            schedule_extractor
        )

        # Query commands
        query_patterns = [
            r"what\s+'s\s+(.+)",
            r"show\s+me\s+(.+)",
            r"list\s+(.+)",
            r"get\s+(?:the\s+)?(.+)"
        ]

        def query_extractor(text: str, match):
            if match:
                return {"query": match.group(1)}
            return {}

        self.add_pattern(
            CommandIntent.QUERY,
            query_patterns,
            query_extractor
        )

    def add_pattern(
        self,
        intent: CommandIntent,
        patterns: List[str],
        parameter_extractor: Optional[callable] = None,
        min_confidence: float = 0.7
    ) -> None:
        """
        Add command pattern.

        Args:
            intent: Command intent
            patterns: List of patterns to match
            parameter_extractor: Optional parameter extractor function
            min_confidence: Minimum fuzzy match confidence
        """
        pattern = VoiceCommandPattern(
            intent,
            patterns,
            parameter_extractor,
            min_confidence
        )

        if intent not in self.patterns:
            self.patterns[intent] = []

        self.patterns[intent].append(pattern)

    def parse(self, text: str, return_alternatives: bool = True) -> ParsedCommand:
        """
        Parse voice command from text.

        Args:
            text: Voice command text
            return_alternatives: Whether to return alternative interpretations

        Returns:
            ParsedCommand with intent, parameters, and confidence
        """
        text = text.strip()
        best_match = None
        best_confidence = 0.0
        best_intent = None
        best_parameters = {}
        best_pattern_str = None
        alternatives = []

        # Try all patterns
        for intent, pattern_list in self.patterns.items():
            for pattern in pattern_list:
                result = pattern.match(text, self.use_fuzzy)

                if result:
                    confidence, parameters = result

                    # Track alternatives
                    if return_alternatives and confidence >= 0.6:
                        alternatives.append((intent, text))

                    # Keep best match
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_intent = intent
                        best_parameters = parameters
                        best_pattern_str = pattern.patterns[0] if pattern.patterns else None

        # If no match found
        if best_intent is None:
            best_intent = CommandIntent.UNKNOWN
            best_confidence = 0.0

        # Sort alternatives by confidence
        alternatives = sorted(alternatives, key=lambda x: x[1], reverse=True)[:3]

        logger.info(
            f"Parsed command: {best_intent.value} "
            f"(confidence: {best_confidence:.2f}, text: '{text[:50]}')"
        )

        return ParsedCommand(
            intent=best_intent,
            command=best_intent.value,
            parameters=best_parameters,
            confidence=best_confidence,
            raw_input=text,
            matched_pattern=best_pattern_str,
            alternatives=alternatives if alternatives else None
        )

    def handle_typos(self, text: str, max_distance: int = 2) -> str:
        """
        Attempt to correct common typos in voice command.

        Args:
            text: Text with potential typos
            max_distance: Maximum edit distance for correction

        Returns:
            Corrected text (or original if no correction found)
        """
        if not FUZZY_AVAILABLE:
            return text

        common_words = {
            "serch": "search",
            "seach": "search",
            "sarch": "search",
            "mesage": "message",
            "msg": "message",
            "creat": "create",
            "updat": "update",
            "delet": "delete",
            "naviage": "navigate",
            "shedule": "schedule",
            "shcedule": "schedule",
        }

        words = text.lower().split()
        corrected_words = []

        for word in words:
            # Check if word matches a common typo
            best_match = None
            best_ratio = 0

            for typo, correct in common_words.items():
                ratio = fuzz.ratio(word, typo)
                if ratio > best_ratio and ratio >= 80:
                    best_ratio = ratio
                    best_match = correct

            corrected_words.append(best_match if best_match else word)

        return " ".join(corrected_words)

    def extract_entities_from_command(self, parsed: ParsedCommand) -> Dict[str, List[str]]:
        """
        Extract named entities from parsed command.

        Args:
            parsed: ParsedCommand object

        Returns:
            Dictionary of extracted entities
        """
        entities = {"parameters": list(parsed.parameters.values())}

        # Extract additional entities based on intent
        if parsed.intent == CommandIntent.SEND_MESSAGE:
            entities["recipients"] = [parsed.parameters.get("recipient", "")]

        elif parsed.intent == CommandIntent.NAVIGATE:
            entities["destinations"] = [parsed.parameters.get("destination", "")]

        elif parsed.intent == CommandIntent.SCHEDULE:
            entities["times"] = [parsed.parameters.get("time", "")]
            entities["events"] = [parsed.parameters.get("event", "")]

        return entities

    def get_stats(self) -> Dict[str, Any]:
        """Get parser statistics"""
        total_patterns = sum(len(plist) for plist in self.patterns.values())

        return {
            "total_intents": len(self.patterns),
            "total_patterns": total_patterns,
            "fuzzy_matching": self.use_fuzzy,
            "intents": list(CommandIntent.__members__.keys()),
            "patterns_per_intent": {
                intent.value: len(plist)
                for intent, plist in self.patterns.items()
            }
        }
