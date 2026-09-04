"""Persistence failures expressed without leaking the ORM."""


class PersistenceError(RuntimeError):
    """Raised when the database rejects or cannot complete a write.

    Repositories and the unit of work translate SQLAlchemy exceptions into
    this type so service and transport layers never import SQLAlchemy just to
    handle a failed write.
    """
