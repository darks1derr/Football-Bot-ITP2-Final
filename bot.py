import asyncio
import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Any

from telegram import BotCommand, Message, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import (
    BOT_TOKEN,
    NOTIFICATION_CHECK_SECONDS,
    QUIZ_QUESTION_LIMIT,
    REMINDER_MINUTES,
    validate_settings,
)
from football_api import (
    FootballDataError,
    fetch_competition_matches,
    fetch_standings,
    fetch_team_recent_matches,
    fetch_team_upcoming_matches,
    has_api_token,
)
from keyboards import (
    BTN_HELP,
    BTN_MATCHES,
    BTN_MY_TEAM,
    BTN_QUIZ,
    BTN_RANKING,
    BTN_SETTINGS,
    BTN_STANDINGS,
    leagues_keyboard,
    main_menu,
    my_team_keyboard,
    quiz_keyboard,
    quiz_start_keyboard,
    settings_keyboard,
    teams_keyboard,
)
from storage import (
    add_notified_match,
    build_quiz_ranking,
    get_user,
    load_leagues,
    load_quiz,
    load_teams,
    load_users,
    update_quiz_state,
    update_user,
    update_user_profile,
)


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


TITLE = "Football Fan Assistant"
LINE = "----------------------"

WELCOME_TEXT = (
    f"{TITLE}\n"
    f"{LINE}\n"
    "Live matches and standings come from the football API.\n"
    "Your team, quiz progress, ranking, settings, and API cache are stored in JSON."
)

HELP_TEXT = (
    f"{TITLE}\n"
    f"{LINE}\n"
    "/start - Open the main menu\n"
    "/matches - Show matches by favorite league\n"
    "/standings - Choose a league table\n"
    "/team - Open My Team\n"
    "/quiz - Start quiz by difficulty\n"
    "/ranking - Show quiz ranking\n"
    "/settings - Change team or league\n"
    "/help - Show help"
)


async def post_init(application: Application) -> None:
    await set_bot_commands(application)
    application.create_task(notification_loop(application))


