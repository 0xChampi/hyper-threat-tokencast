"""
COMMUNITY INTERACTION segment generator

Highlights community polls, Q&A, and engagement from Telegram.
"""

import logging
from ..models import SegmentContext, SegmentOutput
from .base import SegmentGenerator

logger = logging.getLogger(__name__)


class CommunityInteractionGenerator(SegmentGenerator):
    """Generate content for COMMUNITY INTERACTION segment"""

    async def generate_content(self, context: SegmentContext) -> SegmentOutput:
        """
        Generate COMMUNITY INTERACTION segment content

        Workflow:
        1. Review community feedback from previous segments
        2. Highlight popular token mentions
        3. Feature community questions
        """
        speaker_notes = [
            "=== COMMUNITY INTERACTION ===",
            "",
            "Time to hear from the community!",
            ""
        ]

        # Check for community feedback in context
        feedback = context.community_feedback or {}

        if feedback:
            speaker_notes.append("Community Highlights:")

            # Token mentions
            if feedback.get("token_mentions"):
                speaker_notes.append("")
                speaker_notes.append("Most Mentioned Tokens:")
                for token, count in list(feedback["token_mentions"].items())[:5]:
                    speaker_notes.append(f"  • ${token}: {count} mentions")

            # Questions
            if feedback.get("questions"):
                speaker_notes.append("")
                speaker_notes.append("Top Community Questions:")
                for i, q in enumerate(feedback["questions"][:3], 1):
                    speaker_notes.append(f"  {i}. {q}")

        else:
            speaker_notes.append("No community feedback captured yet.")
            speaker_notes.append("Drop your questions and token mentions in the chat!")

        speaker_notes.append("")
        speaker_notes.append("Keep engaging - your input shapes the show!")

        return SegmentOutput(
            speaker_notes="\n".join(speaker_notes),
            featured_tokens=[],
            swarm_analyses=[],
            metadata={"has_feedback": bool(feedback)}
        )
