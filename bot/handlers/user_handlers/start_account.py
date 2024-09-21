import asyncio
import random
from datetime import datetime, UTC, timedelta
from math import ceil
from pathlib import Path

import aiofiles
from aiogram import Router, F, Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from telethon import TelegramClient
from telethon.errors import FloodWaitError, RPCError

from bot.callbacks.account import AccountCallback, PaginationCallbackData
from bot.db.models import Account
from bot.db.account.requests import AccountDAO
from bot.db.sessions.requests import SessionDAO
from bot.db.users.requests import UserDAO
from bot.fsm.fsm import AccountInfoSG

router = Router(name="start_account_router")


async def paginator(session: AsyncSession, page: int = 0):
    builder = InlineKeyboardBuilder()
    accounts = await AccountDAO.get_accounts(session=session)

    limit = 8
    start_offset = page * limit
    end_offset = start_offset + limit

    for account in accounts[start_offset:end_offset]:
        builder.row(InlineKeyboardButton(
            text=f'🖥 {account.username}',
            callback_data=AccountCallback(
                identification=account.id,
            ).pack()
        )
    )

    buttons_row = []

    if page > 0:
        buttons_row.append(
            InlineKeyboardButton(text="⬅️", callback_data=PaginationCallbackData(
                action="prev",
                page=page - 1,
            ).pack())
        )
    if end_offset < len(accounts):
        buttons_row.append(
            InlineKeyboardButton(text="➡️", callback_data=PaginationCallbackData(
                action="next",
                page=page + 1,
            ).pack())
        )

    builder.row(*buttons_row)
    builder.row(InlineKeyboardButton(
        text=f"---{page + 1 if accounts else 0}/{ceil(len(accounts) / limit)}---",
        callback_data="number_of_pages",
    ))
    builder.row(InlineKeyboardButton(text='⬅️ Назад', callback_data='go_back_to_menu'))

    return builder.as_markup()


def account_info(account: Account):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔔 Начать рассылку", callback_data="start_sending"))
    builder.row(InlineKeyboardButton(text="❌ Удалить аккаунт", callback_data="delete_account"))
    builder.row(InlineKeyboardButton(text="📁 Поменять базу клиентов", callback_data="delete_users_db"))
    builder.row(InlineKeyboardButton(text="💬 Сообщение рассылки", callback_data="spam_msg_info"))

    if account.is_active:
        builder.row(InlineKeyboardButton(text="Остановить рассылку", callback_data="stop_sending"))

    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_accounts"))

    message = (f"🖥 Аккаунт <b>@{account.username}</b>\n\n"
               f"☎️ Телефон: <em>{account.phone}</em>\n"
               f"🔐 Пароль: <em>{account.fa2}</em>\n"
               f"⚙️ Api_id: <em>{account.api_id}</em>\n"
               f"⚙️ Api_hash: <em>{account.api_hash}</em>\n\n"
               f"📁 База клиентов:\n<em>{account.db_name}.txt</em>\n\n"
               f"🤖 Бот активен: {'да ✅' if account.is_active else 'нет ❌'}")

    return message, builder