async def set_bot_commands(application: Application) -> None:
    await application.bot.set_my_commands(
        [
            BotCommand("start", "Open the main menu"),
            BotCommand("matches", "Show matches"),
            BotCommand("standings", "Choose standings"),
            BotCommand("team", "Open My Team"),
            BotCommand("quiz", "Start quiz"),
            BotCommand("ranking", "Show quiz ranking"),
            BotCommand("settings", "Open settings"),
            BotCommand("help", "Show help"),
        ]
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    remember_user(update)
    await update.effective_message.reply_text(WELCOME_TEXT, reply_markup=main_menu())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    remember_user(update)
    await update.effective_message.reply_text(HELP_TEXT, reply_markup=main_menu())


async def show_matches(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    remember_user(update)
    if not update.effective_user:
        return

    if not has_api_token():
        await update.effective_message.reply_text(api_token_message(), reply_markup=main_menu())
        return

    user = get_user(update.effective_user.id)
    favorite_league = user.get("favorite_league")
    if not favorite_league:
        await update.effective_message.reply_text(
            "Choose a league for upcoming matches:",
            reply_markup=leagues_keyboard(load_leagues(), "matches"),
        )
        return

    await send_league_matches(update.effective_message, favorite_league)


async def choose_standings_league(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    remember_user(update)
    if not has_api_token():
        await update.effective_message.reply_text(api_token_message(), reply_markup=main_menu())
        return

    await update.effective_message.reply_text(
        "Choose a league table:",
        reply_markup=leagues_keyboard(load_leagues(), "standings"),
    )


async def choose_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    remember_user(update)
    await update.effective_message.reply_text(
        "Choose quiz difficulty:",
        reply_markup=quiz_start_keyboard(),
    )


async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    remember_user(update)
    if not update.effective_user:
        return

    user = get_user(update.effective_user.id)
    team = get_favorite_team(user)
    league = find_league(user.get("favorite_league"))
    lines = [
        "Settings",
        LINE,
        f"Favorite team: {team['name'] if team else 'not selected'}",
        f"Favorite league: {league['name'] if league else 'not selected'}",
    ]
    await update.effective_message.reply_text(
        "\n".join(lines),
        reply_markup=settings_keyboard(),
    )


async def show_my_team(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    remember_user(update)
    if not update.effective_user:
        return

    await send_my_team_card(update.effective_message, update.effective_user.id)


async def show_ranking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    remember_user(update)
    ranking = build_quiz_ranking()

    if not ranking:
        await update.effective_message.reply_text(
            f"Quiz Ranking\n{LINE}\nNo quiz results yet.",
            reply_markup=main_menu(),
        )
        return

    lines = ["Quiz Ranking", LINE]
    for place, (_, user) in enumerate(ranking[:10], start=1):
        quiz = user["quiz"]
        name = clean_display_name(user.get("display_name", "Fan"))
        lines.append(
            f"{place}. {name} - best {quiz['best_score']}, "
            f"games {quiz['games_played']}, total {quiz['total_score']}"
        )

    await update.effective_message.reply_text("\n".join(lines), reply_markup=main_menu())


async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    remember_user(update)
    text = (update.effective_message.text or "").strip()

    if text == BTN_MATCHES:
        await show_matches(update, context)
    elif text == BTN_STANDINGS:
        await choose_standings_league(update, context)
    elif text == BTN_MY_TEAM:
        await show_my_team(update, context)
    elif text == BTN_QUIZ:
        await choose_quiz(update, context)
    elif text == BTN_RANKING:
        await show_ranking(update, context)
    elif text == BTN_SETTINGS:
        await show_settings(update, context)
    elif text == BTN_HELP:
        await help_command(update, context)
    else:
        await update.effective_message.reply_text(
            "Use the menu buttons or /help.",
            reply_markup=main_menu(),
        )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    remember_user(update)
    query = update.callback_query
    if not query or not update.effective_user:
        return

    await query.answer()
    data = query.data or ""

    if data.startswith("standings:"):
        await send_standings(query.message, data.split(":", maxsplit=1)[1])
    elif data.startswith("matches:"):
        league_code = data.split(":", maxsplit=1)[1]
        update_user(update.effective_user.id, {"favorite_league": league_code})
        await send_league_matches(query.message, league_code)
    elif data.startswith("favorite_league:"):
        league_code = data.split(":", maxsplit=1)[1]
        update_user(update.effective_user.id, {"favorite_league": league_code})
        league = find_league(league_code)
        await query.edit_message_text(
            f"Favorite league saved: {league['name'] if league else league_code}"
        )
    elif data.startswith("favorite_team:"):
        await handle_favorite_team_callback(update, data)
    elif data == "settings:league":
        await query.message.reply_text(
            "Choose favorite league:",
            reply_markup=leagues_keyboard(load_leagues(), "favorite_league"),
        )
    elif data == "settings:team":
        await query.message.reply_text(
            "Choose favorite team:",
            reply_markup=teams_keyboard(load_teams()),
        )
    elif data.startswith("notifications:"):
        await handle_notification_callback(update, data)
    elif data.startswith("quiz_start:"):
        await start_quiz(update, data.split(":", maxsplit=1)[1])
    elif data.startswith("quiz:"):
        await handle_quiz_callback(update, data)


async def send_standings(message: Message, competition_code: str) -> None:
    if not has_api_token():
        await message.reply_text(api_token_message(), reply_markup=main_menu())
        return

    league = find_league(competition_code)
    league_name = league["name"] if league else competition_code
    await message.reply_text(f"Loading standings: {league_name}...")

    try:
        data = await fetch_standings(competition_code)
    except FootballDataError as error:
        await message.reply_text(
            f"Standings are unavailable.\nReason: {error}",
            reply_markup=main_menu(),
        )
        return

    await message.reply_text(format_api_standings(data), reply_markup=main_menu())


async def send_league_matches(message: Message, competition_code: str) -> None:
    if not has_api_token():
        await message.reply_text(api_token_message(), reply_markup=main_menu())
        return

    league = find_league(competition_code)
    league_name = league["name"] if league else competition_code
    await message.reply_text(f"Loading matches: {league_name}...")

    try:
        data = await fetch_competition_matches(competition_code, days=7)
    except FootballDataError as error:
        await message.reply_text(
            f"Matches are unavailable.\nReason: {error}",
            reply_markup=main_menu(),
        )
        return

    matches = data.get("matches", [])
    if not matches:
        await message.reply_text(
            f"No matches found for {league_name} in the next 7 days.",
            reply_markup=main_menu(),
        )
        return

    lines = [f"Matches - {league_name}", LINE]
    lines.extend(format_matches(matches[:10]))
    await message.reply_text("\n".join(lines), reply_markup=main_menu())


async def send_my_team_card(message: Message, user_id: int) -> None:
    user = get_user(user_id)
    team = get_favorite_team(user)

    if not team:
        await message.reply_text(
            f"My Team\n{LINE}\nChoose your favorite team first.",
            reply_markup=teams_keyboard(load_teams()),
        )
        return

    reminder_status = "On" if user.get("notifications_enabled") else "Off"
    lines = [
        "My Team",
        LINE,
        f"Team: {team['name']}",
        f"League: {team.get('league', 'Unknown')}",
        f"Match reminders: {reminder_status}",
    ]

    if not has_api_token():
        lines.append("")
        lines.append("Live team data needs FOOTBALL_DATA_TOKEN in .env.")
        await message.reply_text(
            "\n".join(lines),
            reply_markup=my_team_keyboard(user.get("notifications_enabled", False)),
        )
        return

    try:
        upcoming = await fetch_team_upcoming_matches(team["api_id"], days=30, limit=3)
        recent = await fetch_team_recent_matches(team["api_id"], limit=5)
    except FootballDataError as error:
        lines.append("")
        lines.append(f"Team data is unavailable: {error}")
        await message.reply_text(
            "\n".join(lines),
            reply_markup=my_team_keyboard(user.get("notifications_enabled", False)),
        )
        return

    lines.append("")
    lines.append("Next matches:")
    lines.extend(format_matches(upcoming) if upcoming else ["No upcoming matches found."])
    lines.append("")
    lines.append("Form:")
    lines.extend(format_matches(recent) if recent else ["No recent matches found."])

    await message.reply_text(
        "\n".join(lines),
        reply_markup=my_team_keyboard(user.get("notifications_enabled", False)),
    )


async def handle_favorite_team_callback(update: Update, data: str) -> None:
    query = update.callback_query
    if not query or not update.effective_user:
        return

    team_id = data.split(":", maxsplit=1)[1]
    team = find_team(team_id)
    if not team:
        await query.edit_message_text("Team not found. Please choose again.")
        return

    update_user(
        update.effective_user.id,
        {
            "favorite_team": team_id,
            "favorite_league": team.get("league_code"),
            "notified_matches": [],
        },
    )
    await query.edit_message_text(f"Favorite team saved: {team['name']}")
    await send_my_team_card(query.message, update.effective_user.id)


async def handle_notification_callback(update: Update, data: str) -> None:
    query = update.callback_query
    if not query or not update.effective_user:
        return

    enabled = data.endswith(":on")
    team = get_favorite_team(get_user(update.effective_user.id))
    if enabled and not team:
        await query.edit_message_text("Choose your favorite team before turning reminders on.")
        return

    update_user(update.effective_user.id, {"notifications_enabled": enabled})
    await query.edit_message_text(
        "Match reminders are now on." if enabled else "Match reminders are now off."
    )
    await send_my_team_card(query.message, update.effective_user.id)


async def start_quiz(update: Update, difficulty: str) -> None:
    if not update.effective_user or not update.effective_message:
        return

    quiz = load_quiz()
    if difficulty != "random":
        quiz = [
            question
            for question in quiz
            if question.get("difficulty", "easy").lower() == difficulty
        ]

    if not quiz:
        await update.effective_message.reply_text(
            f"No questions found for difficulty: {difficulty}",
            reply_markup=main_menu(),
        )
        return

    question_count = min(len(quiz), QUIZ_QUESTION_LIMIT)
    selected_questions = random.sample(quiz, question_count)
    all_questions = load_quiz()
    order = [all_questions.index(question) for question in selected_questions]

    user = get_user(update.effective_user.id)
    best_score = user["quiz"].get("best_score", 0)
    update_quiz_state(
        update.effective_user.id,
        current=0,
        score=0,
        order=order,
        answer_order=[],
        best_score=best_score,
        difficulty=difficulty,
    )
    await send_current_quiz_question(update.effective_message, update.effective_user.id)


async def send_current_quiz_question(message: Message, user_id: int) -> None:
    quiz = load_quiz()
    user = get_user(user_id)
    state = user["quiz"]
    order = state.get("order", [])
    current = state.get("current", 0)

    if not order or current >= len(order):
        await message.reply_text("Quiz state was reset. Start a new quiz.")
        return

    question_index = order[current]
    question = quiz[question_index]
    answer_order = list(range(len(question["options"])))
    random.shuffle(answer_order)
    update_quiz_state(
        user_id,
        current=current,
        score=state.get("score", 0),
        order=order,
        answer_order=answer_order,
        best_score=state.get("best_score", 0),
        difficulty=state.get("difficulty", "random"),
    )

    shuffled_options = [question["options"][index] for index in answer_order]
    text = (
        "Football Quiz\n"
        f"{LINE}\n"
        f"Difficulty: {state.get('difficulty', 'random').title()}\n"
        f"Category: {question.get('category', 'Football')}\n"
        f"Question {current + 1} of {len(order)}\n"
        f"Score: {state.get('score', 0)}\n\n"
        f"{question['question']}"
    )

    await message.reply_text(text, reply_markup=quiz_keyboard(current, shuffled_options))


async def handle_quiz_callback(update: Update, data: str) -> None:
    query = update.callback_query
    if not query or not update.effective_user:
        return

    try:
        _, step_raw, answer_position_raw = data.split(":")
        step = int(step_raw)
        answer_position = int(answer_position_raw)
    except ValueError:
        await query.edit_message_text("Could not read that answer. Start a new quiz.")
        return

    quiz = load_quiz()
    user = get_user(update.effective_user.id)
    state = user["quiz"]
    order = state.get("order", [])
    current = state.get("current", 0)
    answer_order = state.get("answer_order", [])

    if step != current or not order or current >= len(order):
        await query.edit_message_text("This question is no longer active. Start a new quiz.")
        return

    if answer_position >= len(answer_order):
        await query.edit_message_text("That answer does not exist. Start a new quiz.")
        return

    question = quiz[order[current]]
    answer_index = answer_order[answer_position]
    is_correct = answer_index == question["answer_index"]
    next_score = state.get("score", 0) + int(is_correct)
    next_step = current + 1
    correct_answer = question["options"][question["answer_index"]]
    answer_text = "Correct!" if is_correct else "Wrong."

    await query.edit_message_text(f"{answer_text}\nCorrect answer: {correct_answer}")

    if next_step >= len(order):
        best_score = max(state.get("best_score", 0), next_score)
        games_played = state.get("games_played", 0) + 1
        total_score = state.get("total_score", 0) + next_score
        update_quiz_state(
            update.effective_user.id,
            current=0,
            score=0,
            order=[],
            answer_order=[],
            best_score=best_score,
            games_played=games_played,
            total_score=total_score,
            difficulty=state.get("difficulty", "random"),
        )
        await query.message.reply_text(
            "Quiz finished\n"
            f"{LINE}\n"
            f"Your score: {next_score} of {len(order)}\n"
            f"Best score: {best_score}\n"
            f"Games played: {games_played}",
            reply_markup=main_menu(),
        )
        return

    update_quiz_state(
        update.effective_user.id,
        current=next_step,
        score=next_score,
        order=order,
        answer_order=[],
        best_score=state.get("best_score", 0),
        difficulty=state.get("difficulty", "random"),
    )
    await send_current_quiz_question(query.message, update.effective_user.id)


async def notification_loop(application: Application) -> None:
    await asyncio.sleep(5)
    while True:
        try:
            await send_match_reminders(application)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Match reminder check failed")
        await asyncio.sleep(NOTIFICATION_CHECK_SECONDS)


async def send_match_reminders(application: Application) -> None:
    if not has_api_token():
        return

    users = load_users()
    now = datetime.now(timezone.utc)
    deadline = now + timedelta(minutes=REMINDER_MINUTES)

    for user_id_raw in users:
        try:
            user_id = int(user_id_raw)
        except ValueError:
            continue

        user = get_user(user_id)
        if not user.get("notifications_enabled"):
            continue

        team = get_favorite_team(user)
        if not team:
            continue

        try:
            matches = await fetch_team_upcoming_matches(team["api_id"], days=2, limit=5)
        except FootballDataError:
            continue

        for match in matches:
            kickoff = parse_api_datetime(match.get("utcDate", ""))
            if not kickoff or not (now <= kickoff <= deadline):
                continue

            match_id = str(match.get("id") or build_match_id(match))
            if match_id in user.get("notified_matches", []):
                continue

            try:
                await application.bot.send_message(
                    chat_id=user_id,
                    text=(
                        "Match reminder\n"
                        f"{LINE}\n"
                        f"{match['home']} vs {match['away']}\n"
                        f"{match['competition']}\n"
                        f"Kickoff: {match['localTime']}\n"
                        f"Starts within {REMINDER_MINUTES} minutes."
                    ),
                )
            except Exception:
                logger.exception("Could not send reminder to user %s", user_id)
                continue

            add_notified_match(user_id, match_id)


def remember_user(update: Update) -> None:
    user = update.effective_user
    if not user:
        return
    update_user_profile(user.id, user.full_name or user.first_name or "Fan", user.username)


def format_matches(matches: list[dict[str, Any]]) -> list[str]:
    lines = []
    for match in matches:
        score = format_score(match)
        lines.append(
            f"- {match['localTime']} | {match['home']} vs {match['away']}"
            f"{score} | {match['competition']}"
        )
    return lines


def format_score(match: dict[str, Any]) -> str:
    if match.get("status") != "FINISHED":
        return ""
    home_score = match.get("home_score")
    away_score = match.get("away_score")
    if home_score is None or away_score is None:
        return ""
    return f" ({home_score}-{away_score})"


def format_api_standings(data: dict[str, Any]) -> str:
    rows = data.get("rows", [])
    if not rows:
        return "The table is empty."

    season = data.get("season", {})
    start_date = season.get("startDate", "")
    end_date = season.get("endDate", "")
    season_text = f"{start_date[:4]}/{end_date[:4]}" if start_date and end_date else ""

    lines = [
        f"{data.get('competition', 'League')} {season_text}".strip(),
        LINE,
        "# | Club | P | W | D | L | Pts | GD",
    ]

    for row in rows[:20]:
        lines.append(
            f"{row['position']}. {row['team']} | {row['played']} | {row['won']} | "
            f"{row['drawn']} | {row['lost']} | {row['points']} | "
            f"{row['goal_difference']}"
        )

    return "\n".join(lines)


def find_league(competition_code: str | None) -> dict[str, str] | None:
    if not competition_code:
        return None
    return next(
        (league for league in load_leagues() if league["code"] == competition_code),
        None,
    )


def find_team(team_id: str | None) -> dict[str, Any] | None:
    if not team_id:
        return None
    return next((team for team in load_teams() if team["id"] == team_id), None)


def get_favorite_team(user: dict[str, Any]) -> dict[str, Any] | None:
    return find_team(user.get("favorite_team"))


def parse_api_datetime(utc_date: str) -> datetime | None:
    try:
        return datetime.fromisoformat(utc_date.replace("Z", "+00:00"))
    except ValueError:
        return None


def build_match_id(match: dict[str, Any]) -> str:
    return "|".join(
        [
            str(match.get("utcDate", "")),
            str(match.get("home", "")),
            str(match.get("away", "")),
        ]
    )


def clean_display_name(name: str) -> str:
    return " ".join(name.split())[:24] or "Fan"


def api_token_message() -> str:
    return "Live football data is unavailable. Add FOOTBALL_DATA_TOKEN to .env and restart the bot."


def build_application() -> Application:
    validate_settings()

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("matches", show_matches))
    application.add_handler(CommandHandler("standings", choose_standings_league))
    application.add_handler(CommandHandler("team", show_my_team))
    application.add_handler(CommandHandler("quiz", choose_quiz))
    application.add_handler(CommandHandler("ranking", show_ranking))
    application.add_handler(CommandHandler("settings", show_settings))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu))
    return application


def main() -> None:
    application = build_application()
    logger.info("Football Fan Assistant Bot started")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
