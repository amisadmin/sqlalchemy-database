from typing import Generator, Any, AsyncGenerator, Optional, Mapping, Union, Sequence, Type, List, Callable, TypeVar

from sqlalchemy.engine import Result, Connection
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine, create_async_engine
from sqlalchemy.future import Engine, create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import Executable, Select
from typing_extensions import Concatenate, ParamSpec

from sqlalchemy_database._abc_async_database import AbcAsyncDatabase

_P = ParamSpec("_P")
_T = TypeVar("_T")
_R = TypeVar("_R")

_ExecuteParams = Union[Mapping[Any, Any], Sequence[Mapping[Any, Any]]]
_ExecuteOptions = Mapping[Any, Any]


class AsyncDatabase(AbcAsyncDatabase):
    """`sqlalchemy` asynchronous database client
    """

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
        session_options.setdefault('class_', AsyncSession)
        self.session_maker: Callable[..., AsyncSession] = sessionmaker(self.engine, **session_options)
        """`sqlalchemy` session factory function
        
        Example:
            ```Python
            async with self.session_maker() as sesson:
                await session.delete(User,1)
                await session.commit()
            ```
        """

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
        kwargs.setdefault('future', True)
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
            example: The `Result.all`,`Result.scalar`,`Result.scalars`methods cannot be called again after the connection is closed.

        """
        if is_session:
            maker = self.session_maker
            kw['bind_arguments'] = bind_arguments
        else:
            maker = self.engine.connect
        async with maker() as conn:
            result = await conn.execute(statement, params, execution_options, **kw)  # type:ignore
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
        """
        Execute a statement and return a scalar result.

        Usage and parameters are the same as that of :meth:`_orm.Session.execute`;
        the return result is a scalar Python value.
        """
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
        """
        Execute a statement and return the results as scalar list.

        Usage and parameters are the same as that of :meth:`_orm.Session.execute`;
        the return result is a list of scalar Python value.
        """
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
        """Deletes an instance object."""
        async with self.session_maker() as session:
            async with session.begin():
                await session.delete(instance)

    async def save(self, *instances: Any, refresh: bool = False) -> None:
        """
        Save the given collection of instances.
        Args:
            *instances: A sequence of instance objects.
            refresh: Expire and refresh attributes on the given collection of instances.
        """
        async with self.session_maker() as session:
            async with session.begin():
                session.add_all(instances)
            if refresh:
                [await session.refresh(instance) for instance in instances]

    async def run_sync(
            self,
            fn: Callable[[Concatenate[Union[Session, Connection], _P]], _T],
            *args: _P.args,
            commit: bool = True,
            on_close_pre: Callable[[_T], _R] = None,
            is_session: bool = True,
            **kwargs: _P.kwargs
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
        maker = self.session_maker if is_session else self.engine.connect
        async with maker() as conn:
            result = await conn.run_sync(fn, *args, **kwargs)
            if on_close_pre:
                result = on_close_pre(result)
            if commit:
                await conn.commit()
        return result


class Database(AbcAsyncDatabase):
    """`sqlalchemy` synchronous database client

    """

    def __init__(self, engine: Engine, **session_options):
        super().__init__()
        self.engine: Engine = engine
        self.session_maker: Callable[..., Session] = sessionmaker(self.engine, **session_options)

    @classmethod
    def create(cls, url: str, *, session_options: Optional[Mapping[str, Any]] = None, **kwargs) -> "Database":
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

    def save(self, *instances: Any, refresh: bool = False) -> None:
        with self.session_maker() as session:
            with session.begin():
                session.add_all(instances)
            if refresh:
                [session.refresh(instance) for instance in instances]

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
