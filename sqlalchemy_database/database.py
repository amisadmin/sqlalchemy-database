from contextvars import ContextVar
from typing import (
    Any,
    AsyncGenerator,
    Callable,
    Generator,
    List,
    Mapping,
    Optional,
    Sequence,
    Type,
    TypeVar,
    Union,
)

from sqlalchemy.engine import Connection, Result
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine
from sqlalchemy.future import Engine, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import Executable, Select
from typing_extensions import Concatenate, ParamSpec

try:
    from sqlmodel import Session
    from sqlmodel.ext.asyncio.session import AsyncSession
except ImportError:
    from sqlalchemy.orm import Session
    from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy_database._abc_async_database import AbcAsyncDatabase

_P = ParamSpec("_P")
_T = TypeVar("_T")
_R = TypeVar("_R")

_ExecuteParams = Union[Mapping[Any, Any], Sequence[Mapping[Any, Any]]]
_ExecuteOptions = Mapping[Any, Any]


class AsyncDatabase(AbcAsyncDatabase):
    """`sqlalchemy` asynchronous database client"""

    def __init__(self, engine: AsyncEngine, **session_options):
        """
        Initialize the client through the asynchronous engine
        Args:
            engine: Asynchronous Engine
            **session_options: The default `session` initialization parameters
        """
        super().__init__()
        self.engine: AsyncEngine = engine
        """`sqlalchemy` Asynchronous Engine

        Example:
            ```Python
            async with self.engine.begin() as conn:
                await conn.run_sync(SQLModel.metadata.create_all)
            ```
        """
        session_options.setdefault("class_", AsyncSession)
        self.session_maker: Callable[..., AsyncSession] = sessionmaker(self.engine, **session_options)
        """`sqlalchemy` session factory function

        Example:
            ```Python
            async with self.session_maker() as sesson:
                await session.delete(User,1)
                await session.commit()
            ```
        """
        self._session_context_var: ContextVar[Optional[AsyncSession]] = ContextVar("_session_context_var", default=None)

    @property
    def session(self) -> Optional[AsyncSession]:
        """Return an instance of Session local to the current async context.

        Note: Must register middleware in fastapi application to get session in request.

        Example:
            ```Python
            app = FastAPI()
            app.add_middleware(BaseHTTPMiddleware, dispatch=db.asgi_dispatch)

            @app.get('/get_user')
            async def get_user(id:int):
                return await db.session.get(User,id)
            ```
        In ordinary methods, session will return None. You can get it through:
            ```Python
            async with db():
                db.session.get(User,id)
            ```
        """
        return self._session_context_var.get()

    def __call__(self):
        return AsyncSessionContextVarManager(self)

    @classmethod
    def create(cls, url: str, *, session_options: Mapping[str, Any] = None, **kwargs) -> "AsyncDatabase":
        """
        Initialize the client with a database connection string
        Args:
            url: Asynchronous database connection string
            session_options: The default `session` initialization parameters
            **kwargs: Asynchronous engine initialization parameters

        Returns:
            Return the client instance.
        """
        kwargs.setdefault("future", True)
        engine = create_async_engine(url, **kwargs)
        session_options = session_options or {}
        return cls(engine, **session_options)

    async def session_generator(self) -> AsyncGenerator[AsyncSession, Any]:
        """AsyncSession Generator, available for FastAPI dependencies.

        Example:
            ```Python
            @router.get('/get_user')
            async get_user(id:int,session:AsyncSession=Depends(db.session_generator)):
                return await session.get(User,id)
            ```
        """
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
        executor: Union[AsyncSession, AsyncConnection, None] = None,
        **kw: Any,
    ) -> Union[Result, _T]:
        """
        Execute SQL expressions. Automatically create a connection and execute `AsyncSession.execute` or `AsyncConnection.execute`
        Args:
            statement: Executable expressions. Example: select,update,insert,delete
            params: Optional dictionary, or list of dictionaries, containing
                bound parameter values.   If a single dictionary, single-row
                execution occurs; if a list of dictionaries, an
                "executemany" will be invoked.  The keys in each dictionary
                must correspond to parameter names present in the statement.
            execution_options: optional dictionary of execution options,
                 which will be associated with the statement execution.  This
                 dictionary can provide a subset of the options that are accepted
                 by :meth:`_engine.Connection.execution_options`, and may also
                 provide additional options understood only in an ORM context.
            bind_arguments: dictionary of additional arguments to determine the bind.
                May include "mapper", "bind", or other custom arguments.
                Contents of this dictionary are passed to the :meth:`.Session.get_bind` method.
            commit: Commit or not. If the Statement argument is a `select` object,
                it is not committed by default. Otherwise, it defaults to commit.
            on_close_pre: Close the previous hook function.
            is_session: Session or not. If true, an `AsyncSession` is created.
                If false, an `AsyncConnection` is created. The default is true.
            executor: The executor of the statement. If not specified, an `AsyncSession` or `AsyncConnection` is created.
            **kw: Deprecated; use the bind_arguments dictionary

        Returns:
            Return the execution result.

        Example:
            ```Python
            from sqlalchemy import select
            user = db.execute(
                select(User).where(User.id == 5),
                on_close_pre=lambda r:r.scalar()
            )
            ```

        Note:
            After the connection is closed, the session data will be cleared.
            Please use the 'on_close_pre' parameter to process the execution result.
            example: The `Result.all`,`Result.scalar`,`Result.scalars`methods
                cannot be called again after the connection is closed.

        """
        need_close = False
        if executor is None or not isinstance(executor, (AsyncSession, AsyncConnection)):
            need_close = True
            if is_session:
                executor = self.session
                if executor is None:
                    executor = self.session_maker()
                else:
                    need_close = False
                kw["bind_arguments"] = bind_arguments
            else:
                executor = await self.engine.connect()
        async with ExecutorContextManager(executor, need_close=need_close) as executor:
            result = await executor.execute(statement, params, execution_options, **kw)  # type:ignore
            if on_close_pre:
                result = on_close_pre(result)
            if commit and not isinstance(statement, Select):
                await executor.commit()
            return result

    async def scalar(
        self,
        statement: Executable,
        params: Optional[_ExecuteParams] = None,
        *,
        execution_options: Optional[_ExecuteOptions] = None,
        bind_arguments: Optional[Mapping[str, Any]] = None,
        session: Optional[AsyncSession] = None,
        **kw: Any,
    ) -> Any:
        """
        Execute a statement and return a scalar result.

        Usage and parameters are the same as that of :meth:`_orm.Session.execute`;
        the return result is a scalar Python value.
        """
        need_close = False
        if session is None or not isinstance(session, AsyncSession):
            session = self.session
            if session is None:
                need_close = True
                session = self.session_maker()
        async with ExecutorContextManager(session, need_close=need_close) as session:
            result = await session.scalar(
                statement,
                params,
                execution_options=execution_options,
                bind_arguments=bind_arguments,
                **kw,
            )
            return result

    async def scalars_all(
        self,
        statement: Executable,
        params: Optional[_ExecuteParams] = None,
        *,
        execution_options: Optional[_ExecuteOptions] = None,
        session: Optional[AsyncSession] = None,
        **kw: Any,
    ) -> List[Any]:
        """
        Execute a statement and return the results as scalar list.

        Usage and parameters are the same as that of :meth:`_orm.Session.execute`;
        the return result is a list of scalar Python value.
        """
        need_close = False
        if session is None or not isinstance(session, AsyncSession):
            session = self.session
            if session is None:
                need_close = True
                session = self.session_maker()
        async with ExecutorContextManager(session, need_close=need_close) as session:
            result = (
                await session.scalars(
                    statement,
                    params,
                    execution_options=execution_options,
                    **kw,
                )
            ).all()
            return result

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
        session: Optional[AsyncSession] = None,
    ) -> Optional[_T]:
        """
        Return an instance based on the given primary key identifier, or `None` if not found.

        Args:
            entity: a mapped class or :class:`.Mapper` indicating the type of entity to be loaded.
            ident:  A scalar, tuple, or dictionary representing the primary key.
                For a composite (e.g. multiple column) primary key, a tuple or dictionary should be passed.
            options: optional sequence of loader options which will be applied to the query, if one is emitted.
            populate_existing: causes the method to unconditionally emit a SQL query
                and refresh the object with the newly loaded data,
                regardless of whether or not the object is already present.
            with_for_update: optional boolean ``True`` indicating FOR UPDATE should be used,
                or may be a dictionary containing flags to
                indicate a more specific set of FOR UPDATE flags for the SELECT;
                flags should match the parameters of :meth:`_query.Query.with_for_update`.
                Supersedes the :paramref:`.Session.refresh.lockmode` parameter.
            identity_token:
            execution_options: optional dictionary of execution options,
                which will be associated with the query execution if one is emitted.
                This dictionary can provide a subset of the options that are
                accepted by :meth:`_engine.Connection.execution_options`, and may
                also provide additional options understood only in an ORM context.
            session: If not specified, an `AsyncSession` is created.
        Returns:
            The object instance, or ``None``.

        Example:
            ```Python
            my_user = db.get(User, 5)

            my_user = db.get(User, 5, options=[selectinload(User.Address)])

            some_object = db.get(VersionedFoo, (5, 10))

            some_object = db.get(
                VersionedFoo,
                {"id": 5, "version_id": 10}
            )
            ```
        """
        need_close = False
        if session is None or not isinstance(session, AsyncSession):
            session = self.session
            if session is None:
                need_close = True
                session = self.session_maker()
        async with ExecutorContextManager(session, need_close=need_close) as session:
            result = await session.get(
                entity,
                ident,
                options=options,
                populate_existing=populate_existing,
                with_for_update=with_for_update,
                identity_token=identity_token,
            )
            return result

    async def delete(self, instance: Any) -> None:
        """Deletes an instance object."""
        if self.session is not None:
            await self.session.delete(instance)
            await self.session.commit()
        else:
            async with self.session_maker() as session:
                async with session.begin():
                    await session.delete(instance)

    async def save(self, *instances: Any, refresh: bool = False, session: Optional[AsyncSession] = None) -> None:
        """
        Save the given collection of instances.
            *instances: A sequence of instance objects.
            refresh: Expire and refresh attributes on the given collection of instances.
                    Args:
            session: If not specified, an `AsyncSession` is created.
        """
        need_close = False
        if session is None or not isinstance(session, AsyncSession):
            session = self.session
            if session is None:
                need_close = True
                session = self.session_maker()
        async with ExecutorContextManager(session, need_close=need_close) as session:
            session.add_all(instances)
            await session.commit()
            if refresh:
                [await session.refresh(instance) for instance in instances]

    async def run_sync(
        self,
        fn: Callable[[Concatenate[Union[Session, Connection], _P]], _T],
        *args: _P.args,
        commit: bool = True,
        on_close_pre: Callable[[_T], _R] = None,
        is_session: bool = True,
        executor: Union[AsyncSession, AsyncConnection, None] = None,
        **kwargs: _P.kwargs,
    ) -> Union[_T, _R]:
        """
        Invoke the given sync callable passing sync self as the first
        argument.

        This method maintains the asyncio event loop all the way through
        to the database connection by running the given callable in a
        specially instrumented greenlet.

        Args:
            fn: Synchronization function
            *args: Synchronization function positional argument
            commit: Commit or not.
            on_close_pre: Close the previous hook function.
            is_session: Session or not. If true, an `AsyncSession` is created.
                If false, an `AsyncConnection` is created. The default is true.
            executor: The executor of the statement. If not specified, an `AsyncSession` or `AsyncConnection` is created.
            **kwargs: Synchronization function keyword argument

        Returns: 返回同步函数fn执行结果.如果`on_close_pre`不为空,则返回`on_close_pre`二次处理结果.

        Example:
            ```Python
            def get_user(session:Session,id:int):
                return session.get(User,id)

            user = await db.run_sync(get_user,5)
            ```
        None:
            The provided callable is invoked inline within the asyncio event
            loop, and will block on traditional IO calls.  IO within this
            callable should only call into SQLAlchemy's asyncio database
            APIs which will be properly adapted to the greenlet context.
        """
        need_close = False
        if executor is None or not isinstance(executor, (AsyncSession, AsyncConnection)):
            if is_session:
                executor = self.session
                if executor is None:
                    executor = self.session_maker()
                    need_close = True
            else:
                executor = await self.engine.connect()
                need_close = True
        async with ExecutorContextManager(executor, need_close=need_close) as executor:
            result = await executor.run_sync(fn, *args, **kwargs)
            if on_close_pre:
                result = on_close_pre(result)
            if commit:
                await executor.commit()
            return result


