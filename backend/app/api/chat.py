from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.schemas import ChatRequest, ChatResponse
from app.services.agent_service import run_agent, stream_agent

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(body: ChatRequest, db: Session = Depends(get_db)):
    return run_agent(db, body)


@router.post("/stream")
def chat_stream(body: ChatRequest, db: Session = Depends(get_db)):
    return StreamingResponse(stream_agent(db, body), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
