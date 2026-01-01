"""
Tokencast Orchestrator

Main engine for running live cryptocurrency shows with 9 rotating segments.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from .models import ShowConfig, ShowState, SegmentContext, SegmentOutput, SegmentType
from .scheduler import SegmentScheduler
from .database.models import (
    TokencastShow, TokencastSegment, ShowStatus, SegmentStatus
)

logger = logging.getLogger(__name__)


class TokencastOrchestrator:
    """
    Main orchestration engine for tokencast shows

    Responsibilities:
    - Show lifecycle management (start/end)
    - Segment transitions (automatic and manual)
    - Integration with SWARM, Telegram, segment generators
    - Database persistence
    """

    def __init__(
        self,
        db_session: Session,
        swarm_client: Optional[Any] = None,
        telegram_bot: Optional[Any] = None,
        pump_fun_client: Optional[Any] = None
    ):
        """
        Initialize orchestrator

        Args:
            db_session: SQLAlchemy database session
            swarm_client: SWARM API client (optional)
            telegram_bot: Telegram bot instance (optional)
            pump_fun_client: Pump.fun API client (optional)
        """
        self.db = db_session
        self.swarm = swarm_client
        self.telegram = telegram_bot
        self.pump_fun = pump_fun_client

        # Runtime state
        self.current_show: Optional[ShowState] = None
        self.scheduler: Optional[SegmentScheduler] = None
        self.segment_generators: Dict[SegmentType, Any] = {}

    async def start_show(self, config: Optional[ShowConfig] = None) -> ShowState:
        """
        Start a new tokencast show

        Args:
            config: Show configuration (uses defaults if not provided)

        Returns:
            ShowState for the new show
        """
        if self.current_show:
            raise RuntimeError(f"Show {self.current_show.show_id} is already running")

        # Use default config if not provided
        if config is None:
            config = ShowConfig()

        # Get next show number
        last_show = self.db.query(TokencastShow).order_by(
            TokencastShow.show_number.desc()
        ).first()
        next_show_number = (last_show.show_number + 1) if last_show else 1

        # Create show record
        show = TokencastShow(
            show_number=next_show_number,
            started_at=datetime.utcnow(),
            status=ShowStatus.LIVE,
            estimated_duration=config.estimated_duration_minutes
        )
        self.db.add(show)
        self.db.commit()
        self.db.refresh(show)

        # Initialize scheduler
        self.scheduler = SegmentScheduler(config)

        # Create show state
        self.current_show = ShowState(
            show_id=show.id,
            show_number=show.show_number,
            current_segment_id=None,
            started_at=show.started_at,
            status="live"
        )

        logger.info(f"Started show #{show.show_number} (ID: {show.id})")

        # Start first segment
        await self.start_next_segment()

        # Broadcast to Telegram if configured
        if self.telegram and config.telegram_group_ids:
            await self._broadcast_show_start(config.telegram_group_ids)

        return self.current_show

    async def start_next_segment(self):
        """
        Start the next segment in rotation

        This is called:
        - When show starts (first segment)
        - When automatic transition fires
        - When manual transition requested
        """
        if not self.current_show or not self.scheduler:
            raise RuntimeError("No show is currently running")

        # End current segment if exists
        if self.current_show.current_segment_id:
            await self._end_current_segment()

        # Get next segment config
        segment_config = self.scheduler.advance_segment()

        # Create segment record
        segment = TokencastSegment(
            show_id=self.current_show.show_id,
            segment_type=segment_config.segment_type,
            segment_number=self.current_show.total_segments_completed + 1,
            started_at=datetime.utcnow(),
            duration_seconds=segment_config.duration_seconds,
            status=SegmentStatus.LIVE
        )
        self.db.add(segment)
        self.db.commit()
        self.db.refresh(segment)

        # Update show state
        self.current_show.current_segment_id = segment.id
        self.current_show.total_segments_completed += 1

        logger.info(
            f"Started segment #{segment.segment_number}: {segment_config.segment_type.value} "
            f"(duration: {segment_config.duration_seconds}s)"
        )

        # Generate segment content (async)
        await self._generate_segment_content(segment, segment_config)

        # Schedule automatic transition
        if self.scheduler.show_config.auto_transition:
            self.scheduler.schedule_transition(
                delay_seconds=segment_config.duration_seconds,
                callback=self.start_next_segment
            )

    async def _end_current_segment(self):
        """End the current segment and save metrics"""
        if not self.current_show or not self.current_show.current_segment_id:
            return

        segment = self.db.query(TokencastSegment).filter_by(
            id=self.current_show.current_segment_id
        ).first()

        if segment:
            segment.ended_at = datetime.utcnow()
            segment.status = SegmentStatus.COMPLETED

            # Calculate actual duration
            if segment.started_at:
                duration = (segment.ended_at - segment.started_at).total_seconds()
                segment.duration_seconds = int(duration)

            self.db.commit()

            logger.info(
                f"Ended segment #{segment.segment_number}: {segment.segment_type.value} "
                f"(actual duration: {segment.duration_seconds}s)"
            )

    async def _generate_segment_content(
        self,
        segment: TokencastSegment,
        config: Any
    ):
        """
        Generate content for segment using appropriate generator

        Args:
            segment: Segment database record
            config: Segment configuration
        """
        # Build context for generator
        context = SegmentContext(
            show_id=self.current_show.show_id,
            segment_id=segment.id,
            segment_type=config.segment_type,
            segment_duration=config.duration_seconds
        )

        # Get appropriate generator
        generator = self.segment_generators.get(config.segment_type)

        if not generator:
            logger.warning(f"No generator for {config.segment_type.value}, using default notes")
            segment.speaker_notes = f"Segment: {config.segment_type.value}\nDuration: {config.duration_seconds}s"
            self.db.commit()
            return

        # Generate content
        try:
            output: SegmentOutput = await generator.generate_content(context)

            # Save to database
            segment.speaker_notes = output.speaker_notes
            segment.content_generated = output.speaker_notes[:5000]  # Truncate if needed
            segment.swarm_analysis_data = {
                "swarm_analyses": output.swarm_analyses,
                "featured_tokens": output.featured_tokens,
                "metadata": output.metadata
            }

            self.db.commit()

            logger.info(f"Generated content for segment #{segment.segment_number}")

        except Exception as e:
            logger.error(f"Error generating segment content: {e}", exc_info=True)
            segment.speaker_notes = f"Error generating content for {config.segment_type.value}"
            self.db.commit()

    async def end_show(self):
        """End the current show"""
        if not self.current_show:
            raise RuntimeError("No show is currently running")

        # End current segment
        if self.current_show.current_segment_id:
            await self._end_current_segment()

        # Cancel any scheduled transitions
        if self.scheduler:
            self.scheduler.cancel_scheduled_transition()

        # Update show record
        show = self.db.query(TokencastShow).filter_by(
            id=self.current_show.show_id
        ).first()

        if show:
            show.ended_at = datetime.utcnow()
            show.status = ShowStatus.COMPLETED
            self.db.commit()

            logger.info(f"Ended show #{show.show_number}")

        # Clear runtime state
        self.current_show = None
        self.scheduler = None

    async def manual_transition(self):
        """Manually trigger transition to next segment"""
        if not self.current_show or not self.scheduler:
            raise RuntimeError("No show is currently running")

        # Cancel automatic transition
        self.scheduler.cancel_scheduled_transition()

        # Start next segment
        await self.start_next_segment()

        logger.info("Manual transition triggered")

    def get_current_state(self) -> Optional[ShowState]:
        """Get current show state"""
        return self.current_show

    def get_upcoming_segments(self, count: int = 3) -> list:
        """Get upcoming segments in queue"""
        if not self.scheduler:
            return []
        return self.scheduler.peek_upcoming(count)

    def register_segment_generator(self, segment_type: SegmentType, generator: Any):
        """
        Register a segment generator

        Args:
            segment_type: Type of segment this generator handles
            generator: Generator instance (must have generate_content method)
        """
        self.segment_generators[segment_type] = generator
        logger.info(f"Registered generator for {segment_type.value}")

    async def _broadcast_show_start(self, group_ids: list):
        """Broadcast show start to Telegram groups"""
        if not self.telegram:
            return

        message = f"""
🎬 HYPER-THREAT TOKENCAST LIVE! 🎬

Show #{self.current_show.show_number} is now streaming.

Next segments:
{self._format_upcoming_segments()}

Get ready for market intelligence, pump.fun launches, and SWARM analysis!
        """

        for group_id in group_ids:
            try:
                await self.telegram.send_message(
                    chat_id=group_id,
                    text=message.strip()
                )
            except Exception as e:
                logger.error(f"Failed to broadcast to group {group_id}: {e}")

    def _format_upcoming_segments(self) -> str:
        """Format upcoming segments for display"""
        if not self.scheduler:
            return "No segments scheduled"

        upcoming = self.scheduler.peek_upcoming(3)
        lines = []
        for i, seg in enumerate(upcoming, 1):
            duration_min = seg.duration_seconds // 60
            lines.append(f"{i}. {seg.segment_type.value} ({duration_min} min)")

        return "\n".join(lines)
