from sqlalchemy import delete, insert, select, update
from sqlalchemy.orm import Session

from tests.conftest import Group, User


async def test_async_execute(db):
    # update
    stmt = update(User).where(User.id == 1).values({"username": "new_user"})
    result = await db.async_execute(stmt)
    assert result.rowcount == 1
    # select
    result = await db.async_execute(select(User).where(User.id == 1))
    user = result.scalar()
    assert user.username == "new_user"
    # insert
    stmt = insert(User).values({"id": 6, "username": "User-6", "password": "password_6"})
    result = await db.async_execute(stmt)
    assert result.rowcount == 1
    # delete
    stmt = delete(User).where(User.id == 6)
    result = await db.async_execute(stmt)
    assert result.rowcount == 1


async def test_async_scalar(db):
    user = await db.async_scalar(select(User).where(User.id == 1))
    assert user.id == 1
    assert user.username == "User-1"


async def test_async_scalars(db):
    stmt = select(User)
    result = await db.async_scalars(stmt)
    assert len(result.all()) == 5
    stmt = select(User).where(User.id < 3)
    result = await db.async_scalars(stmt)
    assert len(result.all()) == 2


async def test_async_get(db):
    user = await db.async_get(User, 1)
    assert user.id == 1
    assert user.username == "User-1"


async def test_async_delete(db):
    user = await db.async_get(User, 1)
    assert user.id == 1
    await db.async_delete(user)
    await db.async_commit()
    user = await db.async_get(User, 1)
    assert user is None


async def test_async_save(db):
    # test update
    user = await db.async_get(User, 1)
    assert user.id == 1
    user.username = "new_user"
    await db.async_flush()
    user = await db.async_get(User, 1)
    assert user.username == "new_user"
    # test insert
    user2 = User(username="new_user2")
    db.add(user2)
    await db.async_flush([user2])
    u = await db.async_scalar(select(User).where(User.username == "new_user2"))
    assert u.username == "new_user2"
    # test refresh
    user3 = User(username="new_user3")
    db.add(user3)
    await db.async_flush([user3])
    assert user3.id


async def test_async_run_sync(db):
    def delete_user(session: Session, instance: User):
        session.delete(instance)

    user = await db.async_get(User, 1)
    assert user.id == 1
    await db.async_run_sync(delete_user, user)
    await db.async_flush()
    user = await db.async_get(User, 1)
    assert user is None

    # test db function
    def get_user(session: Session, user_id: int):
        return session.get(User, user_id)

    user = await db.async_run_sync(get_user, 2)
    assert user.id == 2


async def test_async_session_context_var(db):
    global_session = db.session
    async with db():
        assert db.session is not global_session
        # test db function
        user = await db.async_get(User, 1)
        assert user.id == 1
        group = Group(name="group1")
        user.group = group
        await db.async_flush()
        await db.async_refresh(user)
        assert group.id == 1
        user.group_id = group.id

    assert db.session is global_session
