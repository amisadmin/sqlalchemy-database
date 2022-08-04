import datetime
from typing import AsyncGenerator, List, Union

import pytest
from sqlalchemy import insert, select, update, delete
from sqlalchemy.orm import Session
from sqlalchemy_database import AsyncDatabase, Database
from tests.conftest import async_db, sync_db, Base, User


@pytest.fixture(params=[async_db, sync_db])
def db(request) -> Union[Database, AsyncDatabase]:
    return request.param


@pytest.fixture()
async def prepare_database(db) -> AsyncGenerator[None, None]:
    await db.async_run_sync(Base.metadata.create_all, is_session=False)
    yield
    await db.async_run_sync(Base.metadata.drop_all, is_session=False)


@pytest.fixture
async def fake_users(db, prepare_database) -> List[dict]:
    data = [
        {'id': i,
         "username": f'User-{i}',
         "password": f"password_{i}",
         "create_time": datetime.datetime.strptime(f"2022-01-0{i} 00:00:00", "%Y-%m-%d %H:%M:%S")
         } for i in range(1, 6)
    ]
    await db.async_execute(insert(User).values(data))
    return data


async def test_async_execute(db, fake_users):
    # update
    stmt = update(User).where(User.id == 1).values({'username': 'new_user'})
    result = await db.async_execute(stmt)
    assert result.rowcount == 1
    # select
    user = await db.async_execute(select(User).where(User.id == 1), on_close_pre=lambda r: r.scalar())
    assert user.username == 'new_user'
    # insert
    stmt = insert(User).values({
        'id': 6,
        'username': 'User-6',
        'password': 'password_6'
    })
    result = await db.async_execute(stmt)
    assert result.rowcount == 1
    # delete
    stmt = delete(User).where(User.id == 6)
    result = await db.async_execute(stmt)
    assert result.rowcount == 1


async def test_async_execute_connection(db, fake_users):
    # Select
    user = await db.async_execute(select(User).where(User.id == 1), is_session=False, on_close_pre=lambda r: r.one())
    assert user.id == 1


async def test_async_scalar(db, fake_users):
    user = await db.async_scalar(select(User).where(User.id == 1))
    assert user.id == 1
    assert user.username == 'User-1'


async def test_async_scalars_all(db, fake_users):
    stmt = select(User)
    result = await db.async_scalars_all(stmt)
    assert len(result) == 5
    stmt = select(User).where(User.id < 3)
    result = await db.async_scalars_all(stmt)
    assert len(result) == 2


async def test_async_get(db, fake_users):
    user = await db.async_get(User, 1)
    assert user.id == 1
    assert user.username == 'User-1'


async def test_async_delete(db, fake_users):
    user = await db.async_get(User, 1)
    assert user.id == 1
    await db.async_delete(user)
    user = await db.async_get(User, 1)
    assert user is None


async def test_async_save(db, fake_users):
    # test update
    user = await db.async_get(User, 1)
    assert user.id == 1
    user.username = 'new_user'
    await db.async_save(user)
    user = await db.async_get(User, 1)
    assert user.username == 'new_user'
    # test insert
    user2 = User(username='new_user2')
    await db.async_save(user2)
    u = await db.async_scalar(select(User).where(User.username == 'new_user2'))
    assert u.username == 'new_user2'
    # test refresh
    user3 = User(username='new_user3')
    await db.async_save(user3, refresh=True)
    assert user3.id


async def test_async_run_sync(db, fake_users):
    def delete_user(session: Session, instance: User):
        session.delete(instance)

    user = await db.async_get(User, 1)
    assert user.id == 1
    await db.async_run_sync(delete_user, user)
    user = await db.async_get(User, 1)
    assert user is None

    # test on_close_pre
    def get_user(session: Session, user_id: int):
        return session.get(User, user_id)

    user_id = await db.async_run_sync(get_user, 2, on_close_pre=lambda r: r.id)
    assert user_id == 2
