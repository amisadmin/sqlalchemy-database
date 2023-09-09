import abc
import asyncio
import functools
import warnings
from typing import Callable, Dict, TypeVar, Union

from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.future import Engine
from sqlalchemy.orm import scoped_session

try:
    from asyncio import to_thread  # python 3.9+
except ImportError:
    import contextvars

    from typing_extensions import ParamSpec

    _P = ParamSpec("_P")
    _R = TypeVar("_R")

    async def to_thread(func: Callable[_P, _R], *args: _P.args, **kwargs: _P.kwargs) -> _R:  # noqa: E303
        loop = asyncio.get_running_loop()
        ctx = contextvars.copy_context()
        func_call = functools.partial(ctx.run, func, *args, **kwargs)
        return await loop.run_in_executor(None, func_call)


class AbcAsyncDatabase(metaclass=abc.ABCMeta):  # noqa: B024

    _instances: Dict[str, "AbcAsyncDatabase"] = None

    def __new__(cls, engine: Union[Engine, AsyncEngine], *args, **kwargs):
        """Create a new instance of the database class.Each engine url corresponds to a database instance,
        and if it already exists, it is directly returned, otherwise a new instance is created.
        """
        cls._instances = cls._instances or {}
        if engine.url not in cls._instances:
            cls._instances[engine.url] = super().__new__(cls)
        return cls._instances[engine.url]

    def __init__(self, engine: Union[Engine, AsyncEngine], *args, **kwargs) -> None:
        for func_name in {
            "run_sync",
            "begin",
            "begin_nested",
            "close",
            "commit",
            "connection",
            "delete",
            "execute",
            "flush",
            "get",
            "merge",
            "refresh",
            "rollback",
            "scalar",
            "scalars",
            "add",
            "add_all",
            "expire",
            "expire_all",
            "expunge",
            "expunge_all",
            "get_bind",
            "is_modified",
        }:
            func = getattr(self, func_name, None)
            if not func:
                func = getattr(self.scoped_session, func_name)  # type: ignore
                setattr(self, func_name, func)
                """Create a proxy method for the scoped_session method.Note that this method is not recommended,
                because it will cause the type of db.session to be unclear, which is not conducive to the code prompt of IDE."""
            if func_name in {
                "add",
                "add_all",
                "expire",
                "expire_all",
                "expunge",
                "expunge_all",
                "get_bind",
                "is_modified",
            }:  # These methods do not need to be asynchronous.
                continue
            if not asyncio.iscoroutinefunction(func) and isinstance(self.scoped_session, scoped_session):  # type: ignore
                func = functools.partial(to_thread, func)
            setattr(self, f"async_{func_name}", func)

    async def asgi_dispatch(self, request, call_next):
        """
        This method has been deprecated and is not recommended. Please use the `asgi_middleware` method instead.
        Reference: https://www.starlette.io/middleware/#limitations
        """
        # 打印警告信息
        warnings.warn(
            "This method has been deprecated and is not recommended. Please use the `asgi_middleware` method instead.",
            DeprecationWarning,
        )
        if request.scope.get(f"__sqlalchemy_database__:{id(self)}", False):
            return await call_next(request)
        # bind session to request
        async with self.__call__(scope=id(request.scope)):
            request.scope[f"__sqlalchemy_database__:{id(self)}"] = self
            return await call_next(request)

    def attach_middleware(self, app):
        """Attach the middleware to the ASGI application.
        Example:
            ```Python
            app = FastAPI()
            db = Database.create("sqlite:///test.db")
            db.attach_middlewares(app)
            ```
        """
        app.add_middleware(self.asgi_middleware)

    @property
    def asgi_middleware(self):
        """Middleware for ASGI applications, such as: Starlette, FastAPI, Quart, Sanic, Hug, Responder, etc.
        Bind a SQLAlchemy session connection to the incoming HTTP request session context,
        you can access the session object through `self.session`.
        The instance shortcut method will also try to use this `session` object by default.
        Example:
            ```Python
            app = FastAPI()
            db = Database.create("sqlite:///test.db")
            app.add_middleware(db.asgi_middleware)
            ```
        """

        def asgi_decorator(app):
            @functools.wraps(app)
            async def wrapped_app(scope, receive, send):
                if scope.get(f"__sqlalchemy_database__:{id(self)}", False):
                    return await app(scope, receive, send)
                    # bind session to request
                async with self.__call__(scope=id(scope)):
                    scope[f"__sqlalchemy_database__:{id(self)}"] = self
                    await app(scope, receive, send)

            return wrapped_app

        return asgi_decorator
