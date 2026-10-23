"""API routes for contextual AI chat, grounded multi-mode discussions, and conversation history."""
from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.llm.gateway import LLMGateway, get_llm_gateway
from app.models.user import User
from app.schemas.chat import (
    ChatMessageResponse,
    ChatRequest,
    ConversationDetailResponse,
    ConversationSummaryResponse,
)
from app.services.chat_service import ChatService

router = APIRouter(prefix="/ai", tags=["ai-chat"])


def get_chat_service(
    db: AsyncSession = Depends(get_db),
    gateway: LLMGateway = Depends(get_llm_gateway),
) -> ChatService:
    return ChatService(db, gateway=gateway)


@router.post(
    "/chat",
    response_model=ChatMessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Send message to AI academic advisor with grounded context",
)
async def chat(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> ChatMessageResponse:
    """Send message to AI advisor in one of the 4 context modes.

    - Grounded strictly in retrieved catalog, roadmap, skill, or interview data.
    - Evaluates safety pre-check before calling AI.
    - Transaction closed during external AI call.
    - Rate limited to 30 requests/hour.
    """
    return await service.send_message(current_user, req)


@router.get(
    "/conversations",
    response_model=List[ConversationSummaryResponse],
    status_code=status.HTTP_200_OK,
    summary="List active conversation histories for current user",
)
async def list_conversations(
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> List[ConversationSummaryResponse]:
    """List all chat conversations belonging to the authenticated user."""
    return await service.list_conversations(current_user)


@router.get(
    "/conversations/{id}",
    response_model=ConversationDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get conversation detail and transcript",
)
async def get_conversation(
    id: UUID,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> ConversationDetailResponse:
    """Retrieve full transcript of a conversation. Returns 404 for other users' conversations."""
    return await service.get_conversation_detail(current_user, id)


@router.delete(
    "/conversations/{id}",
    status_code=status.HTTP_200_OK,
    summary="Delete conversation and its message history",
)
async def delete_conversation(
    id: UUID,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> Dict[str, Any]:
    """Delete a conversation. Returns 404 for other users' conversations."""
    return await service.delete_conversation(current_user, id)
