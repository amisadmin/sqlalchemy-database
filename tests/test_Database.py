import threading
from concurrent.futures import ALL_COMPLETED, ThreadPoolExecutor, wait
from contextlib import contextmanager

from sqlalchemy import select
from sqlalchemy.orm import Session

from tests.conftest import Group, User, sync_db


def test_session_maker():
    with sync_db.session_maker() as session:
        user = session.get(User, 1)
        assert user.id == 1


def test_session_generator():
    with contextmanager(sync_db.session_generator)() as session:
        user = session.get(User, 1)
        assert user.id == 1


def test_get():
    user = sync_db.session.get(User, 1)
    assert user.id == 1
    assert user.username == "User-1"


def test_run_sync():
    def delete_user(session: Session, instance: User):
        session.delete(instance)

    user = sync_db.session.get(User, 1)
    assert user.id == 1
    sync_db.run_sync(delete_user, user, is_session=True)
    sync_db.session.commit()

    user = sync_db.session.get(User, 1)
    assert user is None

    # test get
    def get_user(session: Session, user_id: int):
        return session.get(User, user_id)

    user = sync_db.run_sync(get_user, 2, is_session=True)
    assert user.id == 2


def test_executor():
    user = sync_db.session.get(User, 1)
    assert user.id == 1
    assert user.username == "User-1"
    assert user.group_id is None
    assert user.group is None

    # test relationship
    group = Group(name="group1")
    user.group = group
    sync_db.session.flush()
    assert group.id == 1
    assert user.group_id == group.id
    assert user.group.name == "group1"  # type: ignore

    user2 = sync_db.session.get(User, 2)
    assert user2.group is None

    user3 = sync_db.session.scalar(select(User).where(User.id == 3))
    assert user3.group is None

    users = sync_db.session.scalars(select(User))
    for user in users:
        assert user.group is None if user.group_id is None else user.group


def test_sqlmodel_session():
    from sqlmodel import select

    user = sync_db.session.exec(select(User)).first()
    assert user.id == 1


lock = threading.Lock()


def test_session_context_var(i=1):
    global_session = sync_db.session  # Default global session
    assert not sync_db.scoped
    with sync_db() as session:  # Enter a new session
        assert sync_db.scoped
        user = session.get(User, 1)
        assert user.id == 1
        assert session is sync_db.session
        assert session is not global_session
        # test nested session
        with sync_db() as session2:  # Enter a nested new session
            user = session2.get(User, 1)
            assert user.id == 1
            assert session2 is sync_db.session
            assert session2 is not session
            assert session2 is not global_session
        assert session is sync_db.session
        # test dbs.session
        user = sync_db.session.get(User, 1)
        assert user.id == 1

        group = Group(name=f"group{i}")

        with lock:  # test thread safe, because the same user is operated here, so a lock is needed
            user.group = group
            session.commit()
            assert user.group_id == group.id
            assert user.group.name == f"group{i}"  # type: ignore
    # Exit the context and restore the global session
    assert sync_db.session is global_session
    user2 = sync_db.session.get(User, 2)
    assert user2.group is None
    return i


def test_ThreadPoolExecutor():
    task_count = 40
    pool = ThreadPoolExecutor(max_workers=20)  # 创建线程池,设置最大线程数
    all_task = [pool.submit(test_session_context_var, k) for k in range(task_count)]  # 投递任务
    done, fail = wait(all_task, return_when=ALL_COMPLETED)  # 等待线程运行完毕
    results = {task.result() for task in done}
    assert len(results) == task_count
