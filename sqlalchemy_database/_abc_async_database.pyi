import abc
from typing import (
    Any,
    Callable,
    List,
    Mapping,
    Optional,
    Sequence,
    Type,
    TypeVar,
    Union,
)

from sqlalchemy.engine import Connection, Result
from sqlalchemy.ext.asyncio import AsyncConnection
from sqlalchemy.sql import Executable
from typing_extensions import Concatenate, ParamSpec

try:
    from sqlmodel import Session
    from sqlmodel.ext.asyncio.session import AsyncSession
except ImportError:
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import Session

_P = ParamSpec("_P")
_T = TypeVar("_T")
_R = TypeVar("_R")

_ExecuteParams = Union[Mapping[Any, Any], Sequence[Mapping[Any, Any]]]
_ExecuteOptions = Mapping[Any, Any]

class AbcAsyncDatabase(metaclass=abc.ABCMeta):
    """`sqlalchemy` asynchronous database abstract base class, not directly instantiated"""

    async def async_execute(
        self,
        statement: Executable,
        params: Optional[_ExecuteParams] = None,
        *,
        execution_options: Optional[_ExecuteOptions] = None,
        bind_arguments: Optional[Mapping[str, Any]] = None,
        commit: bool = True,
        on_close_pre: Callable[[Result], _T] = None,
        is_session: bool = True,
        executor: Union[Session, Connection, AsyncSession, AsyncConnection, None] = None,
        **kw: Any,
    ) -> Union[Result, _T]: ...
    async def async_scalar(
        self,
        statement: Executable,
        params: Optional[_ExecuteParams] = None,
        *,
        execution_options: Optional[_ExecuteOptions] = None,
        bind_arguments: Optional[Mapping[str, Any]] = None,
        session: Union[Session, AsyncSession, None] = None,
        **kw: Any,
    ) -> Any: ...
    async def async_scalars_all(
        self,
        statement: Executable,
        params: Optional[_ExecuteParams] = None,
        *,
        execution_options: Optional[_ExecuteOptions] = None,
        session: Union[Session, AsyncSession, None] = None,
        **kw: Any,
    ) -> List[Any]: ...
    async def async_get(
        self,
        entity: Type[_T],
        ident: Any,
        *,
        options: Optional[Sequence[Any]] = None,
        populate_existing: bool = False,
        with_for_update: Optional[Any] = None,
        identity_token: Optional[Any] = None,
        execution_options: Optional[_ExecuteOptions] = None,
        session: Union[Session, AsyncSession, None] = None,
    ) -> Optional[_T]: ...
    async def async_delete(self, instance: Any) -> None: ...
    async def async_save(
        self, *instances: Any, refresh: bool = False, session: Union[Session, AsyncSession, None] = None
    ) -> None: ...
    async def async_run_sync(
        self,
        fn: Callable[[Concatenate[Union[Session, Connection], _P]], _T],
        *args: _P.args,
        commit: bool = True,
        on_close_pre: Callable[[_T], _R] = None,
        is_session: bool = True,
        executor: Union[Session, Connection, AsyncSession, AsyncConnection, None] = None,
        **kwargs: _P.kwargs,
    ) -> Union[_T, _R]: ...
    async def asgi_dispatch(self, request, call_next): ...
