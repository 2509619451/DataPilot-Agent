from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.schemas import SessionCreate, SessionResponse
from app.services.dataset_service import get_dataset_or_404
from app.services.session_service import create_session, get_history, get_session_or_404

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse)
def new_session(body: SessionCreate, db: Session = Depends(get_db)):
    get_dataset_or_404(db, body.dataset_id)
    s = create_session(db, body.dataset_id)
    return SessionResponse(session_id=s.id, dataset_id=s.dataset_id, messages=[])


@router.get("/{session_id}", response_model=SessionResponse)
def session_detail(session_id: str, db: Session = Depends(get_db)):
    s = get_session_or_404(db, session_id)
    return SessionResponse(session_id=s.id, dataset_id=s.dataset_id, messages=get_history(db, s.id, limit=100))
