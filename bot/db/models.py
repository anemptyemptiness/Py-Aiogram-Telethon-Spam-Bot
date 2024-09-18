from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey

from bot.db.base import Base


class Account(Base):
    __tablename__ = "account"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str]
    api_id: Mapped[int] = mapped_column(unique=True)
    api_hash: Mapped[str] = mapped_column(unique=True)
    phone: Mapped[str] = mapped_column(unique=True)
    fa2: Mapped[str] = mapped_column(nullable=True, default=None)
    spam_msg: Mapped[str] = mapped_column(nullable=True, default="")
    is_active: Mapped[bool] = mapped_column(default=False)
    db_name: Mapped[str] = mapped_column(unique=True)


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("account.id", ondelete="CASCADE"))
    username: Mapped[str]
    is_sent: Mapped[bool] = mapped_column(default=False)
