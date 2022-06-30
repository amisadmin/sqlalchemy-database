import datetime

import sqlalchemy as sa
from sqlalchemy.orm import declarative_base

from sqlalchemy_database import Database, AsyncDatabase

# sqlite
sync_db = Database.create('sqlite:///amisadmin.db?check_same_thread=False')
async_db = AsyncDatabase.create('sqlite+aiosqlite:///amisadmin.db?check_same_thread=False')

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
    password = sa.Column(sa.String(30), default='')
    create_time = sa.Column(sa.DateTime, default=datetime.datetime.utcnow)
