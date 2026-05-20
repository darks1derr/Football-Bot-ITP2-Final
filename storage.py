import json
from pathlib import Path
from typing import Any
from json import JSONDecodeError

from config import DATA_DIR


def _path(filename: str) -> Path:
    return DATA_DIR / filename


def load_json(filename: str, default: Any) -> Any:
    path = _path(filename)
    if not path.exists():
        save_json(filename, default)
        return default

    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (OSError, JSONDecodeError):
        return default


def save_json(filename: str, data: Any) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = _path(filename)
    temp_path = path.with_suffix(path.suffix + ".tmp")

    try:
        with temp_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
            file.write("\n")

        temp_path.replace(path)
    except OSError:
        print(f"Could not save {filename}")


def load_teams() -> list[dict[str, Any]]:
    return load_json("teams.json", [])


def load_leagues() -> list[dict[str, str]]:
    return load_json("leagues.json", [])


def load_quiz() -> list[dict[str, Any]]:
    return load_json("quiz.json", [])


def load_users() -> dict[str, Any]:
    return load_json("users.json", {})


def save_users(users: dict[str, Any]) -> None:
    save_json("users.json", users)


def default_user() -> dict[str, Any]:
    return {
        "display_name": "Fan",
        "username": None,
        "favorite_team": None,
        "favorite_league": None,
        "notifications_enabled": False,
        "notified_matches": [],
        "quiz": {
            "current": 0,
            "score": 0,
            "order": [],
            "answer_order": [],
            "best_score": 0,
            "games_played": 0,
            "total_score": 0,
            "difficulty": "random",
        },
    }


def normalize_user(user: dict[str, Any]) -> dict[str, Any]:
    normalized = default_user()
    normalized.update(user)

    quiz = normalized.get("quiz")
    if not isinstance(quiz, dict):
        quiz = {}

    normalized["quiz"] = {
        "current": quiz.get("current", 0),
        "score": quiz.get("score", 0),
        "order": quiz.get("order", []),
        "answer_order": quiz.get("answer_order", []),
        "best_score": quiz.get("best_score", 0),
        "games_played": quiz.get("games_played", 0),
        "total_score": quiz.get("total_score", 0),
        "difficulty": quiz.get("difficulty", "random"),
    }

    notified = normalized.get("notified_matches", [])
    normalized["notified_matches"] = notified if isinstance(notified, list) else []
    normalized["notifications_enabled"] = bool(
        normalized.get("notifications_enabled", False)
    )
    return normalized


def get_user(user_id: int) -> dict[str, Any]:
    users = load_users()
    key = str(user_id)

    if key not in users:
        users[key] = default_user()
    else:
        users[key] = normalize_user(users[key])

    save_users(users)
    return users[key]


def update_user(user_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    users = load_users()
    key = str(user_id)
    user = normalize_user(users.setdefault(key, default_user()))
    user.update(payload)
    users[key] = normalize_user(user)
    save_users(users)
    return users[key]


def update_user_profile(user_id: int, display_name: str, username: str | None) -> None:
    update_user(user_id, {"display_name": display_name, "username": username})


def update_quiz_state(
    user_id: int,
    current: int,
    score: int,
    order: list[int] | None = None,
    answer_order: list[int] | None = None,
    best_score: int | None = None,
    games_played: int | None = None,
    total_score: int | None = None,
    difficulty: str | None = None,
) -> None:
    user = get_user(user_id)
    previous_quiz = user["quiz"]
    next_quiz = {
        "current": current,
        "score": score,
        "order": order if order is not None else previous_quiz.get("order", []),
        "answer_order": answer_order
        if answer_order is not None
        else previous_quiz.get("answer_order", []),
        "best_score": previous_quiz.get("best_score", 0)
        if best_score is None
        else best_score,
        "games_played": previous_quiz.get("games_played", 0)
        if games_played is None
        else games_played,
        "total_score": previous_quiz.get("total_score", 0)
        if total_score is None
        else total_score,
        "difficulty": previous_quiz.get("difficulty", "random")
        if difficulty is None
        else difficulty,
    }
    update_user(user_id, {"quiz": next_quiz})


def add_notified_match(user_id: int, match_id: str) -> None:
    user = get_user(user_id)
    notified_matches = user.get("notified_matches", [])
    if match_id not in notified_matches:
        notified_matches.append(match_id)
    update_user(user_id, {"notified_matches": notified_matches[-50:]})


def build_quiz_ranking() -> list[tuple[int, dict[str, Any]]]:
    users = load_users()
    ranking = []
    for user_id, user in users.items():
        normalized = normalize_user(user)
        quiz = normalized["quiz"]
        if quiz.get("games_played", 0) > 0 or quiz.get("best_score", 0) > 0:
            ranking.append((int(user_id), normalized))

    return sorted(
        ranking,
        key=lambda item: (
            item[1]["quiz"].get("best_score", 0),
            item[1]["quiz"].get("total_score", 0),
            item[1]["quiz"].get("games_played", 0),
        ),
        reverse=True,
    )
