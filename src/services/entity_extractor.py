"""
Entity Extractor Module
Extracts named entities from text using LLM-based extraction with structured output.
Supports dates, times, persons, locations, numbers, and custom entity types.
"""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta


class EntityType(str, Enum):
    """Supported entity types"""
    DATE = "DATE"
    TIME = "TIME"
    DATETIME = "DATETIME"
    DURATION = "DURATION"
    PERSON = "PERSON"
    ORGANIZATION = "ORGANIZATION"
    LOCATION = "LOCATION"
    NUMBER = "NUMBER"
    MONEY = "MONEY"
    EMAIL = "EMAIL"
    URL = "URL"
    PHONE = "PHONE"
    APP_NAME = "APP_NAME"
    FILE_PATH = "FILE_PATH"
    CUSTOM = "CUSTOM"


@dataclass
class Entity:
    """A single extracted entity"""
    type: EntityType
    value: Any
    raw_text: str
    start: int = 0
    end: int = 0
    confidence: float = 1.0
    normalized_value: Optional[Any] = None  # Parsed/normalized form

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "value": self.value,
            "raw_text": self.raw_text,
            "start": self.start,
            "end": self.end,
            "confidence": self.confidence,
            "normalized_value": self.normalized_value
        }


@dataclass
class ExtractionResult:
    """Result of entity extraction"""
    entities: List[Entity] = field(default_factory=list)
    text: str = ""
    extraction_time_ms: float = 0.0

    def get_entities_by_type(self, entity_type: EntityType) -> List[Entity]:
        """Get all entities of a specific type"""
        return [e for e in self.entities if e.type == entity_type]

    def get_first_entity(self, entity_type: EntityType) -> Optional[Entity]:
        """Get the first entity of a specific type"""
        entities = self.get_entities_by_type(entity_type)
        return entities[0] if entities else None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entities": [e.to_dict() for e in self.entities],
            "text": self.text,
            "extraction_time_ms": self.extraction_time_ms
        }


# Entity extraction prompt template for LLM
ENTITY_EXTRACTION_PROMPT = '''Extract all named entities from the following text. Return a JSON object with an "entities" array.

For each entity, provide:
- type: One of DATE, TIME, DATETIME, DURATION, PERSON, ORGANIZATION, LOCATION, NUMBER, MONEY, EMAIL, URL, PHONE, APP_NAME, FILE_PATH
- value: The extracted value (normalized where possible)
- raw_text: The exact text from the input
- confidence: A score from 0.0 to 1.0

Examples:
- "5 minutes" → type: DURATION, value: "5 minutes", normalized: 300 (seconds)
- "tomorrow at 3pm" → type: DATETIME, value: "tomorrow at 3pm"
- "John" → type: PERSON, value: "John"
- "Spotify" → type: APP_NAME, value: "Spotify"
- "$50" → type: MONEY, value: 50, raw_text: "$50"

Text: {text}

Return only valid JSON:'''


