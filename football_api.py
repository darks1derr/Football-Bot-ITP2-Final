from datetime import datetime, timedelta, timezone
from hashlib import sha1
from typing import Any
from urllib.parse import urlencode

import httpx

from config import FOOTBALL_DATA_BASE_URL, FOOTBALL_DATA_TOKEN
from storage import load_json, save_json


class FootballDataError(Exception):
    """Raised when live football data cannot be loaded."""


def has_api_token() -> bool:
    return bool(FOOTBALL_DATA_TOKEN) and not FOOTBALL_DATA_TOKEN.startswith("PASTE_")


async def fetch_standings(competition_code: str) -> dict[str, Any]:
    payload = await _get_json(
        f"/competitions/{competition_code}/standings",
        cache_minutes=30,
    )
    standings = payload.get("standings", [])
    total_standing = next(
        (standing for standing in standings if standing.get("type") == "TOTAL"),
        None,
    )
    selected_standing = total_standing or (standings[0] if standings else {})
    table = selected_standing.get("table", [])

    rows = []
    for row in table:
        team = row.get("team", {})
        rows.append(
            {
                "position": row.get("position"),
                "team_id": team.get("id"),
                "team": team.get("shortName") or team.get("name", "Unknown"),
                "played": row.get("playedGames", 0),
                "won": row.get("won", 0),
                "drawn": row.get("draw", 0),
                "lost": row.get("lost", 0),
                "points": row.get("points", 0),
                "goal_difference": row.get("goalDifference", 0),
                "form": row.get("form"),
            }
        )

    return {
        "competition": payload.get("competition", {}).get("name", competition_code),
        "season": payload.get("season", {}),
        "rows": rows,
    }


async def fetch_competition_matches(
    competition_code: str,
    days: int = 7,
) -> dict[str, Any]:
    today = datetime.now(timezone.utc).date()
    date_to = today + timedelta(days=days)
    payload = await _get_json(
        f"/competitions/{competition_code}/matches",
        params={
            "dateFrom": today.isoformat(),
            "dateTo": date_to.isoformat(),
        },
        cache_minutes=10,
    )
    matches = [_normalize_match(match) for match in payload.get("matches", [])]
    matches.sort(key=lambda match: match["utcDate"])

    return {
        "competition": payload.get("competition", {}).get("name", competition_code),
        "matches": matches,
    }


async def fetch_team_upcoming_matches(
    team_api_id: int,
    days: int = 30,
    limit: int = 5,
) -> list[dict[str, Any]]:
    today = datetime.now(timezone.utc).date()
    date_to = today + timedelta(days=days)
    payload = await _get_json(
        f"/teams/{team_api_id}/matches",
        params={
            "dateFrom": today.isoformat(),
            "dateTo": date_to.isoformat(),
            "status": "SCHEDULED",
            "limit": str(limit),
        },
        cache_minutes=10,
    )
    matches = [_normalize_match(match) for match in payload.get("matches", [])]
    matches.sort(key=lambda match: match["utcDate"])
    return matches[:limit]


async def fetch_team_recent_matches(
    team_api_id: int,
    limit: int = 5,
) -> list[dict[str, Any]]:
    payload = await _get_json(
        f"/teams/{team_api_id}/matches",
        params={
            "status": "FINISHED",
            "limit": str(limit),
        },
        cache_minutes=60,
    )
    matches = [_normalize_match(match) for match in payload.get("matches", [])]
    matches.sort(key=lambda match: match["utcDate"], reverse=True)
    return matches[:limit]


async def _get_json(
    endpoint: str,
    params: dict[str, str] | None = None,
    cache_minutes: int = 15,
) -> dict[str, Any]:
    if not has_api_token():
        raise FootballDataError("FOOTBALL_DATA_TOKEN is missing")

    params = params or {}
    cache_key = _cache_key(endpoint, params)
    cached = _read_cache(cache_key, cache_minutes)
    if cached is not None:
        return cached

    url = f"{FOOTBALL_DATA_BASE_URL}{endpoint}"
    headers = {"X-Auth-Token": FOOTBALL_DATA_TOKEN}

    try:
        async with httpx.AsyncClient(timeout=12) as client:
            response = await client.get(url, headers=headers, params=params)
    except httpx.HTTPError as error:
        raise FootballDataError("Football API is not available right now") from error

    if response.status_code == 403:
        raise FootballDataError("This data is not available for your API token")
    if response.status_code == 429:
        raise FootballDataError("Football API daily limit is reached")
    if response.status_code >= 400:
        raise FootballDataError(f"Football API returned {response.status_code}")

    payload = response.json()
    _write_cache(cache_key, payload)
    return payload


def _normalize_match(match: dict[str, Any]) -> dict[str, Any]:
    home = match.get("homeTeam", {})
    away = match.get("awayTeam", {})
    competition = match.get("competition", {})
    score = match.get("score", {}).get("fullTime", {})
    utc_date = match.get("utcDate", "")

    return {
        "id": match.get("id"),
        "utcDate": utc_date,
        "localTime": _format_local_time(utc_date),
        "status": match.get("status", "UNKNOWN"),
        "competition": competition.get("name", "Competition"),
        "competition_code": competition.get("code"),
        "home_id": home.get("id"),
        "home": home.get("shortName") or home.get("name", "Home"),
        "away_id": away.get("id"),
        "away": away.get("shortName") or away.get("name", "Away"),
        "home_score": score.get("home"),
        "away_score": score.get("away"),
        "matchday": match.get("matchday"),
    }


def _format_local_time(utc_date: str) -> str:
    try:
        kickoff = datetime.fromisoformat(utc_date.replace("Z", "+00:00"))
    except ValueError:
        return utc_date
    return kickoff.astimezone().strftime("%Y-%m-%d %H:%M")


def _cache_key(endpoint: str, params: dict[str, str]) -> str:
    raw = f"{endpoint}?{urlencode(sorted(params.items()))}"
    return sha1(raw.encode("utf-8")).hexdigest()


def _read_cache(cache_key: str, cache_minutes: int) -> dict[str, Any] | None:
    cache = load_json("api_cache.json", {})
    entry = cache.get(cache_key)
    if not entry:
        return None

    now = datetime.now(timezone.utc).timestamp()
    if now - entry.get("saved_at", 0) > cache_minutes * 60:
        return None
    return entry.get("payload")


def _write_cache(cache_key: str, payload: dict[str, Any]) -> None:
    cache = load_json("api_cache.json", {})
    cache[cache_key] = {
        "saved_at": datetime.now(timezone.utc).timestamp(),
        "payload": payload,
    }
    save_json("api_cache.json", cache)
