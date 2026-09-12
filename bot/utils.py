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


async def get_customer_topic_by_customer_chat_id(
    customer_chat_id: int,
) -> CustomerTgTopic | None:
    async with async_session_maker() as session:
        return await session.scalar(
            select(CustomerTgTopic).where(CustomerTgTopic.customer_chat_id == customer_chat_id)
        )


async def get_customer_topic_by_topic_id(topic_id: int) -> CustomerTgTopic | None:
    async with async_session_maker() as session:
        return await session.scalar(
            select(CustomerTgTopic).where(CustomerTgTopic.topic_id == topic_id)
        )


async def create_customer_tg_topic(
    customer_chat_id: int,
    topic_id: int,
    language_code: str | None,
) -> int:
    async with async_session_maker() as session:
        session.add(
            CustomerTgTopic(
                customer_chat_id=customer_chat_id,
                topic_id=topic_id,
                language_code=language_code,
            )
        )
        await session.commit()

    return topic_id


async def get_customer_chat_id_by_topic_id(topic_id: int) -> int | None:
    async with async_session_maker() as session:
        result = await session.execute(
            select(CustomerTgTopic.customer_chat_id).where(CustomerTgTopic.topic_id == topic_id)
        )
        return result.scalar_one_or_none()


async def update_customer_topic_language(
    topic_id: int,
    language_code: str,
) -> bool:
    async with async_session_maker() as session:
        topic = await session.scalar(
            select(CustomerTgTopic).where(CustomerTgTopic.topic_id == topic_id)
        )
        if topic is None:
            return False

        topic.language_code = language_code
        topic.last_openai_response_id = None
        await session.commit()
        return True


async def update_customer_topic_response_id(
    topic_id: int,
    response_id: str,
) -> bool:
    async with async_session_maker() as session:
        topic = await session.scalar(
            select(CustomerTgTopic).where(CustomerTgTopic.topic_id == topic_id)
        )
        if topic is None:
            return False

        topic.last_openai_response_id = response_id
        await session.commit()
        return True