class RuleBasedEntityExtractor:
    """
    Rule-based entity extractor using regex patterns.
    Used as fallback when LLM is not available.
    """

    def __init__(self):
        # Compile regex patterns for each entity type
        self.patterns = {
            EntityType.EMAIL: re.compile(
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            ),
            EntityType.URL: re.compile(
                r'https?://[^\s<>"{}|\\^`\[\]]+'
            ),
            EntityType.PHONE: re.compile(
                r'\b(?:\+?1[-.]?)?\(?[0-9]{3}\)?[-.]?[0-9]{3}[-.]?[0-9]{4}\b'
            ),
            EntityType.MONEY: re.compile(
                r'\$\d+(?:,\d{3})*(?:\.\d{2})?|\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:dollars?|USD)'
            ),
            EntityType.NUMBER: re.compile(
                r'\b\d+(?:\.\d+)?\b'
            ),
            EntityType.TIME: re.compile(
                r'\b(?:1[0-2]|0?[1-9])(?::[0-5][0-9])?\s*(?:am|pm|AM|PM)\b|\b(?:2[0-3]|[01]?[0-9]):([0-5][0-9])\b'
            ),
            EntityType.DURATION: re.compile(
                r'\b(\d+)\s*(seconds?|secs?|minutes?|mins?|hours?|hrs?|days?|weeks?|months?|years?)\b',
                re.IGNORECASE
            ),
            EntityType.APP_NAME: re.compile(
                r'\b(Spotify|Chrome|Firefox|Safari|Edge|Word|Excel|PowerPoint|Outlook|Teams|Slack|Discord|Zoom|VSCode|Terminal|Finder|Explorer|Notepad|Calculator|Calendar|Mail|Music|Photos|Videos|Settings|Store)\b',
                re.IGNORECASE
            ),
        }

        # Date patterns
        self.date_keywords = {
            'today': 0,
            'tomorrow': 1,
            'yesterday': -1,
            'next week': 7,
            'next month': 30,
        }

    def extract(self, text: str) -> List[Entity]:
        """Extract entities using regex patterns"""
        entities = []

        for entity_type, pattern in self.patterns.items():
            for match in pattern.finditer(text):
                raw_text = match.group()
                normalized = self._normalize(entity_type, raw_text, match)

                entities.append(Entity(
                    type=entity_type,
                    value=raw_text,
                    raw_text=raw_text,
                    start=match.start(),
                    end=match.end(),
                    confidence=0.9,
                    normalized_value=normalized
                ))

        # Extract date keywords
        text_lower = text.lower()
        for keyword, days_offset in self.date_keywords.items():
            if keyword in text_lower:
                idx = text_lower.find(keyword)
                target_date = datetime.now() + timedelta(days=days_offset)
                entities.append(Entity(
                    type=EntityType.DATE,
                    value=keyword,
                    raw_text=keyword,
                    start=idx,
                    end=idx + len(keyword),
                    confidence=0.95,
                    normalized_value=target_date.strftime("%Y-%m-%d")
                ))

        return entities

    def _normalize(
        self,
        entity_type: EntityType,
        raw_text: str,
        match: re.Match
    ) -> Optional[Any]:
        """Normalize extracted value"""
        if entity_type == EntityType.MONEY:
            # Extract numeric value
            nums = re.findall(r'[\d,]+\.?\d*', raw_text)
            if nums:
                return float(nums[0].replace(',', ''))

        elif entity_type == EntityType.DURATION:
            # Convert to seconds
            groups = match.groups()
            if len(groups) >= 2:
                amount = int(groups[0])
                unit = groups[1].lower()

                multipliers = {
                    'second': 1, 'sec': 1,
                    'minute': 60, 'min': 60,
                    'hour': 3600, 'hr': 3600,
                    'day': 86400,
                    'week': 604800,
                }

                for key, mult in multipliers.items():
                    if unit.startswith(key):
                        return amount * mult

        elif entity_type == EntityType.NUMBER:
            try:
                if '.' in raw_text:
                    return float(raw_text)
                return int(raw_text)
            except ValueError:
                return None

        elif entity_type == EntityType.TIME:
            try:
                parsed = date_parser.parse(raw_text)
                return parsed.strftime("%H:%M")
            except Exception:
                return None

        return None


