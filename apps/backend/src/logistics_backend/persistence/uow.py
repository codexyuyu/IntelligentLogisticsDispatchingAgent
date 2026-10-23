"""One transaction per application operation; rollback on any exception.

``commit`` is explicit for application services that must finish several statements before
the context exits; ``__exit__`` commits only if no explicit commit happened, and always
rolls back when the block raised. An optional isolation level is applied before ``BEGIN``
so P03-03 can request a single ``REPEATABLE READ`` snapshot.
"""
from sqlalchemy import Engine


class UnitOfWork:
    def __init__(self, engine: Engine, isolation: str | None = None):
        self.engine = engine
        self.isolation = isolation
        self.connection = None
        self.transaction = None
        self._committed = False

    def __enter__(self):
        self.connection = self.engine.connect()
        if self.isolation is not None:
            self.connection = self.connection.execution_options(isolation_level=self.isolation)
        self.transaction = self.connection.begin()
        return self

    def commit(self) -> None:
        if self.transaction is None or self._committed:
            raise RuntimeError("unit of work is not active or already committed")
        self.transaction.commit()
        self._committed = True

    def rollback(self) -> None:
        if self.transaction is None or self._committed:
            raise RuntimeError("unit of work is not active or already committed")
        self.transaction.rollback()
        self._committed = True

    def __exit__(self, exc_type, exc, traceback):
        try:
            if exc_type is None and not self._committed:
                self.transaction.commit()
            elif exc_type is not None and not self._committed:
                self.transaction.rollback()
        finally:
            self.connection.close()
