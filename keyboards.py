from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup


BTN_MATCHES = "Matches"
BTN_STANDINGS = "Standings"
BTN_MY_TEAM = "My Team"
BTN_QUIZ = "Quiz"
BTN_RANKING = "Ranking"
BTN_SETTINGS = "Settings"
BTN_HELP = "Help"


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [BTN_MATCHES, BTN_STANDINGS],
            [BTN_MY_TEAM, BTN_QUIZ],
            [BTN_RANKING, BTN_SETTINGS],
            [BTN_HELP],
        ],
        resize_keyboard=True,
        input_field_placeholder="Choose a section",
    )


def teams_keyboard(teams: list[dict]) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(team["name"], callback_data=f"favorite_team:{team['id']}")]
        for team in teams
    ]
    return InlineKeyboardMarkup(buttons)


def leagues_keyboard(leagues: list[dict], action: str) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(league["name"], callback_data=f"{action}:{league['code']}")]
        for league in leagues
    ]
    return InlineKeyboardMarkup(buttons)


def settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Choose favorite league", callback_data="settings:league")],
            [InlineKeyboardButton("Choose favorite team", callback_data="settings:team")],
        ]
    )


def my_team_keyboard(notifications_enabled: bool) -> InlineKeyboardMarkup:
    notification_label = (
        "Turn reminders off" if notifications_enabled else "Turn reminders on"
    )
    notification_action = (
        "notifications:off" if notifications_enabled else "notifications:on"
    )
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Change team", callback_data="settings:team")],
            [InlineKeyboardButton(notification_label, callback_data=notification_action)],
        ]
    )


def quiz_start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Random", callback_data="quiz_start:random"),
                InlineKeyboardButton("Easy", callback_data="quiz_start:easy"),
            ],
            [
                InlineKeyboardButton("Medium", callback_data="quiz_start:medium"),
                InlineKeyboardButton("Hard", callback_data="quiz_start:hard"),
            ],
        ]
    )


def quiz_keyboard(step: int, options: list[str]) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(option, callback_data=f"quiz:{step}:{index}")]
        for index, option in enumerate(options)
    ]
    return InlineKeyboardMarkup(buttons)
