from fastapi import APIRouter, Depends, Query, Response, status

from src.auth.deps import get_current_user
from src.matches.schemas import MatchSchema
from src.matches.service import get_user_matches, mark_user_matches_seen

matches_router = APIRouter(prefix="/api/matches", tags=["Matches"])


@matches_router.get("", response_model=list[MatchSchema])
async def get_my_matches(
    language: str = Query("en", min_length=2, max_length=16),
    user=Depends(get_current_user),
):
    return await get_user_matches(user.id, language)


@matches_router.post("/seen", status_code=status.HTTP_204_NO_CONTENT)
async def mark_my_matches_seen(user=Depends(get_current_user)) -> Response:
    await mark_user_matches_seen(user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
