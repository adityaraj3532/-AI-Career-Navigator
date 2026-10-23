"""AI Chat Service orchestrating context retrieval, safety checks, gateway calls, and message ledger."""
from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.safety_config import SUPPORTIVE_SAFETY_MESSAGE, check_distress_safety
from app.llm.gateway import LLMGateway
from app.models.career import Career
from app.models.chat import ChatConversation, ChatMessage
from app.models.user import User
from app.schemas.chat import (
    AIChatOutput,
    ChatMessageResponse,
    ChatRequest,
    ChatSource,
    ConversationDetailResponse,
    ConversationSummaryResponse,
)
from app.services.chat_context_service import (
    FIXED_FALLBACK_ANSWER,
    NO_ROADMAP_ANSWER,
    ChatContextService,
    sanitize_untrusted_text,
    validate_citations_and_build_sources,
)
from app.services.chat_rate_limiter import check_chat_rate_limit

logger = logging.getLogger("app.chat_service")

MAX_CONVERSATIONS_PER_USER = 20
MAX_MESSAGES_PER_CONVERSATION = 50
MAX_HISTORY_MESSAGES_FOR_PROMPT = 6


class ChatService:
    def __init__(self, session: AsyncSession, gateway: Optional[LLMGateway] = None):
        self.session = session
        self.gateway = gateway

    async def send_message(self, user: User, req: ChatRequest) -> ChatMessageResponse:
        """Process user chat message with transaction isolation, safety pre-check, and context grounding."""
        # 1. Rate limiting
        await check_chat_rate_limit(user.id)

        clean_user_message = sanitize_untrusted_text(req.message, max_len=1000)

        # ----------------------------------------------------------------------
        # PHASE 1: Load Context & Conversation (Short Transaction)
        # ----------------------------------------------------------------------
        conv_id, mode, career_id, is_duplicate, duplicate_response, next_seq, history_text, context_dict, registry, can_proceed = (
            await self._phase1_load_context(user, req)
        )

        if is_duplicate and duplicate_response:
            return duplicate_response

        # ----------------------------------------------------------------------
        # PHASE 2: Zero-Transaction AI Call & Safety Verification
        # ----------------------------------------------------------------------
        # No DB transaction is held open during the external AI call
        reply_content, reply_sources, ai_status = await self._phase2_generate_reply(
            clean_user_message=clean_user_message,
            mode=mode,
            can_proceed=can_proceed,
            context_dict=context_dict,
            registry=registry,
            history_text=history_text,
        )

        # ----------------------------------------------------------------------
        # PHASE 3: Write Messages in a New Transaction
        # ----------------------------------------------------------------------
        return await self._phase3_persist_messages(
            conv_id=conv_id,
            user_msg_content=clean_user_message,
            client_msg_id=req.client_message_id,
            assistant_content=reply_content,
            assistant_sources=reply_sources,
            ai_status=ai_status,
            start_seq=next_seq,
        )

    async def _phase1_load_context(
        self,
        user: User,
        req: ChatRequest,
    ) -> Tuple[
        UUID,
        str,
        Optional[UUID],
        bool,
        Optional[ChatMessageResponse],
        int,
        str,
        Dict[str, Any],
        Dict[str, Dict[str, str]],
        bool,
    ]:
        """Phase 1: Fetch or create conversation, check limits, load history, and build context."""
        now = datetime.now(timezone.utc)

        if req.conversation_id:
            stmt = (
                select(ChatConversation)
                .where(ChatConversation.id == req.conversation_id)
                .options(selectinload(ChatConversation.messages))
            )
            res = await self.session.execute(stmt)
            conv = res.scalar_one_or_none()
            if not conv or conv.user_id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Conversation '{req.conversation_id}' not found.",
                )

            # Invariant: mode is fixed at creation
            if req.mode and req.mode != conv.mode:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Conversation mode is fixed as '{conv.mode}' and cannot be altered.",
                )

            mode = conv.mode
            career_id = conv.career_id
            messages = conv.messages or []

            # Check 50-message limit
            if len(messages) >= MAX_MESSAGES_PER_CONVERSATION:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Maximum limit of {MAX_MESSAGES_PER_CONVERSATION} messages reached for this conversation.",
                )

            # Idempotency: Check client_message_id
            if req.client_message_id:
                for idx, m in enumerate(messages):
                    if m.client_message_id == req.client_message_id:
                        # Find the immediately following assistant message
                        if idx + 1 < len(messages) and messages[idx + 1].role == "assistant":
                            reply_m = messages[idx + 1]
                            dup_resp = ChatMessageResponse(
                                id=reply_m.id,
                                conversation_id=conv.id,
                                seq=reply_m.seq,
                                role=reply_m.role,
                                content=reply_m.content,
                                sources=[ChatSource(**s) for s in (reply_m.sources or [])],
                                ai_status=reply_m.ai_status,
                                created_at=reply_m.created_at,
                            )
                            return conv.id, mode, career_id, True, dup_resp, 0, "", {}, {}, True

            next_seq = max((m.seq for m in messages), default=0) + 1

            # Format last 6 messages for prompt history
            recent = messages[-MAX_HISTORY_MESSAGES_FOR_PROMPT:]
            history_lines = [
                f"{m.role.capitalize()}: {sanitize_untrusted_text(m.content, max_len=400)}"
                for m in recent
            ]
            history_text = "\n".join(history_lines)

        else:
            # Creating new conversation
            if not req.mode:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="mode is required when creating a new conversation.",
                )
            mode = req.mode
            career_id = req.career_id

            if mode == "career":
                if not career_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="career_id is required for 'career' mode.",
                    )
                # Verify career
                stmt_c = select(Career).where(Career.id == career_id)
                res_c = await self.session.execute(stmt_c)
                career = res_c.scalar_one_or_none()
                if not career or career.status != "verified":
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Verified career '{career_id}' not found.",
                    )

            # Check max 20 conversations limit
            stmt_count = select(func.count(ChatConversation.id)).where(ChatConversation.user_id == user.id)
            res_count = await self.session.execute(stmt_count)
            total_convs = res_count.scalar() or 0
            if total_convs >= MAX_CONVERSATIONS_PER_USER:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Maximum limit of {MAX_CONVERSATIONS_PER_USER} conversations reached. Please delete an older conversation.",
                )

            # Deterministic title: Mode + Date
            title = f"{mode.capitalize()} Chat - {now.strftime('%Y-%m-%d')}"
            conv = ChatConversation(
                user_id=user.id,
                mode=mode,
                career_id=career_id,
                title=title,
                created_at=now,
                updated_at=now,
            )
            self.session.add(conv)
            await self.session.flush()

            next_seq = 1
            history_text = ""

        # Build mode context
        context_service = ChatContextService(self.session)
        context_dict, registry, can_proceed = await context_service.build_context(
            user_id=user.id,
            mode=mode,
            career_id=career_id,
        )

        conv_id = conv.id
        # Commit Phase 1 read/creation
        await self.session.commit()

        return conv_id, mode, career_id, False, None, next_seq, history_text, context_dict, registry, can_proceed

    async def _phase2_generate_reply(
        self,
        clean_user_message: str,
        mode: str,
        can_proceed: bool,
        context_dict: Dict[str, Any],
        registry: Dict[str, Dict[str, str]],
        history_text: str,
    ) -> Tuple[str, List[Dict[str, str]], str]:
        """Phase 2: Evaluates safety pre-check or calls LLM Gateway. No DB transaction open."""
        # 1. Safety pre-check (Self-harm / Acute distress)
        if check_distress_safety(clean_user_message):
            logger.info("Chat safety pre-check triggered; returning supportive distress resources.")
            return SUPPORTIVE_SAFETY_MESSAGE, [], "safety"

        # 2. Roadmap mode precondition check
        if mode == "roadmap" and not can_proceed:
            return NO_ROADMAP_ANSWER, [], "fallback"

        # 3. Call LLM Gateway
        gateway = self.gateway or LLMGateway()
        inputs = {
            "context_json": json.dumps(context_dict, indent=2),
            "conversation_history": history_text or "No prior messages.",
            "user_query": clean_user_message,
        }

        fallback_chat = AIChatOutput(
            answer=FIXED_FALLBACK_ANSWER,
            used_record_ids=[],
            in_scope=False,
        )

        try:
            gw_res = await gateway.generate(
                prompt_name="ai_chat",
                inputs=inputs,
                output_schema=AIChatOutput,
                fallback=fallback_chat,
                version=1,
            )
            output = gw_res.data

            if gw_res.telemetry.fallback_used or not output or not output.in_scope:
                return FIXED_FALLBACK_ANSWER, [], "fallback"

            # Post-validator: verify used_record_ids is a strict subset of registry
            is_valid, sources = validate_citations_and_build_sources(output.used_record_ids, registry)
            if not is_valid:
                logger.info("AI chat output cited ungrounded record IDs; triggering fallback.")
                return FIXED_FALLBACK_ANSWER, [], "fallback"

            clean_answer = sanitize_untrusted_text(output.answer, max_len=1500)
            return clean_answer, sources, "ok"

        except Exception as exc:
            logger.info("LLM Gateway call failed or returned unexpected schema (%s); using fallback.", exc)
            return FIXED_FALLBACK_ANSWER, [], "fallback"

    async def _phase3_persist_messages(
        self,
        conv_id: UUID,
        user_msg_content: str,
        client_msg_id: Optional[str],
        assistant_content: str,
        assistant_sources: List[Dict[str, str]],
        ai_status: str,
        start_seq: int,
    ) -> ChatMessageResponse:
        """Phase 3: Write user and assistant messages in a fresh database transaction."""
        now = datetime.now(timezone.utc)
        session = self.session

        # 1. User message
        user_msg = ChatMessage(
            conversation_id=conv_id,
            seq=start_seq,
            client_message_id=client_msg_id,
            role="user",
            content=user_msg_content,
            sources=[],
            ai_status="ok",
            created_at=now,
        )
        session.add(user_msg)

        # 2. Assistant message
        assistant_msg = ChatMessage(
            conversation_id=conv_id,
            seq=start_seq + 1,
            client_message_id=None,
            role="assistant",
            content=assistant_content,
            sources=assistant_sources,
            ai_status=ai_status,
            created_at=now,
        )
        session.add(assistant_msg)

        # Update conversation updated_at
        stmt_conv = select(ChatConversation).where(ChatConversation.id == conv_id)
        res_conv = await session.execute(stmt_conv)
        conv = res_conv.scalar_one_or_none()
        if conv:
            conv.updated_at = now

        await session.commit()
        await session.refresh(assistant_msg)

        return ChatMessageResponse(
            id=assistant_msg.id,
            conversation_id=conv_id,
                seq=assistant_msg.seq,
                role=assistant_msg.role,
                content=assistant_msg.content,
                sources=[ChatSource(**s) for s in assistant_sources],
                ai_status=assistant_msg.ai_status,
                created_at=assistant_msg.created_at,
            )

    async def list_conversations(self, user: User) -> List[ConversationSummaryResponse]:
        """List user's active conversations sorted by updated_at desc."""
        stmt = (
            select(
                ChatConversation,
                func.count(ChatMessage.id).label("msg_count"),
            )
            .outerjoin(ChatMessage, ChatMessage.conversation_id == ChatConversation.id)
            .where(ChatConversation.user_id == user.id)
            .group_by(ChatConversation.id)
            .order_by(ChatConversation.updated_at.desc())
        )
        res = await self.session.execute(stmt)
        rows = res.all()

        summaries = []
        for conv, count in rows:
            summaries.append(
                ConversationSummaryResponse(
                    id=conv.id,
                    mode=conv.mode,
                    career_id=conv.career_id,
                    title=conv.title,
                    created_at=conv.created_at,
                    updated_at=conv.updated_at,
                    message_count=count,
                )
            )
        return summaries

    async def get_conversation_detail(self, user: User, conversation_id: UUID) -> ConversationDetailResponse:
        """Get complete conversation transcript with strict ownership verification."""
        stmt = (
            select(ChatConversation)
            .where(ChatConversation.id == conversation_id)
            .options(selectinload(ChatConversation.messages))
        )
        res = await self.session.execute(stmt)
        conv = res.scalar_one_or_none()

        if not conv or conv.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation '{conversation_id}' not found.",
            )

        msgs = [
            ChatMessageResponse(
                id=m.id,
                conversation_id=conv.id,
                seq=m.seq,
                role=m.role,
                content=m.content,
                sources=[ChatSource(**s) for s in (m.sources or [])],
                ai_status=m.ai_status,
                created_at=m.created_at,
            )
            for m in (conv.messages or [])
        ]

        return ConversationDetailResponse(
            id=conv.id,
            mode=conv.mode,
            career_id=conv.career_id,
            title=conv.title,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            messages=msgs,
        )

    async def delete_conversation(self, user: User, conversation_id: UUID) -> Dict[str, Any]:
        """Delete conversation and all its cascaded messages."""
        stmt = select(ChatConversation).where(ChatConversation.id == conversation_id)
        res = await self.session.execute(stmt)
        conv = res.scalar_one_or_none()

        if not conv or conv.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation '{conversation_id}' not found.",
            )

        await self.session.delete(conv)
        await self.session.commit()
        return {"deleted": True, "conversation_id": str(conversation_id)}
