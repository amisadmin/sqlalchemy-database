from sqlalchemy_database.utils import get_engine_url
from tests.conftest import async_db, sync_db


def test_get_engine_url():
    assert get_engine_url(sync_db.engine.url, sync=True) == sync_db.engine.url
    assert get_engine_url(sync_db.engine.url, sync=False) == async_db.engine.url
    assert get_engine_url(async_db.engine.url, sync=True) == sync_db.engine.url.set(drivername="sqlite+pysqlite")
    assert get_engine_url(async_db.engine.url, sync=False) == async_db.engine.url
