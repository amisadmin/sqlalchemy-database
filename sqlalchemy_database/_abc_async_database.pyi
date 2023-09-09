import abc
from typing import (
    Any,
    Callable,
    Iterable,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from sqlalchemy.engine import Connection, Engine, Result
from sqlalchemy.sql import ClauseElement, Executable
from sqlmodel.engine.result import ScalarResult
from typing_extensions import Concatenate, ParamSpec

from sqlalchemy_database.database import AsyncSessionContextVarManager

try:
    from sqlmodel import Session
    from sqlmodel.ext.asyncio.session import AsyncSession
except ImportError:
    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
    from sqlalchemy.orm import Session

_P = ParamSpec("_P")
_T = TypeVar("_T")
_R = TypeVar("_R")

async def to_thread(func: Callable[_P, _R], *args: _P.args, **kwargs: _P.kwargs) -> _R: ...

_ExecuteParams = Union[Mapping[Any, Any], Sequence[Mapping[Any, Any]]]
_ExecuteOptions = Mapping[Any, Any]

class AbcAsyncDatabase(metaclass=abc.ABCMeta):
    """`sqlalchemy` asynchronous database abstract base class, not directly instantiated"""

    engine: Union[Engine, AsyncEngine]

    async def async_run_sync(
        self,
        fn: Callable[[Concatenate[Union[Session, Connection], _P]], _T],
        *args: _P.args,
        is_session: bool = True,
        **kwargs: _P.kwargs,
    ) -> _T: ...
    def asgi_middleware(self, app: Any) -> Callable[[Any], Tuple[Mapping[str, Any], Any, Any]]: ...
    def attach_middleware(self, app: Any) -> None: ...
    def __call__(self, scope: Any = None) -> AsyncSessionContextVarManager:
        pass
    async def async_close(self) -> None: ...
    async def async_commit(self) -> None: ...
    async def async_delete(self, instance: Any) -> None: ...
    async def async_execute(
        self,
        statement: Executable,
        params: Optional[_ExecuteParams] = ...,
        execution_options: Optional[_ExecuteOptions] = ...,
        bind_arguments: Optional[Mapping[str, Any]] = ...,
        **kw: Any,
    ) -> Result: ...
    async def async_flush(self, objects: Optional[Any] = ...) -> None: ...
    async def async_get(
        self,
        entity: Type[_T],
        ident: Any,
        options: Optional[Sequence[Any]] = ...,
        populate_existing: bool = ...,
        with_for_update: Optional[Any] = ...,
        identity_token: Optional[Any] = ...,
        execution_options: Optional[_ExecuteOptions] = ...,
    ) -> Optional[_T]: ...
    async def async_merge(
        self,
        instance: _T,
        load: bool = ...,
        options: Optional[Sequence[Any]] = ...,
    ) -> _T: ...
    async def async_refresh(
        self,
        instance: Any,
        attribute_names: Optional[Any] = ...,
        with_for_update: Optional[Any] = ...,
    ) -> None: ...
    async def async_rollback(self) -> None: ...
    async def async_scalar(
        self,
        statement: Executable,
        params: Optional[_ExecuteParams] = ...,
        execution_options: Optional[_ExecuteOptions] = ...,
        bind_arguments: Optional[Mapping[str, Any]] = ...,
        **kw: Any,
    ) -> Any: ...
    async def async_scalars(
        self,
        statement: Executable,
        parameters: Optional[_ExecuteParams] = ...,
        execution_options: Optional[_ExecuteOptions] = ...,
    ) -> ScalarResult: ...
    def add(self, instance: Any, _warn: bool = ...) -> None: ...
    def add_all(self, instances: Any) -> None: ...
    def expire(self, instance: Any, attribute_names: Optional[Iterable[str]] = ...) -> None: ...
    def expire_all(self) -> None: ...
    def expunge(self, instance: Any) -> None: ...
    def expunge_all(self) -> None: ...
    def get_bind(
        self,
        mapper: Optional[Any] = ...,
        clause: Optional[ClauseElement] = ...,
        bind: Optional[_T] = ...,
        _sa_skip_events: Optional[Any] = ...,
        _sa_skip_for_implicit_returning: bool = ...,
    ) -> _T: ...
    def is_modified(self, instance: Any, include_collections: bool = ...) -> bool: ...
