from datetime import datetime, timedelta, timezone
from communication_graph_analysis import (
    CommunicationGraph,
    IsolationAssessment,
    IsolationConfig,
    MessageRecord,
    detect_isolated_users,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    ChatModel,
    GroupChatMemberModel,
    MessageModel,
)


class CommunicationAnalysisService:
    """Builds communication-analysis snapshots from application data."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def detect_isolation(
        self,
        start: datetime,
        end: datetime,
        config: IsolationConfig,
    ) -> list[IsolationAssessment]:
        if start.tzinfo is None or end.tzinfo is None:
            raise ValueError("Analysis period must use timezone-aware datetimes")
        if start >= end:
            raise ValueError("Analysis period start must precede end")

        message_rows = list(
            (
                await self._session.scalars(
                    select(MessageModel)
                    .join(ChatModel, ChatModel.id == MessageModel.chat_id)
                    .where(
                        MessageModel.created_at >= start,
                        MessageModel.created_at < end,
                        MessageModel.sender_id.is_not(None),
                    )
                    .order_by(MessageModel.created_at, MessageModel.id)
                )
            ).all()
        )
        chat_ids = {row.chat_id for row in message_rows}
        members_by_chat: dict[str, set[str]] = {}
        if chat_ids:
            member_rows = list(
                (
                    await self._session.scalars(
                        select(GroupChatMemberModel).where(
                            GroupChatMemberModel.chat_id.in_(chat_ids)
                        )
                    )
                ).all()
            )
            for row in member_rows:
                members_by_chat.setdefault(str(row.chat_id), set()).add(
                    str(row.user_id)
                )

        records: list[MessageRecord] = []
        for row in message_rows:
            sender = str(row.sender_id)
            is_group = row.recipient_id is None and str(row.chat_id) in members_by_chat
            records.append(
                MessageRecord(
                    sender=sender,
                    recipient=None if is_group else (
                        str(row.recipient_id) if row.recipient_id else None
                    ),
                    chat_id=str(row.chat_id),
                    timestamp=row.created_at,
                    event_type="group" if is_group else "direct",
                    length_chars=len(row.content),
                )
            )

        graph = CommunicationGraph(
            records,
            window_days=config.window_days,
            chat_members=members_by_chat,
        )
        return detect_isolated_users(graph, config)


def default_analysis_period(days: int) -> tuple[datetime, datetime]:
    end = datetime.now(timezone.utc)
    return end - timedelta(days=days), end