class Database(AbcAsyncDatabase):
    """`sqlalchemy` synchronous database client"""

    def __init__(self, engine: Engine, **session_options):
        super().__init__()
        self.engine: Engine = engine
        session_options.setdefault("class_", Session)
        self.session_maker: Callable[..., Session] = sessionmaker(self.engine, **session_options)
        self._session_context_var: ContextVar[Optional[Session]] = ContextVar("_session_context_var", default=None)

    @property
    def session(self) -> Optional[Session]:
        """Return an instance of Session local to the current context."""
        return self._session_context_var.get()

    def __call__(self):
        return SessionContextVarManager(self)

    @classmethod
    def create(cls, url: str, *, session_options: Optional[Mapping[str, Any]] = None, **kwargs) -> "Database":
        kwargs.setdefault("future", True)
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
        executor: Union[Session, Connection, None] = None,
        **kw: Any,
    ) -> Union[Result, _T]:
        need_close = False
        if executor is None or not isinstance(executor, (Session, Connection)):
            need_close = True
            if is_session:
                executor = self.session
                if executor is None:
                    executor = self.session_maker()
                else:
                    need_close = False
                kw["bind_arguments"] = bind_arguments
            else:
                executor = self.engine.connect()
        with ExecutorContextManager(executor, need_close=need_close) as executor:
            result = executor.execute(statement, params, execution_options, **kw)
            if on_close_pre:
                result = on_close_pre(result)
            if commit and not isinstance(statement, Select):
                executor.commit()
            return result

    def scalar(
        self,
        statement: Executable,
        params: Optional[_ExecuteParams] = None,
        *,
        execution_options: Optional[_ExecuteOptions] = None,
        bind_arguments: Optional[Mapping[str, Any]] = None,
        session: Optional[Session] = None,
        **kw: Any,
    ) -> Any:
        need_close = False
        if session is None or not isinstance(session, Session):
            session = self.session
            if session is None:
                need_close = True
                session = self.session_maker()
        with ExecutorContextManager(session, need_close=need_close) as session:
            result = session.scalar(
                statement,
                params,
                execution_options=execution_options,
                bind_arguments=bind_arguments,
                **kw,
            )
            return result

    def scalars_all(
        self,
        statement: Executable,
        params: Optional[_ExecuteParams] = None,
        *,
        execution_options: Optional[_ExecuteOptions] = None,
        bind_arguments: Optional[Mapping[str, Any]] = None,
        session: Optional[Session] = None,
        **kw: Any,
    ) -> List[Any]:
        need_close = False
        if session is None or not isinstance(session, Session):
            session = self.session
            if session is None:
                need_close = True
                session = self.session_maker()
        with ExecutorContextManager(session, need_close=need_close) as session:
            result = session.scalars(
                statement,
                params,
                execution_options=execution_options,
                bind_arguments=bind_arguments,
                **kw,
            ).all()
            return result

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
        session: Optional[Session] = None,
    ) -> Optional[_T]:
        need_close = False
        if session is None or not isinstance(session, Session):
            session = self.session
            if session is None:
                need_close = True
                session = self.session_maker()
        with ExecutorContextManager(session, need_close=need_close) as session:
            result = session.get(
                entity,
                ident,
                options=options,
                populate_existing=populate_existing,
                with_for_update=with_for_update,
                identity_token=identity_token,
            )
            return result

    def delete(self, instance: Any) -> None:
        if self.session is not None:
            self.session.delete(instance)
            self.session.commit()
        else:
            with self.session_maker() as session:
                with session.begin():
                    session.delete(instance)

    def save(self, *instances: Any, refresh: bool = False, session: Optional[Session] = None) -> None:
        need_close = False
        if session is None or not isinstance(session, Session):
            session = self.session
            if session is None:
                need_close = True
                session = self.session_maker()
        with ExecutorContextManager(session, need_close=need_close) as session:
            session.add_all(instances)
            session.commit()
            if refresh:
                [session.refresh(instance) for instance in instances]

    def run_sync(
        self,
        fn: Callable[[Concatenate[Union[Session, Connection], _P]], _T],
        *args: _P.args,
        commit: bool = True,
        on_close_pre: Callable[[_T], _R] = None,
        is_session: bool = True,
        executor: Union[Session, Connection, None] = None,
        **kwargs: _P.kwargs,
    ) -> Union[_T, _R]:
        need_close = False
        if executor is None or not isinstance(executor, (Session, Connection)):
            need_close = True
            if is_session:
                executor = self.session
                if executor is None:
                    executor = self.session_maker()
                else:
                    need_close = False
            else:
                executor = self.engine.connect()
        with ExecutorContextManager(executor, need_close=need_close) as executor:
            result = fn(executor, *args, **kwargs)
            if on_close_pre:
                result = on_close_pre(result)
            if commit:
                executor.commit()
            return result


