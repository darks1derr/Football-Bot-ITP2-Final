# Football Fan Assistant Bot

Telegram bot built with Python and `python-telegram-bot`.

## Architecture

The bot uses both JSON and API data:

- JSON stores user data, quiz questions, ranking, favorite team, favorite league, notification settings, teams, leagues, and API cache.
- football-data.org API provides live standings, league matches, team fixtures, and team form.

This keeps the project realistic: JSON is used for local state, while live football information comes from an external API.

## Features

- Matches by favorite league through API.
- League standings through API.
- `My Team` with favorite team, next matches, recent form, and reminders.
- `Settings` for favorite team and favorite league.
- Quiz with random questions, difficulty levels, and categories.
- Quiz ranking stored in `users.json`.
- API response cache stored in `api_cache.json`.

## Project Structure

```text
.
├── bot.py
├── config.py
├── football_api.py
├── keyboards.py
├── storage.py
├── requirements.txt
├── .env
├── .env.example
└── data/
    ├── api_cache.json
    ├── leagues.json
    ├── teams.json
    ├── quiz.json
    └── users.json
```

## Environment

Edit `.env`:

```env
BOT_TOKEN=your_telegram_bot_token
FOOTBALL_DATA_TOKEN=your_football_data_token
REMINDER_MINUTES=60
NOTIFICATION_CHECK_SECONDS=60
QUIZ_QUESTION_LIMIT=5
```

Get a football-data.org token:

```text
https://www.football-data.org/client/register
```

## Run

```powershell
.\.venv\Scripts\python.exe -m pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt
.\.venv\Scripts\python.exe bot.py
```

## Commands

```text
/start - Open the main menu
/matches - Show matches for your favorite league
/standings - Choose a league table
/team - Open My Team
/quiz - Start quiz
/ranking - Show quiz ranking
/settings - Change team or league
/help - Show help
```

## JSON Files

- `data/users.json` - users, favorite team, favorite league, notifications, quiz ranking.
- `data/quiz.json` - quiz questions with difficulty and category.
- `data/teams.json` - teams that can be selected as favorites.
- `data/leagues.json` - leagues available in the menu.
- `data/api_cache.json` - cached API responses.

## API Features

- Standings: `/v4/competitions/{code}/standings`
- League matches: `/v4/competitions/{code}/matches`
- Team upcoming matches: `/v4/teams/{id}/matches`
- Team form: `/v4/teams/{id}/matches?status=FINISHED`
