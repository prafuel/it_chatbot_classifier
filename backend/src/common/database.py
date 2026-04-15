import os
import logging
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from tenacity import retry, stop_after_attempt, wait_fixed, before_log, after_log
from sqlalchemy_utils import database_exists, create_database

DATABASE_URL = f"postgresql://{str(os.environ.get('POSTGRES_USER'))}:{str(os.environ.get('POSTGRES_PASSWORD'))}@{str(os.environ.get('POSTGRES_SERVER'))}/{str(os.environ.get('POSTGRES_DB'))}"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=50,
    max_overflow=30,
    pool_timeout=30,
    pool_recycle=3600
)
metadata = MetaData()
metadata.bind = engine
Base = declarative_base(metadata=metadata)

max_tries = 60 * 5  # 5 minutes
wait_seconds = 1


@retry(
    stop=stop_after_attempt(max_tries),
    wait=wait_fixed(wait_seconds),
    before=before_log(logging, logging.INFO),
    after=after_log(logging, logging.WARN),
)
def get_db_engine():
    try:
        if not database_exists(engine.url):
            create_database(engine.url)
        return engine
    except Exception as e:
        logging.error(e)
        raise e

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_db_engine())

def get_db():
    try:
        db = SessionLocal()
        return db
    finally:
        db.close()