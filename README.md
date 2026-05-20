# Football Fan Assistant Bot

## Project Description

Football Fan Assistant Bot is a Telegram bot created for football fans.
The bot allows users to view football standings, match schedules, favorite team information, and play football quizzes directly inside Telegram.

The project was developed using Python and Telegram Bot API.

---

## Features

* View football standings
* View upcoming matches
* Save favorite team
* Football quiz system
* Ranking system
* Interactive Telegram menus
* API integration with football-data.org
* JSON data storage

---

## Technologies Used

* Python
* python-telegram-bot
* Telegram Bot API
* football-data.org API
* JSON

---

## Project Structure

* `bot.py` — main bot logic
* `football_api.py` — work with football API
* `storage.py` — reading and writing JSON files
* `keyboards.py` — Telegram keyboards
* `config.py` — configuration and tokens
* `data/` — JSON storage files

---

## Installation

1. Clone the repository

```bash
git clone https://github.com/your-repository-name.git
```

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Add your Telegram Bot Token and API key in `config.py`

4. Run the bot

```bash
python bot.py
```

---

## Challenges Faced

* Working with external API responses
* Organizing project structure
* Handling user data
* Managing asynchronous functions

---

## Future Improvements

* Add database support
* Add live match notifications
* Add more football leagues
* Improve quiz system

---

## Team Members

•	Darkhan Daurambekov - main bot structure, Telegram commands, and football API integration.
•	Magzhan Assankhan - quiz system, JSON data storage, testing, debugging, and project documentation.
