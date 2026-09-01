from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

_engine_kwargs: dict = {"pool_pre_ping": True}
if settings.DATABASE_URL.startswith("postgresql"):
    _engine_kwargs.update({"pool_size": 5, "max_overflow": 10})

engine = create_engine(settings.DATABASE_URL, **_engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()