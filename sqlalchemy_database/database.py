import functools
from contextvars import ContextVar
from typing import (
    Any,
    AsyncGenerator,
    Callable,
    Generator,
    Mapping,
    Optional,
    TypeVar,
    Union,
)

from sqlalchemy.engine import URL, Connection
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_scoped_session,
    create_async_engine,
)
from sqlalchemy.future import Engine, create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from typing_extensions import Awaitable, Concatenate, ParamSpec

try:
    from sqlmodel import Session
    from sqlmodel.ext.asyncio.session import AsyncSession
except ImportError:
    from sqlalchemy.orm import Session
    from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy_database._abc_async_database import AbcAsyncDatabase, to_thread

_P = ParamSpec("_P")
_T = TypeVar("_T")
_R = TypeVar("_R")


class AsyncDatabase(AbcAsyncDatabase):
    """`sqlalchemy` asynchronous database client"""

    def __init__(
        self,
        engine: AsyncEngine,
        commit_on_exit: bool = True,
        **session_options,
    ):
        """
        Initialize the client through the asynchronous engine
        Args:
            engine: Asynchronous Engine
            commit_on_exit: Whether to commit the session when the context manager or session generator exits.
            **session_options: The default `session` initialization parameters
        """
        self.engine: AsyncEngine = engine
        """`sqlalchemy` Asynchronous Engine

        Example:
            ```Python
            async with self.engine.begin() as conn:
                await conn.run_sync(SQLModel.metadata.create_all)
            ```
        """
        self.commit_on_exit: bool = commit_on_exit
        """Whether to commit the session when the context manager or session generator exits."""
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
        self._session_scope: ContextVar[Union[str, AsyncSession, None]] = ContextVar(
            f"_session_context_var_{id(self)}", default=None
        )
        self.scoped_session: async_scoped_session = async_scoped_session(self.session_maker, scopefunc=self._session_scope.get)
        super().__init__(engine)

    @property
    def session(self) -> AsyncSession:
        """Return an instance of Session local to the current async context.

        Note: Must register middleware in fastapi application to get session in request.

        Example:
            ```Python
            app = FastAPI()
            app.add_middleware(db.asgi_middleware)

            @app.get('/get_user')
            async def get_user(id:int):
                return await db.session.get(User,id)
            ```
        In ordinary methods, session will return None. You can get it through:
            ```Python
            async with db():
                await db.session.get(User,id)
            ```
        """
        return self.scoped_session()

    @property
    def scoped(self) -> bool:
        """Whether the current context has a session. If False, the session is the default global session,
        and the transaction needs to be manually submitted.
        """
        return bool(self._session_scope.get())

    def __call__(self, scope: Any = None):
        return AsyncSessionContextVarManager(self, scope=scope)

    @classmethod
    def create(
        cls, url: Union[str, URL], *, commit_on_exit: bool = True, session_options: Mapping[str, Any] = None, **kwargs
    ) -> "AsyncDatabase":
        """
        Initialize the client with a database connection string
        Args:
            url: Asynchronous database connection string
            commit_on_exit: Whether to commit the session when the context manager or session generator exits.
            session_options: The default `session` initialization parameters
            **kwargs: Asynchronous engine initialization parameters

        Returns:
            Return the client instance.
        """
        kwargs.setdefault("future", True)
        engine = create_async_engine(url, **kwargs)
        session_options = session_options or {}
        return cls(engine, commit_on_exit=commit_on_exit, **session_options)

    async def session_generator(self) -> AsyncGenerator[AsyncSession, Any]:
        """AsyncSession Generator, available for FastAPI dependencies.

        Example:
            ```Python
            @router.get('/get_user')
            async get_user(id:int,session:AsyncSession=Depends(db.session_generator)):
                return await session.get(User,id)
            ```
        """
        if self.scoped:
            """If the current context has a session, return it."""
            yield self.session
        else:
            """If the current context has no session, create a new session."""
            async with self.session_maker() as session:
                yield session
                if self.commit_on_exit:
                    await session.commit()

    async def run_sync(
        self,
        fn: Callable[[Concatenate[Union[Session, Connection], _P]], _T],
        *args: _P.args,
        is_session: bool = True,
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
            is_session: Session or not. If true, an `AsyncSession` is created.
                If false, an `AsyncConnection` is created. The default is true.
            **kwargs: Synchronization function keyword argument

        Returns: Returns the result of the fn synchronization function.

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
        if is_session:
            return await self.session.run_sync(fn, *args, **kwargs)
        async with self.engine.begin() as conn:
            return await conn.run_sync(fn, *args, **kwargs)


class Database(AbcAsyncDatabase):
    """`sqlalchemy` synchronous database client"""

    def __init__(self, engine: Engine, commit_on_exit: bool = True, **session_options):
        self.engine: Engine = engine
        self.commit_on_exit: bool = commit_on_exit
        session_options.setdefault("class_", Session)
        self.session_maker: Callable[..., Session] = sessionmaker(self.engine, **session_options)
        self._session_scope: ContextVar[Union[str, Session, None]] = ContextVar(f"_session_context_var_{id(self)}", default=None)
        self.scoped_session: scoped_session = scoped_session(self.session_maker, scopefunc=self._session_scope.get)
        """Returns the Session local instance for the current context or current thread."""
        super().__init__(engine)

    @property
    def session(self) -> Session:
        return self.scoped_session()

    @property
    def scoped(self) -> bool:
        return bool(self._session_scope.get())

    def __call__(self, scope: Any = None):
        return SessionContextVarManager(self, scope=scope)

    @classmethod
    def create(
        cls, url: Union[str, URL], *, commit_on_exit: bool = True, session_options: Optional[Mapping[str, Any]] = None, **kwargs
    ) -> "Database":
        kwargs.setdefault("future", True)
        engine = create_engine(url, **kwargs)
        session_options = session_options or {}
        return cls(engine, **session_options)

    def session_generator(self) -> Generator[Session, Any, None]:
        if self.scoped:
            """If the current context has a session, return it."""
            yield self.session
        else:
            """If the current context has no session, create a new session."""
            with self.session_maker() as session:
                yield session
                if self.commit_on_exit:
                    session.commit()

    def run_sync(
        self,
        fn: Callable[[Concatenate[Union[Session, Connection], _P]], _T],
        *args: _P.args,
        is_session: bool = True,
        **kwargs: _P.kwargs,
    ) -> Union[_T, _R]:
        if is_session:
            return fn(self.session, *args, **kwargs)
        with self.engine.begin() as conn:
            return fn(conn, *args, **kwargs)

    def asyncify(self, db: Union[AsyncSession, AsyncDatabase], fn: Callable[_P, _T]) -> Callable[_P, Awaitable[_T]]:
        """Convert the given sync function that runs in the context of a sync session to
        an async function that runs in the context of an async session.
        Args:
            db: Async database client or session
            fn: sync function
        Returns:
            Returns the async function.
        """
        session = db if isinstance(db, AsyncSession) else db.session

        @functools.wraps(fn)
        async def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _T:
            return await session.run_sync(self._sync_context_run, fn, *args, **kwargs)

        return wrapper

    def _sync_context_run(self, session: Session, fn: Callable[_P, _T], *args: _P.args, **kwargs: _P.kwargs) -> _T:
        """Run the given sync function in the context of the given sync session."""
        with self(session):
            return fn(*args, **kwargs)


class SessionContextVarManager:
    _SessionCls = Session

    def __init__(self, db: Database, scope: Any = None):
        self.db = db
        self._token = None
        self._scope = scope

    def __enter__(self):
        if not self._scope:
            """If the user does not specify the scope, a new session is created by default,
            and set as the current context session."""
            session = self.db.session_maker()
            self._token = self.db._session_scope.set(session)
            self.db.scoped_session.registry.set(session)
        elif isinstance(self._scope, self._SessionCls):
            """If the user specifies the current scope as a Session object,
            the current Session object is set as the context session.
            """
            self._token = self.db._session_scope.set(self._scope)
            self.db.scoped_session.registry.set(self._scope)
        else:
            """If the user specifies the scope as another type,
            the scope is used as the context session variable identifier.
            """
            self._token = self.db._session_scope.set(self._scope)
        return self.db.session

    def _close_session(self, session: Session, exc_type):
        try:
            if exc_type is not None:
                session.rollback()
            elif self.db.commit_on_exit:
                session.commit()
        finally:
            session.close()

    def __exit__(self, exc_type, exc_value, traceback):
        if not (self._scope and isinstance(self._scope, self._SessionCls)):
            """If the scope is a session, it will not be closed."""
            self._close_session(self.db.session, exc_type)
        self.db.scoped_session.registry.clear()
        self.db._session_scope.reset(self._token)

    async def __aenter__(self):
        return self.__enter__()

    async def __aexit__(self, exc_type, exc_value, traceback):
        if not (self._scope and isinstance(self._scope, self._SessionCls)):
            """If the scope is a session, it will not be closed."""
            await to_thread(self._close_session, self.db.session, exc_type)
        self.db.scoped_session.registry.clear()
        self.db._session_scope.reset(self._token)


class AsyncSessionContextVarManager(SessionContextVarManager):
    _SessionCls = AsyncSession

    def __init__(self, db: AsyncDatabase, scope: Any = None):
        super().__init__(db, scope)  # type: ignore

    def __exit__(self, exc_type, exc_val, exc_tb):
        raise NotImplementedError("AsyncSessionContextVarManager does not support sync context manager.")

    async def __aexit__(self, exc_type, exc_value, traceback):
        self.db: AsyncDatabase
        if not (self._scope and isinstance(self._scope, self._SessionCls)):
            """If the scope is a session, it will not be closed."""
            session = self.db.session
            try:
                if exc_type is not None:
                    await session.rollback()
                elif self.db.commit_on_exit:
                    await session.commit()
            finally:
                await session.close()
        self.db.scoped_session.registry.clear()
        self.db._session_scope.reset(self._token)
