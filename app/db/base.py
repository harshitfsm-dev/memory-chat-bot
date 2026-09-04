import uuid

from sqlalchemy.orm import DeclarativeBase


def new_uuid() -> str:
    """Generate a primary key value.

    Applied as a column default, so it runs during flush rather than at
    construction. A repository that needs the key before the surrounding commit
    must flush to obtain it.
    """
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass
