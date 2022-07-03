[简体中文](https://github.com/amisadmin/sqlalchemy_database/blob/master/README.zh.md)
| [English](https://github.com/amisadmin/sqlalchemy_database)

<h2 align="center">
  SQLAlchemy-Database
</h2>
<p align="center">
    <em>SQLAlchemy-Database为SQLAlchemy ORM提供常见数据库操作的快捷方式.</em><br/>
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

## 项目介绍

- 支持`SQLAlchemy`和`SQLModel`,推荐使用`SQLModel`.

## 安装

```bash
pip install sqlalchemy-database
```

## ORM模型

### SQLAlchemy模型示例

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

### SQLModel模型示例

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

### 创建连接

```python
from sqlalchemy_database import AsyncDatabase

# 1.创建数据库客户端
db = AsyncDatabase.create('sqlite+aiosqlite:///amisadmin.db?check_same_thread=False')  # sqlite
# db = AsyncDatabase.create('mysql+aiomysql://root:123456@127.0.0.1:3306/amisadmin?charset=utf8mb4')# mysql
# db = AsyncDatabase.create('postgresql+asyncpg://postgres:root@127.0.0.1:5432/amisadmin')# postgresql

```

### 快捷函数

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

### 创建连接

```python
from sqlalchemy_database import Database

# 1.创建数据库客户端
db = Database.create('sqlite:///amisadmin.db?check_same_thread=False')  # sqlite
# db = Database.create('mysql+pymysql://root:123456@127.0.0.1:3306/amisadmin?charset=utf8mb4') # mysql
# db = Database.create('postgresql://postgres:root@127.0.0.1:5432/amisadmin') # postgresql
# db = Database.create('oracle+cx_oracle://scott:tiger@tnsname') # oracle
# db = Database.create('mssql+pyodbc://scott:tiger@mydsn') # SQL Server
```

### 快捷函数

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

当你在开发一个工具库的时候,你的python程序可能会需要对方提供一个数据库连接.

但是你不能确定对方个人倾向是使用同步连接,还是异步连接.你可以使用`async_`前缀的异步快捷函数.

`AsyncDatabase`和`Database`都继承自`AbcAsyncDatabase`,并且都实现了常用的以`async_`为前缀的异步快捷函数.

例如: `async_execute`,`async_scalar`,`async_scalars_all`,`async_get`,`async_delete`,`async_run_sync`.

说明: `Database`中`async_`前缀异步快捷函数,是通过在线程池中执行对应的同步快捷函数实现的.

### 异步兼容快捷函数

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

## FastAPI中使用依赖

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

## 更多教程文档

### [sqlalchemy](https://github.com/sqlalchemy/sqlalchemy)

`SQLAlchemy-Database`在`SQLAlchemy`的基础上添加拓展功能. 更多功能及复杂使用,请参考`SQLAlchemy`[官方文档](https://www.sqlalchemy.org/).

`SQLAlchemy`非常强大,几乎可以满足你的任何复杂需求.

### [sqlmodel](https://github.com/tiangolo/sqlmodel)

推荐使用`SQLModel`定义ORM模型,请参考`SQLModel`[官方文档](https://sqlmodel.tiangolo.com/).

`SQLModel`由FastAPI作者编写, 完美结合`SQLAlchemy`+`Pydantic`, 拥有`SQLAlchemy`和`Pydantic`的所有功能.

## 相关项目

- [FastAPI-Amis-Admin](https://docs.amis.work/)

## 许可协议

该项目遵循 Apache2.0 许可协议。
