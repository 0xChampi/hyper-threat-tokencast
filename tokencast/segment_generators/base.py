"""
Abstract base class for segment generators
"""

from abc import ABC, abstractmethod
from typing import Optional, Any
from ..models import SegmentContext, SegmentOutput


class SegmentGenerator(ABC):
    """
    Abstract base for segment content generation

    Each segment type (TOKEN_LAUNCH, SWARM_ANALYSIS, etc.) has a
    concrete generator that creates content for that segment.
    """

    def __init__(
        self,
        swarm_client: Optional[Any] = None,
        telegram_client: Optional[Any] = None,
        pump_fun_client: Optional[Any] = None
    ):
        """
        Initialize generator with external clients

        Args:
            swarm_client: SWARM API client
            telegram_client: Telegram bot client
            pump_fun_client: Pump.fun API client
        """
        self.swarm = swarm_client
        self.telegram = telegram_client
        self.pump_fun = pump_fun_client

    @abstractmethod
    async def generate_content(self, context: SegmentContext) -> SegmentOutput:
        """
        Generate segment content

        Args:
            context: Segment context with show/segment metadata

        Returns:
            SegmentOutput with speaker notes, visuals, SWARM analysis
        """
        pass

    def _format_speaker_notes(self, **kwargs) -> str:
        """
        Helper to format speaker notes from template

        Override in subclasses for segment-specific formatting
        """
        lines = []
        for key, value in kwargs.items():
            lines.append(f"{key.upper()}: {value}")
        return "\n".join(lines)
