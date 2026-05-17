from os import getenv
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
FOOTBALL_DATA_BASE_URL = "https://api.football-data.org/v4"

load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = getenv("BOT_TOKEN", "").strip()
FOOTBALL_DATA_TOKEN = getenv("FOOTBALL_DATA_TOKEN", "").strip()


def _get_int(name: str, default: int, minimum: int = 1) -> int:
    try:
        value = int(getenv(name, str(default)))
    except ValueError:
        return default
    return max(value, minimum)


REMINDER_MINUTES = _get_int("REMINDER_MINUTES", 60, minimum=1)
NOTIFICATION_CHECK_SECONDS = _get_int(
    "NOTIFICATION_CHECK_SECONDS", 60, minimum=10
)
QUIZ_QUESTION_LIMIT = _get_int("QUIZ_QUESTION_LIMIT", 5, minimum=1)


def validate_settings() -> None:
    if not BOT_TOKEN or BOT_TOKEN == "PASTE_YOUR_BOTFATHER_TOKEN_HERE":
        raise RuntimeError(
            "Add your Telegram bot token to .env: BOT_TOKEN=your_token_from_botfather"
        )
