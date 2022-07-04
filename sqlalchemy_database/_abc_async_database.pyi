import abc
from typing import Any, Optional, Mapping, Union, Sequence, Type, List, TypeVar, Callable

from sqlalchemy.engine import Result, Connection
from sqlalchemy.orm import Session
from sqlalchemy.sql import Executable
from typing_extensions import ParamSpec, Concatenate

_P = ParamSpec("_P")
_T = TypeVar("_T")
_R = TypeVar("_R")

_ExecuteParams = Union[Mapping[Any, Any], Sequence[Mapping[Any, Any]]]
_ExecuteOptions = Mapping[Any, Any]


class AbcAsyncDatabase(metaclass=abc.ABCMeta):
    """`sqlalchemy` asynchronous database abstract base class, not directly instantiated

    """

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
            **kw: Any,
    ) -> Union[Result, _T]: ...

    async def async_scalar(
            self,
            statement: Executable,
            params: Optional[_ExecuteParams] = None,
            *,
            execution_options: Optional[_ExecuteOptions] = None,
            bind_arguments: Optional[Mapping[str, Any]] = None,
            **kw: Any,
    ) -> Any: ...

    async def async_scalars_all(
            self,
            statement: Executable,
            params: Optional[_ExecuteParams] = None,
            *,
            execution_options: Optional[_ExecuteOptions] = None,
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
    ) -> Optional[_T]: ...

    async def async_delete(self, instance: Any) -> None: ...

    async def async_save(self, *instances: Any, refresh: bool = False) -> None: ...

    async def async_run_sync(
            self,
            fn: Callable[[Concatenate[Union[Session, Connection], _P]], _T],
            *args: _P.args,
            commit: bool = True,
            on_close_pre: Callable[[_T], _R] = None,
            is_session: bool = True,
            **kwargs: _P.kwargs
    ) -> Union[_T, _R]: ...
