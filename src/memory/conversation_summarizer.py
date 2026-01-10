"""
Conversation Summarization Service
Provides intelligent summarization of long conversations to maintain context
while reducing memory footprint and improving performance.

Reference: https://docs.python.org/3/library/dataclasses.html
"""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class SummaryType(str, Enum):
    """Types of conversation summaries"""
    FULL = "full"  # Complete summary
    TOPIC = "topic"  # Topic-based summary
    ACTION = "action"  # Action items summary
    KEY_POINTS = "key_points"  # Key information only


@dataclass
class ConversationTurn:
    """Single turn in a conversation"""
    user_input: str
    assistant_response: str
    timestamp: Optional[str] = None
    intent: Optional[str] = None
    entities: Optional[List[str]] = None


@dataclass
class ConversationSummary:
    """Summary of a conversation segment"""
    summary_text: str
    summary_type: SummaryType
    turns_covered: int
    timestamp: str
    key_topics: List[str]
    action_items: List[str]
    entities_mentioned: List[str]
    start_index: int
    end_index: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert summary to dictionary"""
        return asdict(self)


class ConversationSummarizer:
    """
    Professional conversation summarizer with intelligent compression.
    Maintains context while reducing memory footprint.
    """

    def __init__(self, llm_service=None):
        """
        Initialize conversation summarizer.

        Args:
            llm_service: LLM service for generating summaries (optional)
        """
        self.llm_service = llm_service
        self.summary_threshold = 20  # Summarize after 20 turns
        self.context_window = 10  # Keep last 10 turns in memory
        self.summaries: List[ConversationSummary] = []

        logger.info(
            f"ConversationSummarizer initialized "
            f"(threshold={self.summary_threshold}, context_window={self.context_window})"
        )

    def should_summarize(self, turns_count: int) -> bool:
        """
        Check if conversation should be summarized.

        Args:
            turns_count: Total number of turns so far

        Returns:
            True if summarization is recommended
        """
        return turns_count >= self.summary_threshold

    def extract_key_topics(self, turns: List[ConversationTurn]) -> List[str]:
        """
        Extract key topics from conversation turns.

        Args:
            turns: List of conversation turns

        Returns:
            List of identified key topics
        """
        topics = set()

        # Simple topic extraction based on keywords and intents
        for turn in turns:
            # Extract from intent if available
            if turn.intent:
                topics.add(turn.intent)

            # Extract from entities if available
            if turn.entities:
                topics.update(turn.entities)

            # Extract from response content (simplified)
            response_lower = turn.assistant_response.lower()

            # Topic keywords
            topic_keywords = {
                "weather": ["weather", "temperature", "forecast", "rain", "sunny"],
                "scheduling": ["schedule", "calendar", "meeting", "event", "time"],
                "tasks": ["task", "todo", "complete", "remind", "due"],
                "information": ["tell", "explain", "what", "how", "information"],
                "action": ["send", "create", "post", "update", "delete"],
                "help": ["help", "question", "assistance", "support"],
                "conversation": ["chat", "talk", "discuss", "conversation"]
            }

            for topic, keywords in topic_keywords.items():
                if any(keyword in response_lower for keyword in keywords):
                    topics.add(topic)

        return list(topics)[:10]  # Limit to top 10 topics

    def extract_action_items(self, turns: List[ConversationTurn]) -> List[str]:
        """
        Extract action items from conversation.

        Args:
            turns: List of conversation turns

        Returns:
            List of identified action items
        """
        actions = []

        action_keywords = [
            ("send", "Message to be sent"),
            ("create", "Item to be created"),
            ("schedule", "Event to be scheduled"),
            ("remind", "Reminder to set"),
            ("update", "Item to be updated"),
            ("delete", "Item to be deleted"),
            ("book", "Booking to make"),
            ("call", "Call to make"),
            ("email", "Email to send")
        ]

        for turn in turns:
            response_lower = turn.assistant_response.lower()

            for keyword, action_type in action_keywords:
                if keyword in response_lower:
                    # Extract the action description
                    sentences = turn.assistant_response.split(".")
                    for sentence in sentences:
                        if keyword in sentence.lower():
                            action_text = sentence.strip()
                            if action_text and action_text not in actions:
                                actions.append(action_text)
                            break

        return actions[:5]  # Limit to 5 action items

    def extract_entities(self, turns: List[ConversationTurn]) -> List[str]:
        """
        Extract entities mentioned in conversation.

        Args:
            turns: List of conversation turns

        Returns:
            List of unique entities mentioned
        """
        entities = set()

        for turn in turns:
            if turn.entities:
                entities.update(turn.entities)

        return list(entities)

    def summarize_with_llm(self, turns: List[ConversationTurn]) -> str:
        """
        Generate summary using LLM service.

        Args:
            turns: List of conversation turns to summarize

        Returns:
            Generated summary text
        """
        if not self.llm_service:
            return self._summarize_fallback(turns)

        try:
            # Build conversation text
            conversation_text = "\n".join([
                f"User: {turn.user_input}\nAssistant: {turn.assistant_response}"
                for turn in turns
            ])

            # Create summarization prompt
            prompt = (
                f"Summarize the following conversation in 2-3 sentences, "
                f"capturing the main topics and key information:\n\n"
                f"{conversation_text}\n\n"
                f"Summary:"
            )

            # Use LLM to generate summary
            summary = self.llm_service.generate_response(prompt)

            logger.info(
                f"Generated LLM summary for {len(turns)} turns",
                extra={"summary_length": len(summary)}
            )

            return summary.strip()

        except Exception as e:
            logger.warning(f"LLM summarization failed: {e}, using fallback")
            return self._summarize_fallback(turns)

    def _summarize_fallback(self, turns: List[ConversationTurn]) -> str:
        """
        Generate summary without LLM (fallback method).

        Args:
            turns: List of conversation turns

        Returns:
            Generated summary text
        """
        # Extract key information
        topics = self.extract_key_topics(turns)
        actions = self.extract_action_items(turns)

        # Build summary
        summary_parts = []

        if topics:
            summary_parts.append(f"Topics discussed: {', '.join(topics[:3])}")

        if actions:
            summary_parts.append(f"Action items: {', '.join(actions[:2])}")

        if len(turns) > 0:
            summary_parts.append(f"Conversation spanned {len(turns)} exchanges")

        summary = ". ".join(summary_parts) if summary_parts else "Conversation summary"

        logger.debug(f"Generated fallback summary for {len(turns)} turns")
        return summary

    def create_summary(
        self,
        turns: List[ConversationTurn],
        start_index: int = 0,
        end_index: Optional[int] = None,
        summary_type: SummaryType = SummaryType.FULL
    ) -> ConversationSummary:
        """
        Create a summary of conversation turns.

        Args:
            turns: List of conversation turns to summarize
            start_index: Start index in conversation
            end_index: End index in conversation
            summary_type: Type of summary to create

        Returns:
            ConversationSummary object
        """
        if end_index is None:
            end_index = len(turns)

        summary_turns = turns[start_index:end_index]

        # Generate summary text based on type
        if summary_type == SummaryType.FULL:
            summary_text = self.summarize_with_llm(summary_turns)
        elif summary_type == SummaryType.KEY_POINTS:
            summary_text = self._create_key_points_summary(summary_turns)
        elif summary_type == SummaryType.ACTION:
            summary_text = self._create_action_summary(summary_turns)
        elif summary_type == SummaryType.TOPIC:
            summary_text = self._create_topic_summary(summary_turns)
        else:
            summary_text = self.summarize_with_llm(summary_turns)

        # Create summary object
        summary = ConversationSummary(
            summary_text=summary_text,
            summary_type=summary_type,
            turns_covered=len(summary_turns),
            timestamp=datetime.utcnow().isoformat(),
            key_topics=self.extract_key_topics(summary_turns),
            action_items=self.extract_action_items(summary_turns),
            entities_mentioned=self.extract_entities(summary_turns),
            start_index=start_index,
            end_index=end_index
        )

        self.summaries.append(summary)

        logger.info(
            f"Created {summary_type.value} summary for turns {start_index}-{end_index}",
            extra={
                "turns": len(summary_turns),
                "topics": len(summary.key_topics),
                "actions": len(summary.action_items)
            }
        )

        return summary

    def _create_key_points_summary(self, turns: List[ConversationTurn]) -> str:
        """Create summary of key points only."""
        key_points = []

        for turn in turns:
            # Extract sentences that contain key information
            sentences = turn.assistant_response.split(".")
            for sentence in sentences:
                sentence = sentence.strip()
                if sentence and len(sentence) > 20:
                    # Limit to important-sounding sentences
                    if any(keyword in sentence.lower() for keyword in ["important", "note", "remember", "key"]):
                        key_points.append(sentence)

        if key_points:
            return "Key points: " + "; ".join(key_points[:3])
        else:
            return f"Covered {len(turns)} conversational exchanges"

    def _create_action_summary(self, turns: List[ConversationTurn]) -> str:
        """Create summary of actions discussed."""
        actions = self.extract_action_items(turns)

        if actions:
            return f"Actions identified: {', '.join(actions[:3])}"
        else:
            return f"Conversation covered {len(turns)} turns with no explicit actions"

    def _create_topic_summary(self, turns: List[ConversationTurn]) -> str:
        """Create summary organized by topics."""
        topics = self.extract_key_topics(turns)

        if topics:
            return f"Topics covered: {', '.join(topics[:5])}"
        else:
            return f"General conversation spanning {len(turns)} exchanges"

    def get_summary_history(self) -> List[Dict[str, Any]]:
        """
        Get history of all generated summaries.

        Returns:
            List of summary dictionaries
        """
        return [s.to_dict() for s in self.summaries]

    def get_compressed_context(
        self,
        all_turns: List[ConversationTurn],
        recent_turns_count: int = 10
    ) -> str:
        """
        Get compressed conversation context for new prompt.
        Combines recent turns with summaries of older turns.

        Args:
            all_turns: All conversation turns
            recent_turns_count: Number of recent turns to keep full context

        Returns:
            Compressed context string
        """
        total_turns = len(all_turns)

        if total_turns <= recent_turns_count:
            # Keep all turns
            return self._turns_to_string(all_turns)

        # Build context: summaries + recent turns
        context_parts = []

        # Add summaries of older turns
        if self.summaries:
            latest_summary = self.summaries[-1]
            context_parts.append(f"Previous context: {latest_summary.summary_text}")
            context_parts.append(f"(Topics: {', '.join(latest_summary.key_topics)})")

        # Add recent turns
        context_parts.append("\nRecent conversation:")
        recent_turns = all_turns[-recent_turns_count:]
        context_parts.append(self._turns_to_string(recent_turns))

        return "\n".join(context_parts)

    def _turns_to_string(self, turns: List[ConversationTurn]) -> str:
        """Convert turns to string representation."""
        lines = []

        for turn in turns:
            lines.append(f"User: {turn.user_input}")
            lines.append(f"Assistant: {turn.assistant_response}")

        return "\n".join(lines)

    def clear_history(self) -> None:
        """Clear summary history."""
        self.summaries.clear()
        logger.info("Conversation summary history cleared")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get conversation summarization statistics.

        Returns:
            Statistics dictionary
        """
        total_turns_summarized = sum(s.turns_covered for s in self.summaries)
        unique_topics = set()
        unique_actions = set()

        for summary in self.summaries:
            unique_topics.update(summary.key_topics)
            unique_actions.update(summary.action_items)

        return {
            "total_summaries": len(self.summaries),
            "total_turns_summarized": total_turns_summarized,
            "unique_topics_identified": len(unique_topics),
            "unique_actions_identified": len(unique_actions),
            "avg_turns_per_summary": (
                total_turns_summarized / len(self.summaries)
                if self.summaries else 0
            ),
            "topics": list(unique_topics)[:10],
            "recent_actions": list(unique_actions)[:10]
        }
