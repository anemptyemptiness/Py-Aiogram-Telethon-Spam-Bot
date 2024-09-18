from aiogram import Router
from aiogram.types import CallbackQuery

router = Router(name="utils_router")


@router.callback_query()
async def wrong_callback_handler(callback: CallbackQuery):
    await callback.answer()
    await callback.message.delete_reply_markup()