# Introduction

[简体中文](https://github.com/amisadmin/sqlalchemy_database/blob/master/README.zh.md)
| [English](https://github.com/amisadmin/sqlalchemy_database)

<h2 align="center">
  SQLAlchemy-Database
</h2>
<p align="center">
    <em>SQLAlchemy-Database provides shortcut functions to common database operations for SQLAlchemy ORM.</em><br/>
</p>
<p align="center">
    <a href="https://github.com/amisadmin/sqlalchemy_database/actions/workflows/pytest.yml" target="_blank">
        <img src="https://github.com/amisadmin/sqlalchemy_database/actions/workflows/pytest.yml/badge.svg" alt="Pytest">
    </a>
    <a href="https://codecov.io/gh/amisadmin/sqlalchemy_database" > 
     <img src="https://codecov.io/gh/amisadmin/sqlalchemy_database/branch/master/graph/badge.svg?token=SKOGAKIX4M" alt="codecov"/> 
    </a>
    <a href="https://pypi.org/project/sqlalchemy_database" target="_blank">
        <img src="https://badgen.net/pypi/v/sqlalchemy_database?color=blue" alt="Package version">
    </a>
    <a href="https://gitter.im/amisadmin/fastapi-amis-admin">
        <img src="https://badges.gitter.im/amisadmin/fastapi-amis-admin.svg" alt="Chat on Gitter"/>
    </a>
    <a href="https://jq.qq.com/?_wv=1027&k=U4Dv6x8W" target="_blank">
        <img src="https://badgen.net/badge/qq%E7%BE%A4/229036692/orange" alt="229036692">
    </a>
</p>

## Introduction

- Support `SQLAlchemy` and `SQLModel`,recommend using `SQLModel`.

## Install

```bash
pip install sqlalchemy-database
```

## ORM Model

### SQLAlchemy Model Sample

```python
import datetime

import sqlalchemy as sa
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "User"
    id = sa.Column(sa.Integer, primary_key=True)
    username = sa.Column(sa.String(30), unique=True, index=True, nullable=False)
    password = sa.Column(sa.String(30), default='')
    create_time = sa.Column(sa.DateTime, default=datetime.datetime.utcnow)
```

### SQLModel Model Sample

```python
import datetime

from sqlmodel import SQLModel, Field


class User(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True, nullable=False)
    username: str = Field(title='username', sa_column=Column(String(100), unique=True, index=True, nullable=False))
    password: str = Field(default='', title='Password')
    create_time: datetime = Field(default_factory=datetime.utcnow, title='Create Time')
```

## AsyncDatabase

### Creation Connection

```python
from sqlalchemy_database import AsyncDatabase

# 1.Create an asynchronous database connection
db = AsyncDatabase.create('sqlite+aiosqlite:///amisadmin.db?check_same_thread=False')  # sqlite
# db = AsyncDatabase.create('mysql+aiomysql://root:123456@127.0.0.1:3306/amisadmin?charset=utf8mb4')# mysql
# db = AsyncDatabase.create('postgresql+asyncpg://postgres:root@127.0.0.1:5432/amisadmin')# postgresql

```

### Shortcut functions

```python
from sqlalchemy import insert, select, update, delete


async def fast_execute():
    # update
    stmt = update(User).where(User.id == 1).values({'username': 'new_user'})
    result = await db.execute(stmt)

    # select
    stmt = select(User).where(User.id == 1)
    user = await db.execute(stmt, on_close_pre=lambda r: r.scalar())

    # insert
    stmt = insert(User).values({'username': 'User-6', 'password': 'password-6'})
    result = await db.execute(stmt)

    # delete
    stmt = delete(User).where(User.id == 6)
    result = await db.execute(stmt)

    # scalar
    user = await db.scalar(select(User).where(User.id == 1))

    # scalars_all
    stmt = select(User)
    result = await db.scalars_all(stmt)

    # get
    user = await db.get(User, 1)

    # delete
    user = User(id=1, name='test')
    await db.delete(user)
    
    # save(insert or update)
    user = User(name='new_user')
    await db.save(user)
    
    # run_sync
    await db.run_sync(Base.metadata.create_all, is_session=False)

    # session_maker
    async with db.session_maker() as session:
        user = await session.get(User, 1)
```

## Database

### Creation Connection

```python
from sqlalchemy_database import Database

# 1.Create a database connection
db = Database.create('sqlite:///amisadmin.db?check_same_thread=False')  # sqlite
# db = Database.create('mysql+pymysql://root:123456@127.0.0.1:3306/amisadmin?charset=utf8mb4') # mysql
# db = Database.create('postgresql://postgres:root@127.0.0.1:5432/amisadmin') # postgresql
# db = Database.create('oracle+cx_oracle://scott:tiger@tnsname') # oracle
# db = Database.create('mssql+pyodbc://scott:tiger@mydsn') # SQL Server
```

### Shortcut functions

```python
from sqlalchemy import insert, select, update, delete


def fast_execute():
    # update
    stmt = update(User).where(User.id == 1).values({'username': 'new_user'})
    result = db.execute(stmt)

    # select
    stmt = select(User).where(User.id == 1)
    user = db.execute(stmt, on_close_pre=lambda r: r.scalar())

    # insert
    stmt = insert(User).values({'username': 'User-6', 'password': 'password-6'})
    result = db.execute(stmt)

    # delete
    stmt = delete(User).where(User.id == 6)
    result = db.execute(stmt)

    # scalar
    user = db.scalar(select(User).where(User.id == 1))

    # scalars_all
    stmt = select(User)
    result = db.scalars_all(stmt)

    # get
    user = db.get(User, 1)

    # delete
    user = User(id=1, name='test')
    db.delete(user)
    
    # save(insert or update)
    user = User(name='new_user')
    db.save(user)
    
    # run_sync
    db.run_sync(Base.metadata.create_all, is_session=False)

    # session_maker
    with db.session_maker() as session:
        user = session.get(User, 1)
```

## AbcAsyncDatabase

When you are developing a library of tools, your Python program may require a database connection.

But you can't be sure whether the other person personally prefers synchronous or asynchronous connections.

You can use asynchronous shortcut functions with the `async_` prefix.

`AsyncDatabase` and `Database` both inherit from `AbcAsyncDatabase` and both implement the usual `async_` prefixed asynchronous
shortcut functions.

For example: `async_execute`,`async_scalar`,`async_scalars_all`,`async_get`,`async_delete`,`async_run_sync`.

Remark: The `async_` prefix in `Database` is implemented by executing the corresponding synchronous shortcut in the thread pool.

### Asynchronous compatible shortcut functions

```python
from sqlalchemy import insert, select, update, delete
from sqlalchemy_database import AsyncDatabase, Database


async def fast_execute(db: Union[AsyncDatabase, Database]):
    # update
    stmt = update(User).where(User.id == 1).values({'username': 'new_user'})
    result = await db.async_execute(stmt)

    # select
    stmt = select(User).where(User.id == 1)
    user = await db.async_execute(stmt, on_close_pre=lambda r: r.scalar())

    # insert
    stmt = insert(User).values({'username': 'User-6', 'password': 'password-6'})
    result = await db.async_execute(stmt)

    # delete
    stmt = delete(User).where(User.id == 6)
    result = await db.async_execute(stmt)

    # scalar
    user = await db.async_scalar(select(User).where(User.id == 1))

    # scalars_all
    stmt = select(User)
    result = await db.async_scalars_all(stmt)

    # get
    user = await db.async_get(User, 1)

    # delete
    user = User(id=1, name='test')
    await db.async_delete(user)
    
    # save(insert or update)
    user = User(name='new_user')
    await db.async_save(user)
    
    # run_sync
    await db.async_run_sync(Base.metadata.create_all, is_session=False)

```

## Use dependencies in FastAPI

```python
app = FastAPI()


# AsyncDatabase
@app.get("/user/{id}")
async def get_user(id: int, session: AsyncSession = Depends(db.session_generator)):
    return await session.get(User, id)


# Database
@app.get("/user/{id}")
def get_user(id: int, session: Session = Depends(db.session_generator)):
    return session.get(User, id)
```

## More tutorial documentation

### [sqlalchemy](https://github.com/sqlalchemy/sqlalchemy)

`SQLAlchemy-Database` adds extension functionality to `SQLAlchemy`.

More features and complicated to use, please refer to the ` SQLAlchemy ` [documentation](https://www.sqlalchemy.org/).

`SQLAlchemy` is very powerful and can fulfill almost any complex need you have.

### [sqlmodel](https://github.com/tiangolo/sqlmodel)

Recommend you to use ` SQLModel ` definition `ORM` model, please refer to
the ` SQLModel ` [documentation](https://sqlmodel.tiangolo.com/).

`SQLModel`  written by `FastAPI` author, Perfectly combine [SQLAlchemy](https://www.sqlalchemy.org/)
with [Pydantic](https://pydantic-docs.helpmanual.io/), and have all their features .

## Relevant project

- [FastAPI-Amis-Admin](https://docs.amis.work/)

## License

According to the `Apache2.0` protocol.
