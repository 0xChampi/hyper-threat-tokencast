"""
Tokencast Show Management Routes

/api/tokencast/* endpoints for managing shows and segments
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from ..database.schemas import ShowCreate, ShowResponse, SegmentResponse
from ..database.models import TokencastShow, TokencastSegment, ShowStatus
from ..orchestrator import TokencastOrchestrator
from ..models import ShowConfig

router = APIRouter(prefix="/api/tokencast", tags=["Tokencast"])

# Global orchestrator instance (set by main app)
_orchestrator: Optional[TokencastOrchestrator] = None


def set_orchestrator(orchestrator: TokencastOrchestrator):
    """Set the global orchestrator instance"""
    global _orchestrator
    _orchestrator = orchestrator


def get_orchestrator() -> TokencastOrchestrator:
    """Get the global orchestrator"""
    if not _orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    return _orchestrator


@router.get("/current")
async def get_current_show(orchestrator: TokencastOrchestrator = Depends(get_orchestrator)):
    """Get current live show state"""
    state = orchestrator.get_current_state()

    if not state:
        raise HTTPException(status_code=404, detail="No show currently running")

    return {
        "show_id": state.show_id,
        "show_number": state.show_number,
        "current_segment_id": state.current_segment_id,
        "current_segment_index": state.current_segment_index,
        "started_at": state.started_at,
        "status": state.status,
        "total_segments_completed": state.total_segments_completed,
        "viewer_count": state.viewer_count,
        "upcoming_segments": [
            {"type": seg.segment_type.value, "duration_seconds": seg.duration_seconds}
            for seg in orchestrator.get_upcoming_segments(3)
        ]
    }


@router.post("/start", response_model=ShowResponse)
async def start_show(
    request: ShowCreate,
    db: Session = Depends(get_db),
    orchestrator: TokencastOrchestrator = Depends(get_orchestrator)
):
    """Start a new tokencast show"""
    try:
        config = ShowConfig(estimated_duration_minutes=request.estimated_duration)
        state = await orchestrator.start_show(config)

        # Get show from database
        show = db.query(TokencastShow).filter_by(id=state.show_id).first()

        if not show:
            raise HTTPException(status_code=500, detail="Show created but not found in database")

        return show

    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start show: {str(e)}")


@router.post("/end")
async def end_show(orchestrator: TokencastOrchestrator = Depends(get_orchestrator)):
    """End the current show"""
    try:
        await orchestrator.end_show()
        return {"status": "success", "message": "Show ended"}
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to end show: {str(e)}")


@router.get("/show/{show_id}")
async def get_show(show_id: int, db: Session = Depends(get_db)):
    """Get details for a specific show"""
    show = db.query(TokencastShow).filter_by(id=show_id).first()

    if not show:
        raise HTTPException(status_code=404, detail=f"Show {show_id} not found")

    # Get segments
    segments = db.query(TokencastSegment).filter_by(show_id=show_id).order_by(TokencastSegment.segment_number).all()

    return {
        "show": show,
        "segments": segments,
        "total_segments": len(segments)
    }


@router.get("/segments/current")
async def get_current_segment(
    db: Session = Depends(get_db),
    orchestrator: TokencastOrchestrator = Depends(get_orchestrator)
):
    """Get the current active segment"""
    state = orchestrator.get_current_state()

    if not state or not state.current_segment_id:
        raise HTTPException(status_code=404, detail="No active segment")

    segment = db.query(TokencastSegment).filter_by(id=state.current_segment_id).first()

    if not segment:
        raise HTTPException(status_code=404, detail="Active segment not found in database")

    return segment


@router.post("/segments/transition")
async def manual_transition(orchestrator: TokencastOrchestrator = Depends(get_orchestrator)):
    """Manually trigger transition to next segment"""
    try:
        await orchestrator.manual_transition()
        return {"status": "success", "message": "Transitioned to next segment"}
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transition failed: {str(e)}")