class ExecutorContextManager:
    """Actuator context manager, optionally closing the executor"""

    def __init__(self, executor: Union[Session, Connection, AsyncSession, AsyncConnection], need_close: bool = True):
        self.executor = executor
        self.need_close = need_close

    def __enter__(self):
        return self.executor

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.need_close:
            self.executor.close()

    async def __aenter__(self):
        return self.executor

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.need_close:
            await self.executor.close()


class AsyncSessionContextVarManager:
    def __init__(self, db: AsyncDatabase):
        self.db = db
        self.token = None

    async def __aenter__(self):
        session = self.db.session_maker()
        self.token = self.db._session_context_var.set(session)
        return session

    async def __aexit__(self, exc_type, exc_value, traceback):
        session = self.db._session_context_var.get()
        if exc_type is not None:
            await session.rollback()
        await session.close()
        self.db._session_context_var.reset(self.token)


class SessionContextVarManager:
    def __init__(self, db: Database):
        self.db = db
        self.token = None

    def __enter__(self):
        session = self.db.session_maker()
        self.token = self.db._session_context_var.set(session)
        return session

    def __exit__(self, exc_type, exc_value, traceback):
        session = self.db._session_context_var.get()
        if exc_type is not None:
            session.rollback()
        session.close()
        self.db._session_context_var.reset(self.token)

    async def __aenter__(self):
        return self.__enter__()

    async def __aexit__(self, exc_type, exc_value, traceback):
        self.__exit__(exc_type, exc_value, traceback)
