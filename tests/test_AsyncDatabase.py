import datetime
from contextlib import asynccontextmanager
from typing import AsyncGenerator, List

import pytest_asyncio
from sqlalchemy import insert, select, update, delete
from sqlalchemy.orm import Session

from tests.conftest import async_db as db, Base, User


@pytest_asyncio.fixture
async def prepare_database() -> AsyncGenerator[None, None]:
    await db.async_run_sync(Base.metadata.create_all, is_session=False)
    yield
    await db.async_run_sync(Base.metadata.drop_all, is_session=False)


@pytest_asyncio.fixture
async def fake_users(prepare_database) -> List[dict]:
    data = [
        {'id': i,
         "username": f'User-{i}',
         "password": f"password_{i}",
         "create_time": datetime.datetime.strptime(f"2022-01-0{i} 00:00:00", "%Y-%m-%d %H:%M:%S")
         } for i in range(1, 6)
    ]
    await db.execute(insert(User).values(data))
    return data


async def test_session_maker(fake_users):
    async with db.session_maker() as session:
        user = await session.get(User, 1)
        assert user.id == 1


async def test_session_generator(fake_users):
    async with asynccontextmanager(db.session_generator)() as session:
        user = await session.get(User, 1)
        assert user.id == 1


async def test_execute(fake_users):
    # update
    stmt = update(User).where(User.id == 1).values({'username': 'new_user'})
    result = await db.execute(stmt)
    assert result.rowcount == 1
    # select
    user = await db.execute(select(User).where(User.id == 1), commit=False, on_close_pre=lambda r: r.scalar())
    assert user.username == 'new_user'
    # insert
    stmt = insert(User).values({
        'id': 6,
        'username': 'User-6',
        'password': 'password_6'
    })
    result = await db.execute(stmt)
    assert result.rowcount == 1
    # delete
    stmt = delete(User).where(User.id == 6)
    result = await db.execute(stmt)
    assert result.rowcount == 1


async def test_execute_connection(fake_users):
    # Select
    user = await db.async_execute(select(User).where(User.id == 1), is_session=False, on_close_pre=lambda r: r.one())
    assert user.id == 1


async def test_scalar(fake_users):
    user = await db.scalar(select(User).where(User.id == 1))
    assert user.id == 1
    assert user.username == 'User-1'


async def test_scalars_all(fake_users):
    stmt = select(User)
    result = await db.scalars_all(stmt)
    assert len(result) == 5
    stmt = select(User).where(User.id < 3)
    result = await db.scalars_all(stmt)
    assert len(result) == 2


async def test_get(fake_users):
    user = await db.get(User, 1)
    assert user.id == 1
    assert user.username == 'User-1'


async def test_delete(fake_users):
    user = await db.get(User, 1)
    assert user.id == 1
    await db.delete(user)
    user = await db.get(User, 1)
    assert user is None


async def test_save(fake_users):
    # test update
    user = await db.get(User, 1)
    assert user.id == 1
    user.username = 'new_user'
    await db.save(user)
    user = await db.get(User, 1)
    assert user.username == 'new_user'
    # test insert
    user2 = User(username='new_user2')
    await db.save(user2)
    u = await db.scalar(select(User).where(User.username == 'new_user2'))
    assert u.username == 'new_user2'
    # test refresh
    user3 = User(username='new_user3')
    await db.save(user3, refresh=True)
    assert user3.id

async def test_run_sync(fake_users):
    def delete_user(session: Session, instance: User):
        session.delete(instance)

    user = await db.get(User, 1)
    assert user.id == 1
    await db.run_sync(delete_user, user)
    user = await db.get(User, 1)
    assert user is None

    # test on_close_pre
    def get_user(session: Session, user_id: int):
        return session.get(User, user_id)

    user_id = await db.run_sync(get_user, 2, on_close_pre=lambda r: r.id)
    assert user_id == 2
