import datetime
from contextlib import contextmanager
from typing import List, Generator

import pytest
from sqlalchemy import insert, select, update, delete
from sqlalchemy.orm import Session
from tests.conftest import sync_db as db, Base, User


@pytest.fixture
def prepare_database() -> Generator[None, None, None]:
    db.run_sync(Base.metadata.create_all, is_session=False)
    yield
    db.run_sync(Base.metadata.drop_all, is_session=False)


@pytest.fixture
def fake_users(prepare_database) -> List[dict]:
    data = [
        {'id': i,
         "username": f'User-{i}',
         "password": f"password_{i}",
         "create_time": datetime.datetime.strptime(f"2022-01-0{i} 00:00:00", "%Y-%m-%d %H:%M:%S")
         } for i in range(1, 6)
    ]
    db.execute(insert(User).values(data), commit=True)
    return data


def test_session_maker(fake_users):
    with db.session_maker() as session:
        user = session.get(User, 1)
        assert user.id == 1


def test_session_generator(fake_users):
    with contextmanager(db.session_generator)() as session:
        user = session.get(User, 1)
        assert user.id == 1


def test_execute(fake_users):
    # update
    stmt = update(User).where(User.id == 1).values({'username': 'new_user'})
    result = db.execute(stmt, commit=True)
    assert result.rowcount == 1
    # select
    user = db.execute(select(User).where(User.id == 1), on_close_pre=lambda r: r.scalar())
    assert user.username == 'new_user'
    # insert
    stmt = insert(User).values({
        'id': 6,
        'username': 'User-6',
        'password': 'password_6'
    })
    result = db.execute(stmt, commit=True)
    assert result.rowcount == 1
    # delete
    stmt = delete(User).where(User.id == 6)
    result = db.execute(stmt, commit=True)
    assert result.rowcount == 1


def test_execute_connection(fake_users):
    # Select
    user = db.execute(select(User).where(User.id == 1), is_session=False, on_close_pre=lambda r: r.one())
    assert user.id == 1


def test_scalar(fake_users):
    user = db.scalar(select(User).where(User.id == 1))
    assert user.id == 1
    assert user.username == 'User-1'


def test_scalars_all(fake_users):
    stmt = select(User)
    result = db.scalars_all(stmt)
    assert len(result) == 5
    stmt = select(User).where(User.id < 3)
    result = db.scalars_all(stmt)
    assert len(result) == 2


def test_get(fake_users):
    user = db.get(User, 1)
    assert user.id == 1
    assert user.username == 'User-1'


def test_delete(fake_users):
    user = db.get(User, 1)
    assert user.id == 1
    db.delete(user)
    user = db.get(User, 1)
    assert user is None


def test_save(fake_users):
    # test update
    user = db.get(User, 1)
    assert user.id == 1
    user.username = 'new_user'
    db.save(user)
    user = db.get(User, 1)
    assert user.username == 'new_user'
    # test insert
    user2 = User(username='new_user2')
    db.save(user2)
    u = db.scalar(select(User).where(User.username == 'new_user2'))
    assert u.username == 'new_user2'
    # test refresh
    user3 = User(username='new_user3')
    db.save(user3, refresh=True)
    assert user3.id


def test_run_sync(fake_users):
    def delete_user(session: Session, instance: User):
        session.delete(instance)

    user = db.get(User, 1)
    assert user.id == 1
    db.run_sync(delete_user, user, is_session=True)
    user = db.get(User, 1)
    assert user is None

    # test on_close_pre
    def get_user(session: Session, user_id: int):
        return session.get(User, user_id)

    user_id = db.run_sync(get_user, 2, is_session=True, on_close_pre=lambda r: r.id)
    assert user_id == 2
