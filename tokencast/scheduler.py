"""
Tokencast Segment Scheduler

9-segment state machine with automatic transitions
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Callable
from .models import SegmentType, SegmentConfig, ShowConfig

logger = logging.getLogger(__name__)


class SegmentScheduler:
    """
    Manages segment rotation and automatic transitions

    Default rotation (60-minute cycle):
    1. TOKEN_LAUNCH_LIVE (5-10 min)
    2. SWARM_ANALYSIS (8-10 min)
    3. R3LL_MUSIC (5 min)
    4. MEME_ECONOMY (5-10 min)
    5. CRYPTO_DEEP_DIVE (10 min)
    6. COMMUNITY_INTERACTION (5-10 min)
    7. AI_HOST_BREAKDOWN (5-10 min)
    8. NARRATIVE_ALPHA (8-10 min)
    """

    # Default segment durations (in seconds)
    DEFAULT_DURATIONS = {
        SegmentType.TOKEN_LAUNCH_LIVE: 420,      # 7 min
        SegmentType.GAMBA: 360,                  # 6 min
        SegmentType.SWARM_ANALYSIS: 540,         # 9 min
        SegmentType.R3LL_MUSIC: 300,             # 5 min
        SegmentType.MEME_ECONOMY: 420,           # 7 min
        SegmentType.CRYPTO_DEEP_DIVE: 600,       # 10 min
        SegmentType.COMMUNITY_INTERACTION: 420,  # 7 min
        SegmentType.AI_HOST_BREAKDOWN: 540,      # 9 min
        SegmentType.NARRATIVE_ALPHA: 480,        # 8 min
        SegmentType.INTERMISSION: 180,           # 3 min
    }

    def __init__(self, show_config: ShowConfig):
        """
        Initialize scheduler

        Args:
            show_config: Show configuration with rotation order
        """
        self.show_config = show_config
        self.current_index = 0
        self.rotation = show_config.segment_rotation
        self.transition_task: Optional[asyncio.Task] = None
        self.transition_callback: Optional[Callable] = None

    def get_segment_duration(self, segment_type: SegmentType) -> int:
        """Get default duration for segment type"""
        return self.DEFAULT_DURATIONS.get(segment_type, 300)

    def get_next_segment(self) -> SegmentConfig:
        """
        Get next segment in rotation

        Returns:
            SegmentConfig for next segment
        """
        next_index = (self.current_index + 1) % len(self.rotation)
        next_type = self.rotation[next_index]

        return SegmentConfig(
            segment_type=next_type,
            duration_seconds=self.get_segment_duration(next_type)
        )

    def get_current_segment(self) -> SegmentConfig:
        """Get current segment config"""
        current_type = self.rotation[self.current_index]

        return SegmentConfig(
            segment_type=current_type,
            duration_seconds=self.get_segment_duration(current_type)
        )

    def advance_segment(self) -> SegmentConfig:
        """
        Advance to next segment and return it

        Returns:
            SegmentConfig for new current segment
        """
        self.current_index = (self.current_index + 1) % len(self.rotation)
        return self.get_current_segment()

    def peek_upcoming(self, count: int = 3) -> List[SegmentConfig]:
        """
        Preview next N segments without advancing

        Args:
            count: Number of segments to preview

        Returns:
            List of upcoming segment configs
        """
        upcoming = []
        for i in range(1, count + 1):
            index = (self.current_index + i) % len(self.rotation)
            seg_type = self.rotation[index]
            upcoming.append(
                SegmentConfig(
                    segment_type=seg_type,
                    duration_seconds=self.get_segment_duration(seg_type)
                )
            )
        return upcoming

    def schedule_transition(
        self,
        delay_seconds: int,
        callback: Callable
    ) -> asyncio.Task:
        """
        Schedule automatic segment transition

        Args:
            delay_seconds: Time until transition
            callback: Async function to call on transition

        Returns:
            asyncio.Task for the scheduled transition
        """
        self.transition_callback = callback

        async def _delayed_transition():
            """Internal: wait and then call transition callback"""
            try:
                logger.info(f"Scheduling transition in {delay_seconds} seconds")
                await asyncio.sleep(delay_seconds)
                if self.transition_callback:
                    await self.transition_callback()
            except asyncio.CancelledError:
                logger.info("Transition cancelled")
            except Exception as e:
                logger.error(f"Error in scheduled transition: {e}", exc_info=True)

        self.transition_task = asyncio.create_task(_delayed_transition())
        return self.transition_task

    def cancel_scheduled_transition(self):
        """Cancel pending transition"""
        if self.transition_task and not self.transition_task.done():
            self.transition_task.cancel()
            logger.info("Cancelled scheduled segment transition")

    def get_time_remaining(self, segment_started_at: datetime, segment_duration: int) -> int:
        """
        Calculate seconds remaining in current segment

        Args:
            segment_started_at: When segment started
            segment_duration: Segment duration in seconds

        Returns:
            Seconds remaining (or 0 if expired)
        """
        elapsed = (datetime.utcnow() - segment_started_at).total_seconds()
        remaining = max(0, segment_duration - elapsed)
        return int(remaining)

    def reset(self):
        """Reset scheduler to beginning of rotation"""
        self.current_index = 0
        self.cancel_scheduled_transition()
        logger.info("Scheduler reset to beginning of rotation")
