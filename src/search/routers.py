from fastapi import APIRouter, Depends, Query

from src.auth.deps import get_current_user
from src.search.schemas import CitySearchResultSchema
from src.search.service import find_cities

search_router = APIRouter(prefix="/api/search", tags=["Search"])


@search_router.get("", response_model=list[CitySearchResultSchema])
async def search_cities(
    q: str = Query(..., min_length=1, description="City or country name"),
    language: str = Query("en", min_length=2, max_length=16),
    user=Depends(get_current_user),
):
    return await find_cities(q, language)
