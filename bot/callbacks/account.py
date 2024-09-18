from aiogram.filters.callback_data import CallbackData


class AccountCallback(CallbackData, prefix="account"):
    identification: int


class PaginationCallbackData(CallbackData, prefix="pag"):
    action: str
    page: int