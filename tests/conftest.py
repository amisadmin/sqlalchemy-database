import datetime
from typing import AsyncGenerator, List, Union

import pytest
import sqlalchemy as sa
from sqlalchemy import insert
from sqlalchemy.orm import declarative_base

from sqlalchemy_database import AsyncDatabase, Database

# sqlite
sync_db = Database.create("sqlite:///amisadmin.db?check_same_thread=False")
async_db = AsyncDatabase.create("sqlite+aiosqlite:///amisadmin.db?check_same_thread=False")

# mysql
# sync_db = Database.create('mysql+pymysql://root:123456@127.0.0.1:3306/amisadmin?charset=utf8mb4')
# async_db = AsyncDatabase.create('mysql+aiomysql://root:123456@127.0.0.1:3306/amisadmin?charset=utf8mb4')

# postgresql
# sync_db = Database.create('postgresql://postgres:root@127.0.0.1:5432/amisadmin')
# async_db = AsyncDatabase.create('postgresql+asyncpg://postgres:root@127.0.0.1:5432/amisadmin')

# oracle
# sync_db = Database.create('oracle+cx_oracle://scott:tiger@tnsname')

# SQL Server
# sync_db = Database.create('mssql+pyodbc://scott:tiger@mydsn')


Base = declarative_base()


class User(Base):
    __tablename__ = "User"
    id = sa.Column(sa.Integer, primary_key=True)
    username = sa.Column(sa.String(30), unique=True, index=True, nullable=False)
    password = sa.Column(sa.String(30), default="")
    create_time = sa.Column(sa.DateTime, default=datetime.datetime.utcnow)
    group_id = sa.Column(sa.Integer, sa.ForeignKey("Group.id"))
    group = sa.orm.relationship("Group", back_populates="users")


class Group(Base):
    __tablename__ = "Group"
    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String(30), unique=True, index=True, nullable=False)
    create_time = sa.Column(sa.DateTime, default=datetime.datetime.utcnow)
    users = sa.orm.relationship("User", back_populates="group", lazy="dynamic")


@pytest.fixture
async def prepare_database() -> AsyncGenerator[None, None]:
    await async_db.async_run_sync(Base.metadata.create_all, is_session=False)
    yield
    await async_db.async_run_sync(Base.metadata.drop_all, is_session=False)
    await async_db.async_close()


@pytest.fixture
async def fake_users(prepare_database) -> List[dict]:
    data = [
        {
            "id": i,
            "username": f"User-{i}",
            "password": f"password_{i}",
            "create_time": datetime.datetime.strptime(f"2022-01-0{i} 00:00:00", "%Y-%m-%d %H:%M:%S"),
        }
        for i in range(1, 6)
    ]
    await async_db.session.execute(insert(User).values(data))
    await async_db.session.commit()
    return data


@pytest.fixture(params=[async_db, sync_db])
async def db(request, fake_users) -> Union[Database, AsyncDatabase]:
    database = request.param
    yield database
    await database.async_close()


@pytest.fixture(autouse=True)
def _setup_sync_db(fake_users) -> Database:
    yield sync_db
    # Free connection pool resources
    sync_db.close()  # type: ignore


@pytest.fixture(autouse=True)
async def _setup_async_db(fake_users) -> AsyncDatabase:
    yield async_db
    await async_db.async_close()  # Free connection pool resources
