import os
import enum

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy import create_engine
from sqlalchemy import (
    func,
    Column,
    DateTime,
    Enum,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)

DATABASE_URI = os.environ.get("DATABASE_URI", "sqlite:///screen.db")

engine = create_engine(DATABASE_URI)
db_session = scoped_session(
    sessionmaker(autocommit=False, autoflush=False, bind=engine)
)

Base = declarative_base()


class STATUS(enum.Enum):
    running = "running"
    dead = "dead"


class PINFO(Base):
    __tablename__ = "pinfo"
    __table_args__ = (UniqueConstraint("create_time", "pid"),)

    id = Column(Integer, primary_key=True)
    name = Column(String)
    pid = Column(Integer)
    ppid = Column(Integer)
    cwd = Column(String)
    exe = Column(String)
    status = Column(Enum(STATUS))
    username = Column(String)
    cmdline = Column(String)
    terminal = Column(String)
    environ = Column(JSON)
    create_time = Column(Integer)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    def as_dict(self):
        result = {}
        for key in self.__mapper__.c.keys():
            if getattr(self, key) is not None:
                result[key] = str(getattr(self, key))
            else:
                result[key] = getattr(self, key)
        return result


def get_pinfo_list(only_running: bool = False) -> list:
    if only_running:
        return (
            db_session.query(PINFO)
            .filter(PINFO.status == STATUS.running)
            .order_by(PINFO.updated_at)
            .all()
        )
    else:
        return db_session.query(PINFO).order_by(PINFO.updated_at).all()


def update_pinfo(p: dict, is_running: bool = True) -> bool:
    is_created = False

    pinfo = (
        db_session.query(PINFO)
        .filter(PINFO.pid == p.get("pid"), PINFO.create_time == p.get("create_time"))
        .first()
    )

    if not pinfo:
        pinfo = PINFO(
            name=p.get("name"),
            pid=p.get("pid"),
            ppid=p.get("ppid"),
            cwd=p.get("cwd"),
            exe=p.get("exe"),
            username=p.get("username"),
            cmdline=" ".join(p.get("cmdline")) if p.get("cmdline") else None,
            terminal=p.get("terminal"),
            environ=p.get("environ"),
            create_time=p.get("create_time"),
            status=STATUS.running,
        )
        is_created = True
    else:
        pinfo.status = STATUS.running if is_running else STATUS.dead
        pinfo.updated_at = func.now()

    db_session.add(pinfo)
    db_session.commit()

    return is_created


Base.metadata.create_all(engine)
