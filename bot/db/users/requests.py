from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Account, User


class UserDAO:
    @classmethod
    async def insert_users(
            cls,
            session: AsyncSession,
            api_id: int | str,
            api_hash: str,
            users: list,
    ):
        account_id = select(Account.id).filter_by(api_id=api_id, api_hash=api_hash).scalar_subquery()
        stmt = insert(User).values([
            {"username": user, "account_id": account_id} for user in users
        ])
        await session.execute(stmt)
        await session.commit()

    @classmethod
    async def get_users_by_account(
            cls,
            session: AsyncSession,
            api_id: int | str,
            api_hash: str,
    ):
        query = (
            select(User.username)
            .select_from(User)
            .join(Account, Account.id == User.account_id)
            .where(
                Account.api_id == api_id,
                Account.api_hash == api_hash,
                User.is_sent == False,
            )
            .order_by(User.id)
        )
        result = await session.execute(query)
        return result.scalars().all()

    @classmethod
    async def update_user_by_account(
            cls,
            session: AsyncSession,
            username: str,
            api_id: int | str,
            api_hash: str,
    ):
        account_id = select(Account.id).filter_by(api_id=api_id, api_hash=api_hash).scalar_subquery()
        stmt = (
            update(User)
            .values(is_sent=True)
            .where(
                User.username == username,
                User.account_id == account_id,
            )
        )
        await session.execute(stmt)
        await session.commit()