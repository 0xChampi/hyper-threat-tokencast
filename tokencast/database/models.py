"""
SQLAlchemy ORM Models for Tokencast System
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean, Float,
    ForeignKey, Enum, JSON, Text, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()


class ShowStatus(str, enum.Enum):
    """Show status states"""
    SCHEDULED = "scheduled"
    LIVE = "live"
    COMPLETED = "completed"


class SegmentType(str, enum.Enum):
    """Segment types in rotation"""
    TOKEN_LAUNCH_LIVE = "TOKEN_LAUNCH_LIVE"
    GAMBA = "GAMBA"
    SWARM_ANALYSIS = "SWARM_ANALYSIS"
    R3LL_MUSIC = "R3LL_MUSIC"
    MEME_ECONOMY = "MEME_ECONOMY"
    CRYPTO_DEEP_DIVE = "CRYPTO_DEEP_DIVE"
    COMMUNITY_INTERACTION = "COMMUNITY_INTERACTION"
    AI_HOST_BREAKDOWN = "AI_HOST_BREAKDOWN"
    NARRATIVE_ALPHA = "NARRATIVE_ALPHA"


class SegmentStatus(str, enum.Enum):
    """Segment status states"""
    PENDING = "pending"
    LIVE = "live"
    COMPLETED = "completed"


class TrackingStatus(str, enum.Enum):
    """Token tracking status"""
    ACTIVE = "active"
    PAUSED = "paused"
    GRADUATED = "graduated"
    RUGGED = "rugged"


class TokencastShow(Base):
    """Tokencast show record"""
    __tablename__ = "tokencast_shows"

    id = Column(Integer, primary_key=True)
    show_number = Column(Integer, unique=True, nullable=False)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    status = Column(Enum(ShowStatus), default=ShowStatus.SCHEDULED, nullable=False)
    estimated_duration = Column(Integer, nullable=True)  # in minutes
    total_viewers = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    segments = relationship("TokencastSegment", back_populates="show", cascade="all, delete-orphan")
    metrics = relationship("TokencastMetric", back_populates="show", cascade="all, delete-orphan")
    interactions = relationship("CommunityInteraction", back_populates="show", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_shows_status', 'status'),
        Index('idx_shows_started', 'started_at'),
    )


class TokencastSegment(Base):
    """Individual segment within a show"""
    __tablename__ = "tokencast_segments"

    id = Column(Integer, primary_key=True)
    show_id = Column(Integer, ForeignKey('tokencast_shows.id'), nullable=False)
    segment_type = Column(Enum(SegmentType), nullable=False)
    segment_number = Column(Integer, nullable=False)  # Position in rotation
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    status = Column(Enum(SegmentStatus), default=SegmentStatus.PENDING, nullable=False)

    # Content
    content_generated = Column(Text, nullable=True)
    speaker_notes = Column(Text, nullable=True)
    swarm_analysis_data = Column(JSON, nullable=True)

    # Metrics
    viewer_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    show = relationship("TokencastShow", back_populates="segments")
    featured_tokens = relationship("SegmentToken", back_populates="segment", cascade="all, delete-orphan")
    swarm_outputs = relationship("SwarmSegmentOutput", back_populates="segment", cascade="all, delete-orphan")
    interactions = relationship("CommunityInteraction", back_populates="segment", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_segments_show', 'show_id'),
        Index('idx_segments_status', 'status'),
        Index('idx_segments_type', 'segment_type'),
    )


class PumpFunToken(Base):
    """Pump.fun token tracking"""
    __tablename__ = "pump_fun_tokens"

    id = Column(Integer, primary_key=True)
    token_address = Column(String(255), unique=True, nullable=False)
    ticker = Column(String(50), nullable=True)
    mint_address = Column(String(255), nullable=True)

    # Discovery
    discovered_at = Column(DateTime, default=datetime.utcnow)
    price_at_discovery = Column(Float, nullable=True)

    # Current state
    current_price = Column(Float, nullable=True)
    market_cap = Column(Float, nullable=True)
    holders_count = Column(Integer, nullable=True)
    volume_24h = Column(Float, nullable=True)

    # Metadata
    social_links = Column(JSON, nullable=True)  # {twitter, discord, website}
    bonding_curve_address = Column(String(255), nullable=True)

    # Tracking
    last_tracked_at = Column(DateTime, nullable=True)
    tracking_status = Column(Enum(TrackingStatus), default=TrackingStatus.ACTIVE, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    segment_features = relationship("SegmentToken", back_populates="token")

    __table_args__ = (
        Index('idx_tokens_address', 'token_address'),
        Index('idx_tokens_discovered', 'discovered_at'),
        Index('idx_tokens_status', 'tracking_status'),
    )


class SegmentToken(Base):
    """Tokens featured in segments"""
    __tablename__ = "tokencast_segment_tokens"

    id = Column(Integer, primary_key=True)
    segment_id = Column(Integer, ForeignKey('tokencast_segments.id'), nullable=False)
    token_id = Column(Integer, ForeignKey('pump_fun_tokens.id'), nullable=False)
    featured_position = Column(Integer, nullable=False)  # Display order
    analysis_data = Column(JSON, nullable=True)  # SWARM analysis for this token
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    segment = relationship("TokencastSegment", back_populates="featured_tokens")
    token = relationship("PumpFunToken", back_populates="segment_features")

    __table_args__ = (
        Index('idx_segment_tokens_segment', 'segment_id'),
        Index('idx_segment_tokens_token', 'token_id'),
    )


class SwarmSegmentOutput(Base):
    """SWARM agent outputs for segments"""
    __tablename__ = "swarm_segment_outputs"

    id = Column(Integer, primary_key=True)
    segment_id = Column(Integer, ForeignKey('tokencast_segments.id'), nullable=False)
    agent_name = Column(String(50), nullable=False)  # PERCEPTRON, FOOLIO, AZOKA, etc.
    analysis_type = Column(String(100), nullable=False)  # regime_detection, narrative_phase, etc.
    output_data = Column(JSON, nullable=False)
    confidence_score = Column(Float, nullable=True)
    reasoning = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    segment = relationship("TokencastSegment", back_populates="swarm_outputs")

    __table_args__ = (
        Index('idx_swarm_outputs_segment', 'segment_id'),
        Index('idx_swarm_outputs_agent', 'agent_name'),
    )


class CommunityInteraction(Base):
    """Community interactions during show"""
    __tablename__ = "community_interactions"

    id = Column(Integer, primary_key=True)
    show_id = Column(Integer, ForeignKey('tokencast_shows.id'), nullable=False)
    segment_id = Column(Integer, ForeignKey('tokencast_segments.id'), nullable=True)
    user_id = Column(String(255), nullable=False)  # Telegram user ID

    interaction_type = Column(String(50), nullable=False)  # poll_vote, chat_message, token_mention, reaction
    content = Column(Text, nullable=True)
    extra_metadata = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    show = relationship("TokencastShow", back_populates="interactions")
    segment = relationship("TokencastSegment", back_populates="interactions")

    __table_args__ = (
        Index('idx_interactions_show', 'show_id'),
        Index('idx_interactions_segment', 'segment_id'),
        Index('idx_interactions_type', 'interaction_type'),
    )


class TokencastMetric(Base):
    """Metrics and analytics for shows"""
    __tablename__ = "tokencast_metrics"

    id = Column(Integer, primary_key=True)
    show_id = Column(Integer, ForeignKey('tokencast_shows.id'), nullable=False)
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Float, nullable=False)
    extra_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    show = relationship("TokencastShow", back_populates="metrics")

    __table_args__ = (
        Index('idx_metrics_show', 'show_id'),
        Index('idx_metrics_name', 'metric_name'),
    )
