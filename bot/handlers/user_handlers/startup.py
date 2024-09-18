from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from bot.keyboards.user_kb import get_menu_kb

router = Router(name="startup_router")


@router.message(CommandStart())
async def start_command(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        text=f'Привет, <a href="{message.from_user.url}">{message.from_user.username}</a>!\n\n',
        reply_markup=get_menu_kb(),
    )


@router.callback_query(F.data == "go_back_to_menu")
async def go_back_to_menu_handler(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete_reply_markup()
    await state.clear()
    await callback.message.answer(
        text="Вы вернулись в главное меню 🏡",
        reply_markup=get_menu_kb(),
    )
    await callback.answer()
