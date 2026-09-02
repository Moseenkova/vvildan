from sqlalchemy import select

from src.database import CustomerTgTopic, async_session_maker


async def get_topic_id_by_customer_chat_id(customer_chat_id: int) -> int | None:
    async with async_session_maker() as session:
        result = await session.execute(
            select(CustomerTgTopic.topic_id).where(
                CustomerTgTopic.customer_chat_id == customer_chat_id
            )
        )
        return result.scalar_one_or_none()


async def create_customer_tg_topic(customer_chat_id: int, topic_id: int) -> int:
    async with async_session_maker() as session:
        session.add(
            CustomerTgTopic(
                customer_chat_id=customer_chat_id,
                topic_id=topic_id,
            )
        )
        await session.commit()

    return topic_id


async def get_customer_chat_id_by_topic_id(topic_id: int) -> int | None:
    async with async_session_maker() as session:
        result = await session.execute(
            select(CustomerTgTopic.customer_chat_id).where(
                CustomerTgTopic.topic_id == topic_id
            )
        )
        return result.scalar_one_or_none()
