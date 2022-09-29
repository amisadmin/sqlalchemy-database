import datetime
import threading
from concurrent.futures import ALL_COMPLETED, ThreadPoolExecutor, wait
from contextlib import contextmanager
from typing import Generator, List

import pytest
from sqlalchemy import delete, insert, select, update
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import DetachedInstanceError

from tests.conftest import Base, Group, User
from tests.conftest import sync_db as db


@pytest.fixture
def prepare_database() -> Generator[None, None, None]:
    db.run_sync(Base.metadata.create_all, is_session=False)
    yield
    db.run_sync(Base.metadata.drop_all, is_session=False)


@pytest.fixture
def fake_users(prepare_database) -> List[dict]:
    data = [
        {
            "id": i,
            "username": f"User-{i}",
            "password": f"password_{i}",
            "create_time": datetime.datetime.strptime(f"2022-01-0{i} 00:00:00", "%Y-%m-%d %H:%M:%S"),
        }
        for i in range(1, 6)
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
    stmt = update(User).where(User.id == 1).values({"username": "new_user"})
    result = db.execute(stmt, commit=True)
    assert result.rowcount == 1
    # select
    user = db.execute(select(User).where(User.id == 1), on_close_pre=lambda r: r.scalar())
    assert user.username == "new_user"
    # insert
    stmt = insert(User).values({"id": 6, "username": "User-6", "password": "password_6"})
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
    assert user.username == "User-1"


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
    assert user.username == "User-1"


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
    user.username = "new_user"
    db.save(user)
    user = db.get(User, 1)
    assert user.username == "new_user"
    # test insert
    user2 = User(username="new_user2")
    db.save(user2)
    u = db.scalar(select(User).where(User.username == "new_user2"))
    assert u.username == "new_user2"
    # test refresh
    user3 = User(username="new_user3")
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


def test_executor(fake_users):
    user = db.get(User, 1)
    assert user.id == 1
    assert user.username == "User-1"
    assert user.group_id is None
    with pytest.raises(DetachedInstanceError):
        assert user.group is None

    # test relationship
    group = Group(name="group1")
    with db.session_maker() as session:
        db.save(group, refresh=True, session=session)
        assert group.id == 1
        user.group_id = group.id
        db.save(user, refresh=True, session=session)
        assert user.group_id == group.id
        assert user.group.name == "group1"  # type: ignore

        user2 = db.get(User, 2, session=session)
        assert user2.group is None

        user3 = db.scalar(select(User).where(User.id == 3), session=session)
        assert user3.group is None

        users = db.scalars_all(select(User), session=session)
        for user in users:
            assert user.group is None if user.group_id is None else user.group


def test_sqlmodel_session(fake_users):
    from sqlmodel import select

    with db.session_maker() as session:
        user = session.exec(select(User)).first()
        assert user.id == 1


lock = threading.Lock()


def test_session_context_var(fake_users, i=1):
    with db() as session:
        # test enter return session
        user = session.get(User, 1)
        assert user.id == 1
        assert session is db.session
        # test nested session
        with db() as session2:
            user = session2.get(User, 1)
            assert user.id == 1
            assert session2 is db.session
            assert session is not session2
        assert session is db.session
        # test db.session
        user = db.session.get(User, 1)
        assert user.id == 1

        # test db function
        user = db.get(User, 1)
        assert user.id == 1
        group = Group(name=f"group{i}")
        db.save(group, refresh=True)

        with lock:  # test thread safe, because the same user is operated here, so a lock is needed
            user.group_id = group.id
            db.save(user, refresh=True)
            assert user.group_id == group.id
            assert user.group.name == f"group{i}"  # type: ignore

        user2 = db.get(User, 2)
        assert user2.group is None

        user3 = db.scalar(select(User).where(User.id == 3))
        assert user3.group is None

        users = db.scalars_all(select(User))
        for user in users:
            assert user.group is None if user.group_id is None else user.group
    assert db.session is None
    return i


def test_ThreadPoolExecutor(fake_users):
    task_count = 40
    pool = ThreadPoolExecutor(max_workers=20)  # 创建线程池,设置最大线程数
    all_task = [pool.submit(test_session_context_var, fake_users, k) for k in range(task_count)]  # 投递任务
    # print(all_task)
    done, fail = wait(all_task, return_when=ALL_COMPLETED)  # 等待线程运行完毕
    results = {task.result() for task in done}
    assert len(results) == task_count