@router.callback_query(StateFilter(AccountInfoSG.accounts), F.data == "number_of_pages")
async def show_number_of_pages_handler(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(StateFilter(default_state), F.data == "start_account")
async def start_account_handler(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    await callback.answer()
    await callback.message.delete_reply_markup()
    await callback.message.edit_text(
        text="🖥 Аккаунты:",
        reply_markup=await paginator(session=session),
    )
    await state.set_state(AccountInfoSG.accounts)
    await state.update_data(page=0)


@router.callback_query(StateFilter(AccountInfoSG.accounts), F.data == "back_to_accounts")
async def back_to_accounts_handler(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    data = await state.get_data()
    page = data.get("page")
    message = callback.message.edit_text(
        text="🖥 Аккаунты:",
        reply_markup=await paginator(session=session, page=page)
    )

    if data.get("disconnected_dt", None):
        disconnected_dt = datetime.fromisoformat(data.get("disconnected_dt"))
        dt_now = datetime.now(tz=UTC)

        if disconnected_dt > dt_now:
            seconds_to_wait = (disconnected_dt - dt_now).seconds
            await callback.answer(
                text=f"⏳ Подождите {seconds_to_wait} секунд, рассылка отменяется!"
            )
            builder = InlineKeyboardBuilder()
            builder.add(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_accounts"))

            await callback.message.edit_text(
                text=f"⏳ Останавливаю рассылку, пожалуйста, подождите {seconds_to_wait} секунд!",
                reply_markup=builder.as_markup(),
            )
        else:
            await callback.answer()
            await state.update_data(disconnected_dt=None, is_disconnected=False)
            await message
    else:
        await callback.answer()
        await message


@router.callback_query(StateFilter(AccountInfoSG.accounts), PaginationCallbackData.filter())
async def pagination_handler(
        callback: CallbackQuery, callback_data: PaginationCallbackData, session: AsyncSession, state: FSMContext,
):
    await callback.answer()
    await callback.message.edit_text(
        text="🖥 Аккаунты:",
        reply_markup=await paginator(session=session, page=callback_data.page)
    )
    await state.update_data(page=callback_data.page)


@router.callback_query(StateFilter(AccountInfoSG.accounts), AccountCallback.filter())
async def user_info_handler(
        callback: CallbackQuery, callback_data: AccountCallback, session: AsyncSession, state: FSMContext,
):
    await callback.answer()
    account = await AccountDAO.get_account(session=session, id=callback_data.identification)
    await state.update_data(
        account_id=account.id,
        api_id=account.api_id,
        api_hash=account.api_hash,
        phone=account.phone,
    )

    info, builder = account_info(account)
    await callback.message.edit_text(
        text=f"{info}",
        reply_markup=builder.as_markup(),
    )


@router.callback_query(StateFilter(AccountInfoSG.accounts), F.data == "start_sending")
async def start_sending_handler(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    await callback.answer()

    data = await state.get_data()
    account = await AccountDAO.get_account(session=session, id=data["account_id"])
    error_message = (f"⚠️ Вероятнее всего, аккаунт @{account.username} получил блокировку "
                     "или произошла какая-то иная ошибка в результате "
                     "взаимодействия аккаунта или бота с Телеграм!\n\n"
                     "Возможные причины:\n"
                     "1) Пользователь мог поменять свой username и мы его не нашли, получив ошибку\n"
                     "2) Аккаунт получил блокировку от Телеграм\n"
                     "3) Рассылка прошла успешно, но Вы не были в меню аккаунта, вследствие чего "
                     "бот не смог отредактировать сообщение, а потому и сгенерировал ошибку, "
                     "но по сути всё хорошо, это не критично\n\n"
                     "Пожалуйста, зайдите на аккаунт и проверьте, нет ли визуально каких-либо ошибок?")

    client = TelegramClient(
        session=f"bot/sessions/{data['api_id']}_{data['phone'][1:]}",
        api_id=account.api_id,
        api_hash=account.api_hash,
        system_version="4.16.30-vxCUSTOM",
    )
    await client.connect()

    users = await UserDAO.get_users_by_account(
        session=session,
        api_id=account.api_id,
        api_hash=account.api_hash,
    )
    await AccountDAO.update_account(session=session, is_active=True)

    info, builder = account_info(account)
    await callback.message.edit_text(
        text=f"{info}",
        reply_markup=builder.as_markup(),
    )
    count: int = 0

    async with client:
        if not users:
            await callback.message.answer(
                text="Похоже, база клиентов для рассылки пустая 😓\n"
                     "Пожалуйста, обновите/загрузите базу клиентов!"
            )

        for user in users:
            if count != 30:
                if (await state.get_data()).get("is_disconnected", None):
                    # Рассылку отменили -> отменяем эту функцию, чтобы не рассылать больше
                    await state.update_data(is_disconnected=False)
                    task = asyncio.current_task()
                    task.cancel()
                    return
                else:
                    count += 1
                    try:
                        if not account.spam_msg:
                            # Если нет спам-сообщения, то просим его создать
                            raise KeyError
                        await client.send_message(
                            entity=f"{user}",
                            message=f"{account.spam_msg}",
                        )
                        await UserDAO.update_user_by_account(
                            session=session,
                            api_id=account.api_id,
                            api_hash=account.api_hash,
                            username=user,
                        )
                        await asyncio.sleep(random.randint(10, 20))
                    except FloodWaitError as flood:
                        # Если получили флуд от Телеграм, то ждем, пока флуд спадёт
                        await asyncio.sleep(flood.seconds + 1)
                        await client.send_message(
                            entity=f"{user.strip()}",
                            message=f"{account.spam_msg}",
                        )
                        await UserDAO.update_user_by_account(
                            session=session,
                            api_id=account.api_id,
                            api_hash=account.api_hash,
                            username=user,
                        )
                        await asyncio.sleep(random.randint(10, 20))
                    except ValueError:
                        # Если нет аккаунта на конкретный username, то обновим статус is_sent на True
                        # и пропустим юзера
                        await UserDAO.update_user_by_account(
                            session=session,
                            api_id=account.api_id,
                            api_hash=account.api_hash,
                            username=user,
                        )
                        await asyncio.sleep(random.randint(10, 20))
                        continue
                    except RPCError as e:
                        # Поймали ошибку от Телеграм
                        await callback.message.answer(
                            text=f"{error_message}",
                        )
                        await callback.message.bot.send_message(
                            chat_id=292972814,
                            text="Ошибка:\n\n"
                                 f"{e}"
                        )
                        await asyncio.sleep(random.randint(10, 20))
                        continue
                    except KeyError:
                        # Просим создать спам-сообщение для рассылки
                        await callback.message.answer(
                            text="Нечего отправлять 😔\n"
                                 "Пожалуйста, создайте рассылочное сообщение!",
                        )
                        break
                    except Exception as e:
                        # Либо поймали необработанную ошибку Телеграм, либо что-то иное
                        await callback.message.answer(
                            text=f"{error_message}",
                        )
                        await callback.message.bot.send_message(
                            chat_id=292972814,
                            text="Ошибка:\n\n"
                                 f"{e}"
                        )
                        await asyncio.sleep(random.randint(10, 20))
                        continue
            else:
                # Разослали 10 людям сообщение, спим 1.5 суток, чтобы аккаунт отдохнул,
                # иначе Телеграм может дать бан за частую рассылку
                await callback.message.answer(
                    text=f"✅ Бот разослал сообщение {count} раз ({count} людей)\n"
                         "💤 Бот в спячке на 1.5 дня (36 часов)"
                )

                count = 0
                await asyncio.sleep(60 * 60 * 24 * 1.5)  # спим 1.5 дня (36 часов)

        # Рассылка прошла успешно
        # или мы экстренно завершили её, потому что:
        # 1) нет рассылочного сообщения
        # 2) поймали ошибку от Телеграм
        # 3) поймали ошибку от aiogram/telethon/Python
        await AccountDAO.update_account(session=session, is_active=False)
        info, builder = account_info(account)
        await callback.message.edit_text(
            text=f"{info}",
            reply_markup=builder.as_markup(),
        )


@router.callback_query(StateFilter(AccountInfoSG.accounts), F.data == "delete_account")
async def delete_account_handler(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    await callback.answer()
    await callback.message.delete_reply_markup()

    data = await state.get_data()
    account = await AccountDAO.get_account(session=session, id=data["account_id"])

    client = TelegramClient(
        session=f"bot/sessions/{data['api_id']}_{data['phone'][1:]}",
        api_id=account.api_id,
        api_hash=account.api_hash,
        system_version="4.16.30-vxCUSTOM",
    )
    await client.connect()

    async with client:
        await client.log_out()

    unsend_accounts = await UserDAO.get_users_by_account(
        session=session,
        api_id=account.api_id,
        api_hash=account.api_hash,
    )

    if unsend_accounts:
        # Если есть аккаунты, до которых не дошла рассылка из-за блокировки,
        # то собираем эти аккаунты в .txt и отправляем, чтобы дальше работать с ними
        async with aiofiles.open(
                file=f"bot/dbs_users/saved_unsend_accounts/{account.api_id}_{account.api_hash}.txt",
                mode="r+"
        ) as file:
            await file.writelines(map(lambda x: x + "\n", unsend_accounts))
        await callback.message.answer_document(
            document=FSInputFile(path=Path(f"bot/dbs_users/saved_unsend_accounts/{account.api_id}_{account.api_hash}.txt"))
        )

    await AccountDAO.delete_account(session=session, id=data["account_id"])
    await SessionDAO.delete_session(api_id=account.api_id, phone=account.phone)

    await callback.message.answer(
        text=f"Аккаунт <b>@{account.username}</b> успешно удален ✅\n\n"
             "🖥 Аккаунты:",
        reply_markup=await paginator(session, data["page"])
    )


@router.callback_query(StateFilter(AccountInfoSG.accounts), F.data == "delete_users_db")
async def delete_users_db_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.delete_reply_markup()

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_account_info"))

    await callback.message.answer(
        text="Пришлите новый <b>.txt</b> файл базы клиентов!",
        reply_markup=builder.as_markup(),
    )
    await state.set_state(AccountInfoSG.change_db)


@router.message(StateFilter(AccountInfoSG.change_db))
async def change_db_handler(message: Message, session: AsyncSession, state: FSMContext, bot: Bot):
    data = await state.get_data()

    file_id = message.document.file_id
    file = await bot.get_file(file_id)
    filename = f"{data['api_id']}_{data['api_hash']}"

    await bot.download_file(file.file_path, f"bot/dbs_users/{filename}.txt")
    await message.answer(
        text="Отлично, я сохранил новую базу клиентов ✅",
    )

    account = await AccountDAO.get_account(session=session, id=data["account_id"])
    info, builder = account_info(account)

    await message.edit_text(
        text=f"{info}",
        reply_markup=builder.as_markup(),
    )
    await state.set_state(AccountInfoSG.accounts)


@router.callback_query(StateFilter(AccountInfoSG.accounts), F.data == "spam_msg_info")
async def spam_msg_info_handler(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    await callback.answer()
    await callback.message.delete_reply_markup()
    data = await state.get_data()
    account = await AccountDAO.get_account(session=session, id=data["account_id"])

    if not account.spam_msg:
        await callback.message.answer(
            text="Пришлите мне в ответном сообщение оформленное сообщение для рассылки",
        )
        await state.set_state(AccountInfoSG.change_spam_msg)
    else:
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="🔄 Изменить", callback_data="change_spam_msg"))
        builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_account_info"))

        await callback.message.answer(
            text="Ваше рассылочное сообщение:\n\n"
                 f"{account.spam_msg}",
            reply_markup=builder.as_markup(),
        )


@router.callback_query(StateFilter(AccountInfoSG.accounts), F.data == "change_spam_msg")
async def change_spam_msg_cb_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.delete_reply_markup()
    await callback.message.answer(
        text="Пришлите мне в ответном сообщение оформленное сообщение для рассылки",
    )
    await state.set_state(AccountInfoSG.change_spam_msg)


@router.message(StateFilter(AccountInfoSG.change_spam_msg), F.text)
async def change_spam_msg_handler(message: Message, session: AsyncSession, state: FSMContext):
    await state.update_data(spam_msg=message.text.strip())
    await AccountDAO.update_account(session=session, spam_msg=message.text.strip())
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_account_info"))

    await message.answer(
        text="Ваше рассылочное сообщение:\n\n"
             f"{message.text.strip()}",
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data == "back_to_account_info")
async def back_to_account_info_handler(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    await callback.answer()
    await callback.message.delete_reply_markup()

    data = await state.get_data()
    account = await AccountDAO.get_account(session=session, id=data["account_id"])
    info, builder = account_info(account)

    await callback.message.answer(
        text=f"{info}",
        reply_markup=builder.as_markup(),
    )
    await state.set_state(AccountInfoSG.accounts)


@router.callback_query(StateFilter(AccountInfoSG.accounts), F.data == "stop_sending")
async def stop_sending_handler(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    await callback.answer()
    await state.update_data(
        is_disconnected=True,
        disconnected_dt=(datetime.now(tz=UTC) + timedelta(seconds=20)).isoformat(),
    )
    await AccountDAO.update_account(session=session, is_active=False)

    data = await state.get_data()
    seconds_to_wait = (datetime.fromisoformat(data["disconnected_dt"]) - datetime.now(tz=UTC)).seconds

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_accounts"))

    await callback.message.edit_text(
        text=f"⏳ Останавливаю рассылку, пожалуйста, подождите {seconds_to_wait} секунд!",
        reply_markup=builder.as_markup(),
    )
