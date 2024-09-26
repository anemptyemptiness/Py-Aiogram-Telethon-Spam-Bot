from aiogram.fsm.state import StatesGroup, State


class AddAccountSG(StatesGroup):
    api_id = State()
    api_hash = State()
    phone = State()
    password = State()
    db_name = State()
    code = State()


class AccountInfoSG(StatesGroup):
    accounts = State()
    change_db = State()
    change_spam_msg = State()
    change_spam_msg_2 = State()
