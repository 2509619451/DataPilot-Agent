from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.entities import ChatSession, Message


def create_session(db: Session, dataset_id: str) -> ChatSession:
    session = ChatSession(dataset_id=dataset_id)
    db.add(session); db.commit(); db.refresh(session)
    return session


def get_session_or_404(db: Session, session_id: str) -> ChatSession:
    session = db.get(ChatSession, session_id)
    if not session:
        raise HTTPException(404, "会话不存在")
    return session


def add_message(db: Session, session_id: str, role: str, content: str, payload: dict | None = None) -> Message:
    message = Message(session_id=session_id, role=role, content=content, payload=payload)
    db.add(message); db.commit(); db.refresh(message)
    return message


def get_history(db: Session, session_id: str, limit: int = 12) -> list[dict]:
    rows = db.scalars(
        select(Message).where(Message.session_id == session_id).order_by(Message.created_at.desc()).limit(limit)
    ).all()
    rows = list(reversed(rows))
    return [{"role": m.role, "content": m.content, "payload": m.payload or {}} for m in rows]
