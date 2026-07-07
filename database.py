import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base

# SO-006: Anchor the DB path to the directory containing this file so the
# correct database is used regardless of the process CWD (e.g. Streamlit
# changes the working directory on startup).
_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "secureops.db")
engine = create_engine(f"sqlite:///{_DB_PATH}", echo=False)
SessionLocal = sessionmaker(bind=engine)


def init_db():
    Base.metadata.create_all(engine)