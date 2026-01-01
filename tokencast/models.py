"""
Tokencast domain models (Pydantic)

These are NOT database models - they're used for business logic and validation.
For database models, see tokencast/database/models.py
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class SegmentType(str, Enum):
    """Segment types in the 9-segment rotation"""
    TOKEN_LAUNCH_LIVE = "TOKEN_LAUNCH_LIVE"
    GAMBA = "GAMBA"
    SWARM_ANALYSIS = "SWARM_ANALYSIS"
    R3LL_MUSIC = "R3LL_MUSIC"
    MEME_ECONOMY = "MEME_ECONOMY"
    CRYPTO_DEEP_DIVE = "CRYPTO_DEEP_DIVE"
    COMMUNITY_INTERACTION = "COMMUNITY_INTERACTION"
    AI_HOST_BREAKDOWN = "AI_HOST_BREAKDOWN"
    NARRATIVE_ALPHA = "NARRATIVE_ALPHA"
    INTERMISSION = "INTERMISSION"  # Flexible segment for breaks


class SegmentConfig(BaseModel):
    """Configuration for a segment"""
    segment_type: SegmentType
    duration_seconds: int = Field(300, description="Default 5 minutes")
    featured_token: Optional[str] = None  # Token address if applicable
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SegmentContext(BaseModel):
    """Context passed to segment generators"""
    show_id: int
    segment_id: int
    segment_type: SegmentType
    segment_duration: int  # seconds
    previous_segment_data: Optional[Dict[str, Any]] = None
    featured_tokens: List[str] = Field(default_factory=list)  # Token addresses
    community_feedback: Dict[str, Any] = Field(default_factory=dict)


class SegmentOutput(BaseModel):
    """Output from a segment generator"""
    speaker_notes: str = Field(..., description="Notes for AI host to present")
    visual_data: Dict[str, Any] = Field(default_factory=dict, description="Data for overlays/charts")
    swarm_analyses: List[Dict[str, Any]] = Field(default_factory=list)
    featured_tokens: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ShowConfig(BaseModel):
    """Configuration for a tokencast show"""
    estimated_duration_minutes: int = 60
    auto_transition: bool = True
    segment_rotation: List[SegmentType] = Field(
        default_factory=lambda: [
            SegmentType.TOKEN_LAUNCH_LIVE,
            SegmentType.SWARM_ANALYSIS,
            SegmentType.R3LL_MUSIC,
            SegmentType.MEME_ECONOMY,
            SegmentType.CRYPTO_DEEP_DIVE,
            SegmentType.COMMUNITY_INTERACTION,
            SegmentType.AI_HOST_BREAKDOWN,
            SegmentType.NARRATIVE_ALPHA
        ]
    )
    telegram_group_ids: List[int] = Field(default_factory=list)


class ShowState(BaseModel):
    """Current state of a running show"""
    show_id: int
    show_number: int
    current_segment_id: Optional[int]
    current_segment_index: int = 0
    started_at: datetime
    status: str  # "live", "paused", "completed"
    total_segments_completed: int = 0
    viewer_count: int = 0
