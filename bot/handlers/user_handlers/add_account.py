import aiofiles
from aiogram import Router, F, Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

from bot.db.account.requests import AccountDAO
from bot.db.users.requests import UserDAO
from bot.fsm.fsm import AddAccountSG

router = Router(name="add_account_router")


@router.callback_query(StateFilter(default_state), F.data == "add_account")
async def add_command_handler(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete_reply_markup()
    await callback.message.answer(
        text="Пришлите мне <b>api_id</b> нового аккаунта в ответном сообщении",
    )
    await state.set_state(AddAccountSG.api_id)
    await callback.answer()


@router.message(StateFilter(AddAccountSG.api_id), F.text)
async def set_api_id_handler(message: Message, state: FSMContext):
    await state.update_data(api_id=int(message.text))
    await message.answer(
        text="Отлично, я записал введённый Вами <b>api_id</b>\n\n"
             "Теперь введите <b>api_hash</b> в ответном сообщении",
    )
    await state.set_state(AddAccountSG.api_hash)


@router.message(StateFilter(AddAccountSG.api_hash), F.text)
async def set_api_hash_handler(message: Message, state: FSMContext):
    await state.update_data(api_hash=message.text)
    await message.answer(
        text="Отлично, я записал введённый Вами <b>api_hash</b>\n\n"
             "Теперь отправьте мне номер телефона подключаемого аккаунта в "
             "таком формате: <b><em>+7XXXXXXXXXX</em></b>",
    )
    await state.set_state(AddAccountSG.phone)


@router.message(StateFilter(AddAccountSG.phone), F.text)
async def set_phone_handler(message: Message, state: FSMContext):
    await state.update_data(phone=message.text.strip())
    await message.answer(
        text="Отлично, я записал введённый Вами <b>номер телефона</b>\n\n"
             "Теперь пришлите мне пароль двухэтапной аутентификации добавляемого аккаунта (облачный пароль)",
    )
    await state.set_state(AddAccountSG.password)


@router.message(StateFilter(AddAccountSG.password), F.text)
async def set_password_handler(message: Message, state: FSMContext):
    await state.update_data(password=message.text.strip())
    await message.answer(
        text="Отлично, я записал введённый Вами <b>облачный пароль</b>\n\n"
             "Теперь отправьте мне базу данных с клиентами в формате .txt",
    )
    await state.set_state(AddAccountSG.db_name)


@router.message(StateFilter(AddAccountSG.db_name))
async def set_db_handler(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()

    file_id = message.document.file_id
    file = await bot.get_file(file_id)
    filename = f"{data['api_id']}_{data['api_hash']}"

    await bot.download_file(file.file_path, f"bot/dbs_users/{filename}.txt")
    await message.answer(
        text="Отлично, я сохранил базу клиентов!\n\n"
             "Теперь введите код-подтверждения из аккаунта, который Вы сейчас подключаете\n\n"
             "⚠️ Пожалуйста, пришлите мне код без лишних пробелов и символов!",
    )

    client = TelegramClient(
        session=f"bot/sessions/{data['api_id']}_{data['phone'][1:]}",
        api_id=data['api_id'],
        api_hash=data['api_hash'],
        system_version="4.16.30-vxCUSTOM",
    )
    await client.connect()
    req = await client.send_code_request(phone=data['phone'])
    await state.update_data(phone_code_hash=req.phone_code_hash, db_name=filename)
    await state.set_state(AddAccountSG.code)


@router.message(StateFilter(AddAccountSG.code), F.text)
async def set_code_handler(message: Message, state: FSMContext, session: AsyncSession):
    code = message.text.strip()
    data = await state.get_data()

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ Назад в меню", callback_data="go_back_to_menu"))

    success_message = message.answer(
        text="Аккаунт успешно подключен!",
        reply_markup=builder.as_markup(),
    )

    client = TelegramClient(
        session=f"bot/sessions/{data['api_id']}_{data['phone'][1:]}",
        api_id=data['api_id'],
        api_hash=data['api_hash'],
        system_version="4.16.30-vxCUSTOM",
    )
    await client.connect()
    try:
        await client.sign_in(
            phone=data['phone'],
            code=code,
            phone_code_hash=data['phone_code_hash'],
        )
        await success_message
    except AttributeError:
        await client.sign_in(
            phone=data['phone'],
            code=code,
            phone_code_hash=data['phone_code_hash'],
        )
    except SessionPasswordNeededError:
        await client.sign_in(
            password=data['password'],
        )
        await success_message
    except Exception:
        await message.answer(
            text="⚠️ Во время подключения аккаунт произошла ошибка!\n"
                 "⚠️ Свяжитесь с разработчиком!"
        )
    account = await client.get_me()
    await AccountDAO.add_account(
        session=session,
        api_id=data["api_id"],
        api_hash=data["api_hash"],
        phone=data["phone"],
        db_name=data["db_name"],
        username=account.username or f"account_{account.id}",
        fa2=data["password"],
    )
    async with aiofiles.open(
        file=f"bot/dbs_users/{data['api_id']}_{data['api_hash']}.txt",
        mode="r",
        encoding="utf-8",
    ) as f:
        users = [username.strip() for username in await f.readlines()]
        await UserDAO.insert_users(
            session=session,
            users=users,
            api_id=data['api_id'],
            api_hash=data['api_hash'],
        )
    await state.clear()
