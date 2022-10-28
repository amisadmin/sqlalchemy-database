from typing import List

from fastapi import Depends, FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.testclient import TestClient

from tests.conftest import User, async_db, sync_db

global_sync_session = sync_db.session  # Default global session


def get_users() -> List[User]:
    assert sync_db.session is not global_sync_session
    users = sync_db.session.scalars(select(User))
    """1. If the session is used in a non-dependency function, the session is global.
    2. If the session is used in a dependency function, the session is bound to the fastapi request.
    3. You can also create a new session for a function separately.
    """
    return users.all()


def test_sync_db_in_fastapi():
    app = FastAPI()
    sub_app = FastAPI()
    app.mount("/sub", sub_app)
    app.add_middleware(BaseHTTPMiddleware, dispatch=sync_db.asgi_dispatch)
    client = TestClient(app)

    @app.get("/users")
    @sub_app.get("/users")
    def route_get_users(
        session: Session = Depends(sync_db.session_generator),
        users2=Depends(get_users),
    ):
        assert session is not None  # ound to the request.scope session
        assert session is sync_db.session  # The session in the current context
        assert session is not global_sync_session  # Request scope session is different from global session
        with sync_db() as session2:  # Create a new session
            assert session2 is not None
            assert session2 is sync_db.session
            assert session2 is not session
            assert session2 is not global_sync_session
        assert len(users2) == 5
        users = get_users()
        assert len(users) == 5
        # test update
        users[0].username = "new_user"
        return users

    # test read
    response = client.get("/users")
    assert response.status_code == 200
    assert len(response.json()) == 5
    # test update
    user = sync_db.session.get(User, 1)
    assert user.username == "new_user"
    # test sub app
    response = client.get("/sub/users")
    assert response.status_code == 200
    assert len(response.json()) == 5


global_async_session = async_db.session


async def get_users_async() -> List[User]:
    assert async_db.session is not global_async_session
    users = await async_db.session.scalars(select(User))
    """1. If the session is used in a non-dependency function, the session is global.
    2. If the session is used in a dependency function, the session is bound to the fastapi request.
    3. You can also create a new session for a function separately.
    """
    return users.all()


async def test_async_db_in_fastapi():
    app = FastAPI()
    sub_app = FastAPI()
    app.mount("/sub", sub_app)
    app.add_middleware(BaseHTTPMiddleware, dispatch=async_db.asgi_dispatch)
    client = TestClient(app)

    @app.get("/users")
    @sub_app.get("/users")
    async def route_get_users(
        session: AsyncSession = Depends(async_db.session_generator),
        users2=Depends(get_users_async),
        user3=Depends(sync_db.asyncify(async_db, get_users)),
    ):
        assert len(users2) == 5
        assert len(user3) == 5

        assert session is not None  # bound to the request.scope session
        assert session is async_db.session  # The session in the current context
        assert session is not global_async_session  # Request scope session is different from global session
        async with async_db() as session2:  # Create a new session
            assert session2 is not None
            assert session2 is async_db.session
            assert session2 is not session
            assert session2 is not global_async_session

        # Note that you are using an async session object to run a sync session context function.
        users = await sync_db.asyncify(async_db, get_users)()
        assert len(users) == 5
        # test update
        users[0].username = "new_user"
        return users

    # test read
    response = client.get("/users")
    assert response.status_code == 200
    assert len(response.json()) == 5
    # test update
    user = await async_db.session.get(User, 1)
    assert user.username == "new_user"
    # test sub app
    response = client.get("/sub/users")
    assert response.status_code == 200
    assert len(response.json()) == 5
