"""
Enhanced Entity Extraction Service
Provides advanced Named Entity Recognition (NER) using spaCy with fallback patterns.
Identifies persons, organizations, locations, dates, times, quantities, and more.

Reference: https://spacy.io/usage/linguistic-features#named-entities
"""

import logging
import re
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

# Try to import spaCy (optional)
try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    logger.warning("spaCy not installed. Using regex-based entity extraction.")


class EntityType(str, Enum):
    """Types of entities to extract"""
    PERSON = "PERSON"
    ORGANIZATION = "ORG"
    LOCATION = "GPE"
    LOCATION_PHYSICAL = "LOC"
    DATE = "DATE"
    TIME = "TIME"
    QUANTITY = "QUANTITY"
    MONEY = "MONEY"
    PERCENT = "PERCENT"
    PRODUCT = "PRODUCT"
    EVENT = "EVENT"
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    URL = "URL"
    IP_ADDRESS = "IP_ADDRESS"


@dataclass
class Entity:
    """Extracted entity with metadata"""
    text: str
    type: EntityType
    confidence: float = 0.95
    start_pos: Optional[int] = None
    end_pos: Optional[int] = None
    context: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class PatternMatcher:
    """Pattern-based entity extraction for when spaCy is unavailable"""

    # Email pattern
    EMAIL_PATTERN = re.compile(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    )

    # Phone pattern (US format mostly)
    PHONE_PATTERN = re.compile(
        r'(?:\+1[-.\s]?)?\(?[2-9]\d{2}\)?[-.\s]?[2-9]\d{2}[-.\s]?\d{4}\b'
    )

    # URL pattern
    URL_PATTERN = re.compile(
        r'https?://[^\s]+|www\.[^\s]+'
    )

    # IP address pattern
    IP_PATTERN = re.compile(
        r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
    )

    # Money pattern
    MONEY_PATTERN = re.compile(
        r'[$£€¥]\s*[\d,]+\.?\d*|[\d,]+\.?\d*\s*(?:dollars?|cents?|euros?|pounds?|yen)'
    )

    # Percentage pattern
    PERCENT_PATTERN = re.compile(
        r'\d+\.?\d*\s*%'
    )

    # Time pattern
    TIME_PATTERN = re.compile(
        r'\b(?:0?[0-9]|1[0-9]|2[0-3]):[0-5][0-9](?::[0-5][0-9])?\s*(?:am|pm|AM|PM)?\b'
    )

    # Date patterns
    DATE_PATTERNS = [
        re.compile(r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b'),  # MM/DD/YYYY or DD/MM/YYYY
        re.compile(r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}(?:,?\s+\d{4})?\b', re.IGNORECASE),
        re.compile(r'\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|Mon|Tue|Wed|Thu|Fri|Sat|Sun)\b', re.IGNORECASE),
    ]

    @classmethod
    def extract(cls, text: str) -> List[Entity]:
        """Extract entities using regex patterns"""
        entities = []

        # Email extraction
        for match in cls.EMAIL_PATTERN.finditer(text):
            entities.append(Entity(
                text=match.group(),
                type=EntityType.EMAIL,
                confidence=0.99,
                start_pos=match.start(),
                end_pos=match.end()
            ))

        # Phone extraction
        for match in cls.PHONE_PATTERN.finditer(text):
            entities.append(Entity(
                text=match.group(),
                type=EntityType.PHONE,
                confidence=0.95,
                start_pos=match.start(),
                end_pos=match.end()
            ))

        # URL extraction
        for match in cls.URL_PATTERN.finditer(text):
            entities.append(Entity(
                text=match.group(),
                type=EntityType.URL,
                confidence=0.99,
                start_pos=match.start(),
                end_pos=match.end()
            ))

        # IP address extraction
        for match in cls.IP_PATTERN.finditer(text):
            entities.append(Entity(
                text=match.group(),
                type=EntityType.IP_ADDRESS,
                confidence=0.95,
                start_pos=match.start(),
                end_pos=match.end()
            ))

        # Money extraction
        for match in cls.MONEY_PATTERN.finditer(text):
            entities.append(Entity(
                text=match.group(),
                type=EntityType.MONEY,
                confidence=0.90,
                start_pos=match.start(),
                end_pos=match.end()
            ))

        # Percentage extraction
        for match in cls.PERCENT_PATTERN.finditer(text):
            entities.append(Entity(
                text=match.group(),
                type=EntityType.PERCENT,
                confidence=0.95,
                start_pos=match.start(),
                end_pos=match.end()
            ))

        # Time extraction
        for match in cls.TIME_PATTERN.finditer(text):
            entities.append(Entity(
                text=match.group(),
                type=EntityType.TIME,
                confidence=0.90,
                start_pos=match.start(),
                end_pos=match.end()
            ))

        # Date extraction
        for pattern in cls.DATE_PATTERNS:
            for match in pattern.finditer(text):
                # Check if not already extracted
                if not any(
                    e.start_pos == match.start() and e.end_pos == match.end()
                    for e in entities
                ):
                    entities.append(Entity(
                        text=match.group(),
                        type=EntityType.DATE,
                        confidence=0.85,
                        start_pos=match.start(),
                        end_pos=match.end()
                    ))

        return entities


class EnhancedEntityExtractor:
    """
    Professional entity extraction using spaCy with fallback patterns.
    Identifies and classifies various types of entities in text.
    """

    def __init__(self, use_spacy: bool = True):
        """
        Initialize entity extractor.

        Args:
            use_spacy: Whether to try using spaCy (if available)
        """
        self.use_spacy = use_spacy and SPACY_AVAILABLE
        self.nlp = None
        self.pattern_matcher = PatternMatcher()

        # Load spaCy model if requested
        if self.use_spacy:
            try:
                self.nlp = spacy.load("en_core_web_sm")
                logger.info("spaCy NER model loaded successfully")
            except OSError:
                logger.warning(
                    "spaCy model 'en_core_web_sm' not found. "
                    "Install with: python -m spacy download en_core_web_sm"
                )
                self.use_spacy = False

        if not self.use_spacy:
            logger.info("Using regex-based entity extraction")

    def extract(self, text: str) -> Dict[str, List[Entity]]:
        """
        Extract all entities from text.

        Args:
            text: Text to extract entities from

        Returns:
            Dictionary with entities grouped by type
        """
        entities = []

        # Try spaCy first
        if self.use_spacy and self.nlp:
            entities.extend(self._extract_spacy(text))

        # Always add pattern-based extractions (they're usually more reliable)
        pattern_entities = self.pattern_matcher.extract(text)
        entities.extend(pattern_entities)

        # Remove duplicates based on position
        unique_entities = []
        seen_positions = set()

        for entity in sorted(entities, key=lambda e: e.confidence, reverse=True):
            if entity.start_pos is not None and entity.end_pos is not None:
                pos = (entity.start_pos, entity.end_pos)
                if pos not in seen_positions:
                    unique_entities.append(entity)
                    seen_positions.add(pos)

        # Group by type
        grouped = {}
        for entity in unique_entities:
            if entity.type not in grouped:
                grouped[entity.type] = []
            grouped[entity.type].append(entity)

        logger.debug(f"Extracted {len(unique_entities)} entities from text")

        return grouped

    def _extract_spacy(self, text: str) -> List[Entity]:
        """Extract entities using spaCy NER"""
        try:
            doc = self.nlp(text)
            entities = []

            for ent in doc.ents:
                # Map spaCy label to EntityType
                entity_type = self._map_spacy_label(ent.label_)

                if entity_type:
                    entities.append(Entity(
                        text=ent.text,
                        type=entity_type,
                        confidence=0.85,  # spaCy confidence average
                        start_pos=ent.start_char,
                        end_pos=ent.end_char,
                        context=ent.label_
                    ))

            return entities

        except Exception as e:
            logger.warning(f"spaCy extraction failed: {e}")
            return []

    @staticmethod
    def _map_spacy_label(label: str) -> Optional[EntityType]:
        """Map spaCy NER label to EntityType"""
        mapping = {
            "PERSON": EntityType.PERSON,
            "ORG": EntityType.ORGANIZATION,
            "GPE": EntityType.LOCATION,
            "LOC": EntityType.LOCATION_PHYSICAL,
            "DATE": EntityType.DATE,
            "TIME": EntityType.TIME,
            "QUANTITY": EntityType.QUANTITY,
            "MONEY": EntityType.MONEY,
            "PERCENT": EntityType.PERCENT,
            "PRODUCT": EntityType.PRODUCT,
            "EVENT": EntityType.EVENT,
            "FAC": EntityType.LOCATION_PHYSICAL,
            "NORP": EntityType.ORGANIZATION,
            "LANGUAGE": EntityType.PERSON,
        }

        return mapping.get(label)

    def extract_by_type(self, text: str, entity_type: EntityType) -> List[Entity]:
        """
        Extract specific entity type.

        Args:
            text: Text to extract from
            entity_type: Type of entity to extract

        Returns:
            List of extracted entities of specified type
        """
        all_entities = self.extract(text)
        return all_entities.get(entity_type, [])

    def extract_summary(self, text: str) -> Dict[str, Any]:
        """
        Get summary of all extracted entities.

        Args:
            text: Text to analyze

        Returns:
            Summary dictionary with entity counts and samples
        """
        entities = self.extract(text)

        summary = {}
        for entity_type, entity_list in entities.items():
            summary[entity_type.value] = {
                "count": len(entity_list),
                "samples": [e.text for e in entity_list[:3]],
                "all": [e.text for e in entity_list]
            }

        return summary

    def has_entity_type(self, text: str, entity_type: EntityType) -> bool:
        """Check if text contains specific entity type"""
        entities = self.extract_by_type(text, entity_type)
        return len(entities) > 0

    def get_people(self, text: str) -> List[str]:
        """Extract all person names"""
        return [e.text for e in self.extract_by_type(text, EntityType.PERSON)]

    def get_organizations(self, text: str) -> List[str]:
        """Extract all organization names"""
        return [e.text for e in self.extract_by_type(text, EntityType.ORGANIZATION)]

    def get_locations(self, text: str) -> List[str]:
        """Extract all location names"""
        locations = []
        for entity_type in [EntityType.LOCATION, EntityType.LOCATION_PHYSICAL]:
            locations.extend([e.text for e in self.extract_by_type(text, entity_type)])
        return locations

    def get_dates(self, text: str) -> List[str]:
        """Extract all dates"""
        return [e.text for e in self.extract_by_type(text, EntityType.DATE)]

    def get_contact_info(self, text: str) -> Dict[str, List[str]]:
        """Extract contact information (emails, phones)"""
        return {
            "emails": [e.text for e in self.extract_by_type(text, EntityType.EMAIL)],
            "phones": [e.text for e in self.extract_by_type(text, EntityType.PHONE)],
            "urls": [e.text for e in self.extract_by_type(text, EntityType.URL)]
        }
