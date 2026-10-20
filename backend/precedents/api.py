"""Read-only Korean precedent API for the web client (대응 방안 panel and checklist)."""

from fastapi import APIRouter, HTTPException, Query

from backend.precedents import repository
from backend.precedents.taxonomy import CATEGORIES, categorize

router = APIRouter(prefix="/precedents", tags=["precedents"])


def resolve(category, statute):
    """Category from ?category= or, failing that, from a statute string."""
    if category:
        if category not in CATEGORIES:
            raise HTTPException(status_code=422, detail="알 수 없는 거절 유형입니다.")
        return category
    if statute:
        return categorize(statute)
    raise HTTPException(status_code=422, detail="category 또는 statute를 지정하세요.")


@router.get("/categories")
def categories():
    """Common rejection categories with their Korean statutes."""
    return CATEGORIES


@router.get("/stats")
def stats(category: str | None = None, statute: str | None = Query(None, max_length=200)):
    """Resolution statistics for one category (real KIPRIS cases only)."""
    return repository.stats(resolve(category, statute))


@router.get("/similar")
def similar(
    category: str | None = None,
    statute: str | None = Query(None, max_length=200),
    q: str = Query("", max_length=8000),
    limit: int = Query(5, ge=1, le=20),
    exclude: str = Query("", max_length=40),
):
    """Cases whose rejected claim resembles `q` (needs claim text; today the DEMO cases)."""
    skip = frozenset({exclude}) if exclude else frozenset()
    return repository.similar(resolve(category, statute), q, limit, skip)


@router.get("")
def search(
    category: str | None = None,
    statute: str | None = Query(None, max_length=200),
    q: str = Query("", max_length=4000),
    limit: int = Query(3, ge=1, le=20),
):
    """Representative real cases (resolved by amendment / argument only / unresolved)."""
    return repository.find(resolve(category, statute), q, limit)


@router.get("/{case_id}")
def case(case_id: str):
    """Full stored record of one case."""
    found = repository.get(case_id)
    if found is None:
        raise HTTPException(status_code=404, detail="대응 사례가 없습니다.")
    return found
