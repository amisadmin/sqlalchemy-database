import abc
import asyncio
import functools
from typing import TypeVar, Callable

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


class AbcAsyncDatabase(metaclass=abc.ABCMeta):

    def __init__(self) -> None:
        for func_name in ['execute', 'scalar', 'scalars_all', 'get', 'delete', 'save', 'run_sync']:
            func = getattr(self, func_name)
            if not asyncio.iscoroutinefunction(func):
                func = functools.partial(to_thread, func)
            setattr(self, f'async_{func_name}', func)
