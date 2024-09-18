from bot.handlers.user_handlers.startup import router as startup_router
from bot.handlers.user_handlers.add_account import router as add_account_router
from bot.handlers.user_handlers.start_account import router as start_account_router
from bot.handlers.user_handlers.utils import router as utils_router

__all__ = [
    "startup_router",
    "add_account_router",
    "start_account_router",
    "utils_router",
]