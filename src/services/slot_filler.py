"""
Slot Filler Module
Manages slot filling for task-based intents, tracking required and optional
parameters and generating prompts for missing information.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .entity_extractor import EntityType, Entity, ExtractionResult


class SlotStatus(str, Enum):
    """Status of a slot"""
    EMPTY = "empty"
    FILLED = "filled"
    PENDING = "pending"  # Waiting for user input
    CONFIRMED = "confirmed"  # User confirmed the value


@dataclass
class SlotDefinition:
    """Definition of a slot for an intent"""
    name: str
    entity_type: EntityType
    required: bool = True
    prompt: str = ""  # Question to ask if missing
    examples: List[str] = field(default_factory=list)
    default: Optional[Any] = None
    validator: Optional[str] = None  # Validation function name

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "entity_type": self.entity_type.value,
            "required": self.required,
            "prompt": self.prompt,
            "examples": self.examples,
            "default": self.default
        }


@dataclass
class FilledSlot:
    """A slot that has been filled with a value"""
    definition: SlotDefinition
    value: Any
    raw_text: str = ""
    confidence: float = 1.0
    status: SlotStatus = SlotStatus.FILLED
    source: str = "extraction"  # extraction, user_input, default

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.definition.name,
            "value": self.value,
            "raw_text": self.raw_text,
            "confidence": self.confidence,
            "status": self.status.value,
            "source": self.source
        }


@dataclass
class SlotFillingResult:
    """Result of slot filling operation"""
    intent: str
    filled_slots: Dict[str, FilledSlot] = field(default_factory=dict)
    missing_required: List[SlotDefinition] = field(default_factory=list)
    missing_optional: List[SlotDefinition] = field(default_factory=list)
    is_complete: bool = False
    next_prompt: Optional[str] = None

    def get_slot_value(self, name: str) -> Optional[Any]:
        """Get the value of a filled slot"""
        slot = self.filled_slots.get(name)
        return slot.value if slot else None

    def get_all_values(self) -> Dict[str, Any]:
        """Get all filled slot values as a dictionary"""
        return {name: slot.value for name, slot in self.filled_slots.items()}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent": self.intent,
            "filled_slots": {k: v.to_dict() for k, v in self.filled_slots.items()},
            "missing_required": [s.name for s in self.missing_required],
            "missing_optional": [s.name for s in self.missing_optional],
            "is_complete": self.is_complete,
            "next_prompt": self.next_prompt
        }


# Default slot definitions for common intents
DEFAULT_SLOT_DEFINITIONS: Dict[str, List[SlotDefinition]] = {
    "set_timer": [
        SlotDefinition(
            name="duration",
            entity_type=EntityType.DURATION,
            required=True,
            prompt="How long should I set the timer for?",
            examples=["5 minutes", "30 seconds", "1 hour"]
        ),
        SlotDefinition(
            name="label",
            entity_type=EntityType.CUSTOM,
            required=False,
            prompt="What should I call this timer?",
            examples=["cooking timer", "workout timer"],
            default="Timer"
        )
    ],
    "set_alarm": [
        SlotDefinition(
            name="time",
            entity_type=EntityType.TIME,
            required=True,
            prompt="What time should I set the alarm for?",
            examples=["7:00 AM", "6:30 PM", "noon"]
        ),
        SlotDefinition(
            name="label",
            entity_type=EntityType.CUSTOM,
            required=False,
            prompt="What should I call this alarm?",
            default="Alarm"
        ),
        SlotDefinition(
            name="repeat",
            entity_type=EntityType.CUSTOM,
            required=False,
            prompt="Should this alarm repeat?",
            examples=["daily", "weekdays", "once"],
            default="once"
        )
    ],
    "set_reminder": [
        SlotDefinition(
            name="task",
            entity_type=EntityType.CUSTOM,
            required=True,
            prompt="What would you like to be reminded about?",
            examples=["call mom", "take medicine", "meeting at 3pm"]
        ),
        SlotDefinition(
            name="datetime",
            entity_type=EntityType.DATETIME,
            required=True,
            prompt="When should I remind you?",
            examples=["tomorrow at 9am", "in 2 hours", "next Monday"]
        )
    ],
    "send_email": [
        SlotDefinition(
            name="recipient",
            entity_type=EntityType.EMAIL,
            required=True,
            prompt="Who should I send this email to?",
            examples=["john@example.com", "my manager"]
        ),
        SlotDefinition(
            name="subject",
            entity_type=EntityType.CUSTOM,
            required=False,
            prompt="What should the subject be?",
            default="(No subject)"
        ),
        SlotDefinition(
            name="body",
            entity_type=EntityType.CUSTOM,
            required=False,
            prompt="What should the email say?"
        )
    ],
    "launch_app": [
        SlotDefinition(
            name="app_name",
            entity_type=EntityType.APP_NAME,
            required=True,
            prompt="Which application should I open?",
            examples=["Spotify", "Chrome", "Word"]
        )
    ],
    "get_weather": [
        SlotDefinition(
            name="location",
            entity_type=EntityType.LOCATION,
            required=False,
            prompt="For which location?",
            default="current location"
        ),
        SlotDefinition(
            name="date",
            entity_type=EntityType.DATE,
            required=False,
            prompt="For which date?",
            default="today"
        )
    ],
    "search_web": [
        SlotDefinition(
            name="query",
            entity_type=EntityType.CUSTOM,
            required=True,
            prompt="What would you like me to search for?"
        )
    ],
    "calendar_event": [
        SlotDefinition(
            name="title",
            entity_type=EntityType.CUSTOM,
            required=True,
            prompt="What's the name of the event?"
        ),
        SlotDefinition(
            name="datetime",
            entity_type=EntityType.DATETIME,
            required=True,
            prompt="When should the event be scheduled?",
            examples=["tomorrow at 2pm", "next Friday at 10am"]
        ),
        SlotDefinition(
            name="duration",
            entity_type=EntityType.DURATION,
            required=False,
            prompt="How long should the event be?",
            default="1 hour"
        ),
        SlotDefinition(
            name="location",
            entity_type=EntityType.LOCATION,
            required=False,
            prompt="Where will the event take place?"
        ),
        SlotDefinition(
            name="attendees",
            entity_type=EntityType.PERSON,
            required=False,
            prompt="Who should I invite?"
        )
    ],
    "play_music": [
        SlotDefinition(
            name="query",
            entity_type=EntityType.CUSTOM,
            required=False,
            prompt="What would you like to listen to?",
            examples=["jazz music", "the Beatles", "my liked songs"]
        ),
        SlotDefinition(
            name="service",
            entity_type=EntityType.APP_NAME,
            required=False,
            prompt="Which music service?",
            default="Spotify"
        )
    ],
    "navigate_to": [
        SlotDefinition(
            name="destination",
            entity_type=EntityType.LOCATION,
            required=True,
            prompt="Where would you like to go?",
            examples=["home", "work", "nearest gas station"]
        )
    ]
}


class SlotFiller:
    """
    Manages slot filling for task-based intents.

    Tracks required and optional parameters, fills slots from extracted entities,
    and generates prompts for missing information.
    """

    def __init__(
        self,
        slot_definitions: Optional[Dict[str, List[SlotDefinition]]] = None
    ):
        """
        Initialize slot filler.

        Args:
            slot_definitions: Custom slot definitions. Uses defaults if not provided.
        """
        self.slot_definitions = slot_definitions or DEFAULT_SLOT_DEFINITIONS

    def get_slot_definitions(self, intent: str) -> List[SlotDefinition]:
        """Get slot definitions for an intent"""
        return self.slot_definitions.get(intent, [])

    def fill_slots(
        self,
        intent: str,
        extraction_result: ExtractionResult,
        existing_slots: Optional[Dict[str, FilledSlot]] = None
    ) -> SlotFillingResult:
        """
        Fill slots from extracted entities.

        Args:
            intent: The classified intent
            extraction_result: Result from entity extraction
            existing_slots: Previously filled slots (for multi-turn)

        Returns:
            SlotFillingResult with filled and missing slots
        """
        definitions = self.get_slot_definitions(intent)
        filled_slots = dict(existing_slots) if existing_slots else {}
        missing_required = []
        missing_optional = []

        # Try to fill each slot from extracted entities
        for slot_def in definitions:
            if slot_def.name in filled_slots:
                continue  # Already filled

            # Find matching entity
            entity = self._find_matching_entity(
                slot_def.entity_type,
                extraction_result.entities
            )

            if entity:
                filled_slots[slot_def.name] = FilledSlot(
                    definition=slot_def,
                    value=entity.normalized_value or entity.value,
                    raw_text=entity.raw_text,
                    confidence=entity.confidence,
                    status=SlotStatus.FILLED,
                    source="extraction"
                )
            elif slot_def.default is not None:
                # Use default value
                filled_slots[slot_def.name] = FilledSlot(
                    definition=slot_def,
                    value=slot_def.default,
                    raw_text="",
                    confidence=1.0,
                    status=SlotStatus.FILLED,
                    source="default"
                )
            elif slot_def.required:
                missing_required.append(slot_def)
            else:
                missing_optional.append(slot_def)

        # Determine if complete
        is_complete = len(missing_required) == 0

        # Generate next prompt if incomplete
        next_prompt = None
        if missing_required:
            next_prompt = missing_required[0].prompt

        return SlotFillingResult(
            intent=intent,
            filled_slots=filled_slots,
            missing_required=missing_required,
            missing_optional=missing_optional,
            is_complete=is_complete,
            next_prompt=next_prompt
        )

    def fill_slot_from_input(
        self,
        current_result: SlotFillingResult,
        user_input: str,
        extraction_result: ExtractionResult,
        slot_name: Optional[str] = None
    ) -> SlotFillingResult:
        """
        Fill a specific slot from user input in a multi-turn conversation.

        Args:
            current_result: Current slot filling state
            user_input: Raw user input
            extraction_result: Entities extracted from user input
            slot_name: Specific slot to fill (uses next missing if not provided)

        Returns:
            Updated SlotFillingResult
        """
        if not current_result.missing_required:
            return current_result

        # Determine which slot to fill
        if slot_name:
            target_slot = next(
                (s for s in current_result.missing_required if s.name == slot_name),
                None
            )
        else:
            target_slot = current_result.missing_required[0]

        if not target_slot:
            return current_result

        # Find matching entity or use raw input
        entity = self._find_matching_entity(
            target_slot.entity_type,
            extraction_result.entities
        )

        filled_slots = dict(current_result.filled_slots)

        if entity:
            filled_slots[target_slot.name] = FilledSlot(
                definition=target_slot,
                value=entity.normalized_value or entity.value,
                raw_text=entity.raw_text,
                confidence=entity.confidence,
                status=SlotStatus.FILLED,
                source="user_input"
            )
        else:
            # Use raw input as value for CUSTOM types
            if target_slot.entity_type == EntityType.CUSTOM:
                filled_slots[target_slot.name] = FilledSlot(
                    definition=target_slot,
                    value=user_input.strip(),
                    raw_text=user_input,
                    confidence=0.8,
                    status=SlotStatus.FILLED,
                    source="user_input"
                )

        # Recalculate missing slots
        missing_required = [
            s for s in current_result.missing_required
            if s.name not in filled_slots
        ]
        missing_optional = current_result.missing_optional

        is_complete = len(missing_required) == 0
        next_prompt = missing_required[0].prompt if missing_required else None

        return SlotFillingResult(
            intent=current_result.intent,
            filled_slots=filled_slots,
            missing_required=missing_required,
            missing_optional=missing_optional,
            is_complete=is_complete,
            next_prompt=next_prompt
        )

    def _find_matching_entity(
        self,
        entity_type: EntityType,
        entities: List[Entity]
    ) -> Optional[Entity]:
        """Find the best matching entity for a slot type"""
        matching = [e for e in entities if e.type == entity_type]

        if not matching:
            return None

        # Return highest confidence match
        return max(matching, key=lambda e: e.confidence)

    def validate_slot_value(
        self,
        slot_name: str,
        value: Any,
        intent: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate a slot value.

        Returns:
            (is_valid, error_message)
        """
        definitions = self.get_slot_definitions(intent)
        slot_def = next((s for s in definitions if s.name == slot_name), None)

        if not slot_def:
            return True, None

        # Basic validation based on entity type
        if slot_def.entity_type == EntityType.DURATION:
            if isinstance(value, (int, float)) and value <= 0:
                return False, "Duration must be positive"

        elif slot_def.entity_type == EntityType.EMAIL:
            if isinstance(value, str) and '@' not in value:
                return False, "Please provide a valid email address"

        return True, None

    def get_confirmation_prompt(self, result: SlotFillingResult) -> str:
        """Generate a confirmation prompt for filled slots"""
        if not result.is_complete:
            return result.next_prompt or "Please provide the missing information."

        parts = ["I'll "]

        if result.intent == "set_timer":
            duration = result.get_slot_value("duration")
            label = result.get_slot_value("label") or "Timer"
            parts.append(f"set a {duration} timer called '{label}'")

        elif result.intent == "set_reminder":
            task = result.get_slot_value("task")
            when = result.get_slot_value("datetime")
            parts.append(f"remind you to '{task}' at {when}")

        elif result.intent == "send_email":
            recipient = result.get_slot_value("recipient")
            parts.append(f"send an email to {recipient}")

        elif result.intent == "calendar_event":
            title = result.get_slot_value("title")
            when = result.get_slot_value("datetime")
            parts.append(f"create an event '{title}' for {when}")

        else:
            # Generic confirmation
            slots_str = ", ".join(
                f"{name}={slot.value}"
                for name, slot in result.filled_slots.items()
            )
            parts.append(f"execute {result.intent} with {slots_str}")

        parts.append(". Is that correct?")
        return "".join(parts)


def create_slot_filler(
    custom_definitions: Optional[Dict[str, List[SlotDefinition]]] = None
) -> SlotFiller:
    """Factory function to create SlotFiller"""
    return SlotFiller(slot_definitions=custom_definitions)
