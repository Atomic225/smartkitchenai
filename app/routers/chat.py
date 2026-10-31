from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ChatMessage
from app.schemas import ChatRequest, ChatResponse
from app.services.ai_chat import chat

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def post_chat(payload: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    result = chat(db, payload.message)
    return ChatResponse(**result)


@router.get("/history")
def history(db: Session = Depends(get_db), limit: int = 50) -> list[dict]:
    rows = db.query(ChatMessage).order_by(ChatMessage.id.desc()).limit(limit).all()
    return [
        {"id": row.id, "role": row.role, "content": row.content, "created_at": row.created_at.isoformat()}
        for row in reversed(rows)
    ]