class EntityExtractor:
    """
    Main entity extractor that uses LLM for extraction
    with rule-based fallback.
    """

    def __init__(self, llm_service=None):
        """
        Initialize entity extractor.

        Args:
            llm_service: Optional LLM service for advanced extraction.
                        Falls back to rule-based if not provided.
        """
        self.llm_service = llm_service
        self.rule_based = RuleBasedEntityExtractor()

    def extract(self, text: str, use_llm: bool = True) -> ExtractionResult:
        """
        Extract entities from text.

        Args:
            text: The text to extract entities from
            use_llm: Whether to use LLM extraction (if available)

        Returns:
            ExtractionResult with extracted entities
        """
        import time
        start_time = time.time()

        entities = []

        # Try LLM extraction first if available and requested
        if use_llm and self.llm_service is not None:
            try:
                entities = self._extract_with_llm(text)
            except Exception:
                # Fall back to rule-based
                entities = self.rule_based.extract(text)
        else:
            # Use rule-based extraction
            entities = self.rule_based.extract(text)

        # Remove duplicates (same type and overlapping spans)
        entities = self._deduplicate(entities)

        extraction_time = (time.time() - start_time) * 1000

        return ExtractionResult(
            entities=entities,
            text=text,
            extraction_time_ms=extraction_time
        )

    def _extract_with_llm(self, text: str) -> List[Entity]:
        """Extract entities using LLM with structured output"""
        prompt = ENTITY_EXTRACTION_PROMPT.format(text=text)

        # Call LLM with JSON response format
        response = self.llm_service.generate(
            prompt=prompt,
            max_tokens=500,
            temperature=0.1  # Low temperature for structured output
        )

        # Parse JSON response
        try:
            # Find JSON in response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
                entities = []

                for item in data.get('entities', []):
                    entity_type = EntityType(item.get('type', 'CUSTOM'))
                    entities.append(Entity(
                        type=entity_type,
                        value=item.get('value'),
                        raw_text=item.get('raw_text', item.get('value', '')),
                        confidence=item.get('confidence', 0.8),
                        normalized_value=item.get('normalized')
                    ))

                return entities
        except (json.JSONDecodeError, ValueError):
            pass

        # Fall back to rule-based if parsing fails
        return self.rule_based.extract(text)

    def _deduplicate(self, entities: List[Entity]) -> List[Entity]:
        """Remove duplicate entities with overlapping spans"""
        if not entities:
            return entities

        # Sort by start position
        sorted_entities = sorted(entities, key=lambda e: (e.start, -e.confidence))

        result = []
        for entity in sorted_entities:
            # Check if overlaps with any already added entity of same type
            overlaps = False
            for existing in result:
                if existing.type == entity.type:
                    if (existing.start <= entity.start < existing.end or
                        entity.start <= existing.start < entity.end):
                        overlaps = True
                        break

            if not overlaps:
                result.append(entity)

        return result

    def extract_for_intent(
        self,
        text: str,
        intent: str,
        expected_entities: Optional[List[EntityType]] = None
    ) -> ExtractionResult:
        """
        Extract entities with intent-specific hints.

        Args:
            text: The text to extract from
            intent: The classified intent
            expected_entities: List of entity types expected for this intent

        Returns:
            ExtractionResult with focused extraction
        """
        result = self.extract(text)

        # If expected entities specified, prioritize those
        if expected_entities:
            prioritized = []
            for entity in result.entities:
                if entity.type in expected_entities:
                    entity.confidence = min(1.0, entity.confidence + 0.1)
                    prioritized.insert(0, entity)
                else:
                    prioritized.append(entity)
            result.entities = prioritized

        return result


# Slot definitions for common intents
INTENT_SLOT_MAPPING = {
    "set_timer": {
        "required": ["duration"],
        "optional": ["label"],
        "entity_mapping": {
            "duration": EntityType.DURATION,
            "label": EntityType.CUSTOM
        }
    },
    "set_reminder": {
        "required": ["task", "datetime"],
        "optional": [],
        "entity_mapping": {
            "task": EntityType.CUSTOM,
            "datetime": EntityType.DATETIME
        }
    },
    "send_email": {
        "required": ["recipient"],
        "optional": ["subject", "body"],
        "entity_mapping": {
            "recipient": EntityType.EMAIL,
            "subject": EntityType.CUSTOM,
            "body": EntityType.CUSTOM
        }
    },
    "launch_app": {
        "required": ["app_name"],
        "optional": [],
        "entity_mapping": {
            "app_name": EntityType.APP_NAME
        }
    },
    "get_weather": {
        "required": [],
        "optional": ["location", "date"],
        "entity_mapping": {
            "location": EntityType.LOCATION,
            "date": EntityType.DATE
        }
    },
    "calendar_event": {
        "required": ["title", "datetime"],
        "optional": ["location", "duration", "attendees"],
        "entity_mapping": {
            "title": EntityType.CUSTOM,
            "datetime": EntityType.DATETIME,
            "location": EntityType.LOCATION,
            "duration": EntityType.DURATION,
            "attendees": EntityType.PERSON
        }
    }
}


def create_entity_extractor(llm_service=None) -> EntityExtractor:
    """Factory function to create EntityExtractor"""
    return EntityExtractor(llm_service=llm_service)
