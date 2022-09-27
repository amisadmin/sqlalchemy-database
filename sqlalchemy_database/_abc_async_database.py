import abc
import asyncio
import functools
from typing import Callable, TypeVar

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
    def __init__(self) -> None:
        for func_name in ["execute", "scalar", "scalars_all", "get", "delete", "save", "run_sync"]:
            func = getattr(self, func_name)
            if not asyncio.iscoroutinefunction(func):
                func = functools.partial(to_thread, func)
            setattr(self, f"async_{func_name}", func)

    async def asgi_dispatch(self, request, call_next):
        """Middleware for ASGI applications, such as: Starlette, FastAPI, Quart, Sanic, Hug, Responder, etc.
        Bind a SQLAlchemy session connection to the incoming HTTP request session context,
        you can access the session object through `self.session`.
        The instance shortcut method will also try to use this `session` object by default.
        Example:
            ```Python
            app = FastAPI()
            db = Database.create("sqlite:///test.db")
            app.add_middleware(BaseHTTPMiddleware, dispatch=db.asgi_dispatch)
            ```
        """
        async with self:
            response = await call_next(request)
        return response
