from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query

from app.domain.communication_analysis_service import (
    CommunicationAnalysisService,
)
from app.web.deps import AdminUserDep, SessionDep
from app.web.schemas import (
    CommunicationIsolationItem,
    CommunicationIsolationResponse,
)
from communication_graph_analysis import IsolationConfig

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get(
    "/isolation",
    response_model=CommunicationIsolationResponse,
    summary="Analyze communication isolation",
)
async def analyze_isolation(
    session: SessionDep,
    _: AdminUserDep,
    days: int = Query(default=30, ge=1, le=365),
    window_days: int = Query(default=7, ge=1, le=365),
):
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    service = CommunicationAnalysisService(session)
    try:
        assessments = await service.detect_isolation(
            start=start,
            end=end,
            config=IsolationConfig(window_days=window_days),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    users = [
        CommunicationIsolationItem(
            user_id=item.user,
            score=round(item.score, 4),
            isolated=item.isolated,
            is_bot=item.is_bot,
            criterion_c1=item.criterion_c1,
            criterion_c2=item.criterion_c2,
            criterion_c3=item.criterion_c3,
            criterion_c4=item.criterion_c4,
            f1=round(item.f1, 4),
            f2=round(item.f2, 4),
            f3=round(item.f3, 4),
            f4=round(item.f4, 4),
            personal_in_weight=item.metrics.personal_in_weight,
            personal_out_weight=item.metrics.personal_out_weight,
            mutual_partners=item.metrics.mutual_partners,
            max_silence_days=round(item.metrics.max_silence_days, 2),
            last_seen_gap_days=round(item.metrics.last_seen_gap_days, 2),
            reasons=item.reasons,
        )
        for item in assessments
    ]
    return CommunicationIsolationResponse(
        period_start=start,
        period_end=end,
        window_days=window_days,
        users=users,
    )
