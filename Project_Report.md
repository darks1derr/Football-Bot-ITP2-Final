# Project Report

## Project Name

Football Fan Assistant Bot

## Team Members

- Darkhan Daurambekov: Telegram bot handlers, menus, commands, and user actions, API integration.
- Magzhan Assankhan: JSON data, exception handling, documentation, and testing.

## OOP

The project uses simple Object-Oriented Programming in `football_api.py`.

`BaseAPIClient` is a base class that stores common API data such as `base_url`, `token`, and request timeout.

`FootballAPI` inherits from `BaseAPIClient` and adds football-specific methods:

- `fetch_standings`
- `fetch_competition_matches`
- `fetch_team_upcoming_matches`
- `fetch_team_recent_matches`

The bot creates and uses an object of this class:

```python
football_api = FootballAPI()
```

## Data Persistence

The bot stores local data in JSON files:

- `users.json` stores favorite team, favorite league, reminders, and quiz scores.
- `quiz.json` stores quiz questions.
- `teams.json` stores selectable teams.
- `leagues.json` stores selectable leagues.
- `api_cache.json` stores cached API responses.

## Exception Handling

The project uses `try/except` in two important areas:

- API requests in `football_api.py`
- JSON reading and writing in `storage.py`

If the API or JSON loading fails, the bot shows a simple message instead of crashing.

## Telegram Bot Features

- `/start`, `/matches`, `/standings`, `/team`, `/quiz`, `/ranking`, `/settings`, `/help`
- ReplyKeyboard menu
- InlineKeyboard buttons
- Different user actions
- External football API integration
- JSON persistence
