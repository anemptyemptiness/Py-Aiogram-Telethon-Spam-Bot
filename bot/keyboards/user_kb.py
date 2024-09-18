from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_menu_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🤖🆕 Добавить аккаунт", callback_data="add_account")],
            [InlineKeyboardButton(text="🤖 Аккаунты", callback_data="start_account")],
        ]
    )