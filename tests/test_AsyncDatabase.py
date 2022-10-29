import asyncio
from asyncio import AbstractEventLoop
from contextlib import asynccontextmanager

import pytest
from sqlalchemy import delete, insert, select, update
from sqlalchemy.orm import Session, selectinload

from tests.conftest import Group, User, async_db


async def test_session_maker():
    user = await async_db.session.get(User, 1)
    assert user.id == 1


async def test_session_generator():
    async with asynccontextmanager(async_db.session_generator)() as session:
        user = await session.get(User, 1)
        assert user.id == 1


async def test_execute():
    # update
    stmt = update(User).where(User.id == 1).values({"username": "new_user"})
    result = await async_db.session.execute(stmt)
    assert result.rowcount == 1
    # select
    result = await async_db.session.execute(select(User).where(User.id == 1))
    user = result.scalar()
    assert user.username == "new_user"
    # insert
    stmt = insert(User).values({"id": 6, "username": "User-6", "password": "password_6"})
    result = await async_db.session.execute(stmt)
    assert result.rowcount == 1
    # delete
    stmt = delete(User).where(User.id == 6)
    result = await async_db.session.execute(stmt)
    assert result.rowcount == 1


async def test_run_sync():
    def delete_user(session: Session, instance: User):
        session.delete(instance)

    user = await async_db.session.get(User, 1)
    assert user.id == 1
    await async_db.run_sync(delete_user, user)
    await async_db.session.flush()
    user = await async_db.session.get(User, 1)
    assert user is None

    # test on_close_pre
    def get_user(session: Session, user_id: int):
        return session.get(User, user_id)

    user = await async_db.run_sync(get_user, 2)
    assert user.id == 2


async def test_executor():
    user = await async_db.session.get(User, 1)
    assert user.id == 1
    assert user.username == "User-1"
    assert user.group_id is None
    assert user.group is None
    # test relationship
    group = Group(name="group1")

    user.group = group
    await async_db.session.flush()
    assert user.group_id == group.id
    assert user.group.name == "group1"  # type: ignore

    user2 = await async_db.session.get(User, 2, options=[selectinload(User.group)])
    assert user2.group is None

    user3 = await async_db.session.scalar(select(User).where(User.id == 3))
    assert user3.group is None

    users = await async_db.session.scalars(select(User))
    for user in users:
        assert user.group is None if user.group_id is None else user.group


async def test_sqlmodel_session():
    from sqlmodel import select

    result = await async_db.session.exec(select(User))
    user = result.first()
    assert user.id == 1


@pytest.fixture()
def lock(event_loop: AbstractEventLoop):
    return asyncio.Lock()


async def test_async_session_context_var(lock, i=1):
    global_session = async_db.session  # Default global session
    assert not async_db.scoped
    async with async_db() as session:  # Enter a new session
        assert async_db.scoped
        user = await session.get(User, 1)
        assert user.id == 1
        assert session is async_db.session
        assert session is not global_session
        # test nested session
        async with async_db() as session2:  # Enter a nested new session
            user = await session2.get(User, 1)
            assert user.id == 1
            assert session2 is async_db.session
            assert session2 is not session
            assert session2 is not global_session
        assert session is async_db.session
        # test dba.session
        user = await async_db.session.get(User, 1, options=[selectinload(User.group)])
        assert user.id == 1

        group = Group(name=f"group{i}")

        async with lock:  # test async concurrency safe, because the same user is operated here, so a lock is needed
            user.group = group
            # await session.commit()
            await session.flush()
            await session.refresh(user)
            assert user.group_id == group.id
            assert user.group.name == f"group{i}"  # type: ignore
    # Exit the context and restore the global session
    assert async_db.session is global_session
    user2 = await async_db.session.get(User, 2)
    assert user2.group is None
    return i


def test_asyncio_groups(event_loop: AbstractEventLoop, lock):
    task_count = 40
    tasks = [asyncio.ensure_future(test_async_session_context_var(lock, i=i)) for i in range(task_count)]
    event_loop.run_until_complete(asyncio.wait(tasks))
    assert len(tasks) == task_count
    for task in tasks:
        assert task.result() is not None
        assert task.exception() is None
