from bot.config import redis


class SessionDAO:
    @classmethod
    async def delete_session(
            cls,
            api_id: int | str,
            phone: str,
    ):
        pattern = f"telethon:client:{api_id}_{phone[1:]}:*"

        for key in await redis.keys(pattern):
            await redis.delete(key)
