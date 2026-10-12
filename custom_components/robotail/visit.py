"""Interpret recorded cat identities without guessing from weight."""

from typing import Any


def last_cat_name(data: dict[str, Any]) -> str | None:
    """Resolve the latest visit's associated cat profile."""
    visit = data.get("latest_visit") or {}
    if not visit:
        return None
    if visit.get("catName"):
        return str(visit["catName"])
    cat_id = visit.get("catInfoId") or visit.get("catId")
    if cat_id in (None, 0, "0", ""):
        return None
    for cat in data.get("cats") or []:
        if str(cat.get("catInfoId")) == str(cat_id):
            return cat.get("nickname") or None
    return None
