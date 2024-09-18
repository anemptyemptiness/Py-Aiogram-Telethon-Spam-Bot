from sqlalchemy import select, update, delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Account


class AccountDAO:
    @classmethod
    async def get_accounts(
            cls,
            session: AsyncSession,
    ):
        query = select(Account).order_by(Account.id)
        result = await session.execute(query)
        return result.scalars().all()

    @classmethod
    async def get_account(
            cls,
            session: AsyncSession,
            id: int,
    ):
        query = select(Account).where(Account.id == id)
        result = await session.execute(query)
        return result.scalar()

    @classmethod
    async def add_account(
            cls,
            session: AsyncSession,
            **kwargs,
    ):
        stmt = insert(Account).values(**kwargs)
        await session.execute(stmt)
        await session.commit()

    @classmethod
    async def update_account(
            cls,
            session: AsyncSession,
            **kwargs,
    ):
        stmt = update(Account).values(**kwargs)
        await session.execute(stmt)
        await session.commit()

    @classmethod
    async def delete_account(
            cls,
            session: AsyncSession,
            id: int,
    ):
        stmt = delete(Account).where(Account.id == id)
        await session.execute(stmt)
        await session.commit()
