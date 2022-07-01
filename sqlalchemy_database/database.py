from typing import Generator, Any, AsyncGenerator, Optional, Mapping, Union, Sequence, Type, List, Callable, TypeVar

from sqlalchemy.engine import Result, Connection
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine, create_async_engine
from sqlalchemy.future import Engine, create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import Executable, Select
from sqlalchemy_database._abc_async_database import AbcAsyncDatabase
from typing_extensions import Concatenate, ParamSpec

_P = ParamSpec("_P")
_T = TypeVar("_T")
_R = TypeVar("_R")

_ExecuteParams = Union[Mapping[Any, Any], Sequence[Mapping[Any, Any]]]
_ExecuteOptions = Mapping[Any, Any]


class AsyncDatabase(AbcAsyncDatabase):

    def __init__(self, engine: AsyncEngine, **session_options):
        super().__init__()
        self.engine: AsyncEngine = engine
        session_options.setdefault('class_', AsyncSession)
        self.session_maker: Callable[..., AsyncSession] = sessionmaker(self.engine, **session_options)

    @classmethod
    def create(cls, url, *, session_options: Optional[Mapping[str, Any]] = None, **kwargs):
        kwargs.setdefault('future', True)
        engine = create_async_engine(url, **kwargs)
        session_options = session_options or {}
        return cls(engine, **session_options)

    async def session_generator(self) -> AsyncGenerator[AsyncSession, Any]:
        async with self.session_maker() as session:
            yield session

    async def execute(
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
    ) -> Union[Result, _T]:
        if is_session:
            maker = self.session_maker
            kw['bind_arguments'] = bind_arguments
        else:
            maker = self.engine.connect
        async with maker() as conn:

            result = await conn.execute(statement, params, execution_options, **kw)
            if on_close_pre:
                result = on_close_pre(result)
            if commit and not isinstance(statement, Select):
                await conn.commit()
        return result

    async def scalar(
            self,
            statement: Executable,
            params: Optional[_ExecuteParams] = None,
            *,
            execution_options: Optional[_ExecuteOptions] = None,
            bind_arguments: Optional[Mapping[str, Any]] = None,
            **kw: Any,
    ) -> Any:
        async with self.session_maker() as session:
            return await session.scalar(
                statement,
                params,
                execution_options=execution_options,
                bind_arguments=bind_arguments,
                **kw,
            )

    async def scalars_all(
            self,
            statement: Executable,
            params: Optional[_ExecuteParams] = None,
            *,
            execution_options: Optional[_ExecuteOptions] = None,
            **kw: Any,
    ) -> List[Any]:
        async with self.session_maker() as session:
            result = await session.scalars(
                statement,
                params,
                execution_options=execution_options,
                **kw,
            )
            return result.all()

    async def get(
            self,
            entity: Type[_T],
            ident: Any,
            *,
            options: Optional[Sequence[Any]] = None,
            populate_existing: bool = False,
            with_for_update: Optional[Any] = None,
            identity_token: Optional[Any] = None,
            execution_options: Optional[_ExecuteOptions] = None,
    ) -> Optional[_T]:
        async with self.session_maker() as session:
            return await session.get(
                entity,
                ident,
                options=options,
                populate_existing=populate_existing,
                with_for_update=with_for_update,
                identity_token=identity_token,
            )

    async def delete(self, instance: Any) -> None:
        async with self.session_maker() as session:
            async with session.begin():
                await session.delete(instance)

    async def run_sync(
            self,
            fn: Callable[[Concatenate[Union[Session, Connection], _P]], _T],
            *args: _P.args,
            commit: bool = True,
            on_close_pre: Callable[[_T], _R] = None,
            is_session: bool = True,
            **kwargs: _P.kwargs
    ) -> Union[_T, _R]:
        maker = self.session_maker if is_session else self.engine.connect
        async with maker() as conn:
            result = await conn.run_sync(fn, *args, **kwargs)
            if on_close_pre:
                result = on_close_pre(result)
            if commit:
                await conn.commit()
        return result


class Database(AbcAsyncDatabase):

    def __init__(self, engine: Engine, **session_options):
        super().__init__()
        self.engine: Engine = engine
        self.session_maker: Callable[..., Session] = sessionmaker(self.engine, **session_options)

    @classmethod
    def create(cls, url, *, session_options: Optional[Mapping[str, Any]] = None, **kwargs):
        kwargs.setdefault('future', True)
        engine = create_engine(url, **kwargs)
        session_options = session_options or {}
        return cls(engine, **session_options)

    def session_generator(self) -> Generator[Session, Any, None]:
        with self.session_maker() as session:
            yield session

    def execute(
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
    ) -> Union[Result, _T]:
        if is_session:
            maker = self.session_maker
            kw['bind_arguments'] = bind_arguments
        else:
            maker = self.engine.connect
        with maker() as conn:
            result = conn.execute(statement, params, execution_options, **kw)
            if on_close_pre:
                result = on_close_pre(result)
            if commit and not isinstance(statement, Select):
                conn.commit()
        return result

    def scalar(
            self,
            statement: Executable,
            params: Optional[_ExecuteParams] = None,
            *,
            execution_options: Optional[_ExecuteOptions] = None,
            bind_arguments: Optional[Mapping[str, Any]] = None,
            **kw: Any,
    ) -> Any:
        with self.session_maker() as session:
            return session.scalar(
                statement,
                params,
                execution_options=execution_options,
                bind_arguments=bind_arguments,
                **kw,
            )

    def scalars_all(
            self,
            statement: Executable,
            params: Optional[_ExecuteParams] = None,
            *,
            execution_options: Optional[_ExecuteOptions] = None,
            bind_arguments: Optional[Mapping[str, Any]] = None,
            **kw: Any,
    ) -> List[Any]:
        with self.session_maker() as session:
            return session.scalars(
                statement,
                params,
                execution_options=execution_options,
                bind_arguments=bind_arguments,
                **kw,
            ).all()

    def get(
            self,
            entity: Type[_T],
            ident: Any,
            *,
            options: Optional[Sequence[Any]] = None,
            populate_existing: bool = False,
            with_for_update: Optional[Any] = None,
            identity_token: Optional[Any] = None,
            execution_options: Optional[_ExecuteOptions] = None,
    ) -> Optional[_T]:
        with self.session_maker() as session:
            return session.get(
                entity,
                ident,
                options=options,
                populate_existing=populate_existing,
                with_for_update=with_for_update,
                identity_token=identity_token,
            )

    def delete(self, instance: Any) -> None:
        with self.session_maker() as session:
            with session.begin():
                session.delete(instance)

    def run_sync(
            self,
            fn: Callable[[Concatenate[Union[Session, Connection], _P]], _T],
            *args: _P.args,
            commit: bool = True,
            on_close_pre: Callable[[_T], _R] = None,
            is_session: bool = True,
            **kwargs: _P.kwargs
    ) -> Union[_T, _R]:
        maker = self.session_maker if is_session else self.engine.connect
        with maker() as conn:
            result = fn(conn, *args, **kwargs)
            if on_close_pre:
                result = on_close_pre(result)
            if commit:
                conn.commit()
        return result
