from typing import Union

from sqlalchemy.engine import URL, make_url

SQLALCHEMY_DRIVER = {
    "sqlite": {"sync": ["pysqlite", "pysqlcipher"], "async": ["aiosqlite"]},
    "mysql": {"sync": ["pymysql", "mysqldb", "mysqlconnector", "cymysql", "pyodbc"], "async": ["aiomysql", "asyncmy"]},
    "mariadb": {"sync": ["pymysql", "mysqldb", "mysqlconnector", "cymysql", "pyodbc"], "async": ["aiomysql", "asyncmy"]},
    "postgresql": {"sync": ["pg8000", "pyscopg2", "psycopg", "psycopg2cffi"], "async": ["asyncpg"]},
    "oracle": {"sync": ["cx_oracle", "oracledb"], "async": []},
    "mssql": {"sync": ["pyodbc", "pymssql"], "async": []},
}


def get_engine_url(url: Union[str, URL], sync: bool = True) -> URL:
    url: URL = make_url(url)
    backend_name = url.get_backend_name()
    driver_name = url.get_driver_name()
    driver_type = "sync" if sync else "async"
    if driver_name in SQLALCHEMY_DRIVER.get(backend_name, {}).get(driver_type, []):
        return url
    new_driver = SQLALCHEMY_DRIVER[backend_name][driver_type][0]
    url = url.set(drivername=f"{backend_name}+{new_driver}")
    return url
