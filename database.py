"""Shared persistence: SQLite locally, PostgreSQL on Vercel."""

import json
import certifi
from pathlib import Path
from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    Column,
    String,
    Integer,
    Float,
    Text,
    ForeignKey,
    CheckConstraint,
    select,
    func,
    case,
    event,
    text,
)
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.pool import NullPool
from sqlalchemy.engine import make_url


class Database:
    def __init__(self, path, url=None):
        if url:
            if url.startswith("postgres://"):
                url = "postgresql+psycopg://" + url[len("postgres://") :]
            elif url.startswith("postgresql://"):
                url = "postgresql+psycopg://" + url[len("postgresql://") :]
            if not url.startswith("postgresql+psycopg://"):
                raise ValueError("DATABASE_URL must be a PostgreSQL connection URL.")
            parsed = make_url(url)
            if parsed.query.get("sslmode") != "verify-full":
                parsed = parsed.update_query_dict({"sslmode": "verify-full"})
            if "sslrootcert" not in parsed.query:
                parsed = parsed.update_query_dict({"sslrootcert": certifi.where()})
            self.engine = create_engine(
                parsed, poolclass=NullPool, connect_args={"connect_timeout": 10}
            )
        else:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            self.engine = create_engine(
                "sqlite:///" + str(path), connect_args={"timeout": 15}
            )

            @event.listens_for(self.engine, "connect")
            def configure(connection, record):
                connection.execute("PRAGMA foreign_keys=ON")
                connection.execute("PRAGMA journal_mode=WAL")

        m = MetaData()
        self.users = Table(
            "users",
            m,
            Column("id", String(64), primary_key=True),
            Column("created_at", String, server_default=func.current_timestamp()),
        )
        self.queries = Table(
            "queries",
            m,
            Column("id", Integer, primary_key=True),
            Column("user_id", String(64), ForeignKey("users.id"), nullable=False),
            Column("message", Text, nullable=False),
            Column("created_at", String, server_default=func.current_timestamp()),
        )
        self.responses = Table(
            "responses",
            m,
            Column("id", Integer, primary_key=True),
            Column(
                "query_id",
                Integer,
                ForeignKey("queries.id", ondelete="CASCADE"),
                unique=True,
                nullable=False,
            ),
            Column("response", Text, nullable=False),
            Column("intent", String(64), nullable=False),
            Column("confidence", Float, nullable=False),
            Column("latency", Float, nullable=False),
            Column("rating", Integer),
            CheckConstraint("rating IN (-1, 1)"),
        )
        self.knowledge = Table(
            "knowledge",
            m,
            Column("intent", String(64), primary_key=True),
            Column("data", Text, nullable=False),
        )
        self.metadata = m
        if url:
            with self.engine.begin() as connection:
                connection.execute(text("SELECT pg_advisory_xact_lock(2146409137)"))
                m.create_all(connection)
        else:
            m.create_all(self.engine)
        self.insert = postgres_insert if url else sqlite_insert

    def connect(self):
        return self.engine.begin()

    def entries(self, defaults, seed=False):
        with self.connect() as db:
            if seed:
                db.execute(
                    self.insert(self.knowledge)
                    .values(
                        [
                            {"intent": e["intent"], "data": json.dumps(e)}
                            for e in defaults
                        ]
                    )
                    .on_conflict_do_nothing(index_elements=["intent"])
                )
            entries = {
                row.intent: json.loads(row.data)
                for row in db.execute(select(self.knowledge))
            }
            return [entries[e["intent"]] for e in defaults]

    def save(self, user, message, result, latency):
        with self.connect() as db:
            db.execute(
                self.insert(self.users)
                .values(id=user)
                .on_conflict_do_nothing(index_elements=["id"])
            )
            q = db.execute(
                self.queries.insert()
                .values(user_id=user, message=message)
                .returning(self.queries.c.id)
            ).scalar_one()
            db.execute(
                self.responses.insert().values(
                    query_id=q,
                    response=result["response"],
                    intent=result["intent"],
                    confidence=result["confidence"],
                    latency=latency,
                )
            )
            return q

    def history(self, user):
        q, r = self.queries, self.responses
        with self.connect() as db:
            rows = (
                db.execute(
                    select(
                        q.c.id,
                        q.c.message,
                        q.c.created_at,
                        r.c.response,
                        r.c.intent,
                        r.c.rating,
                    )
                    .join(r, q.c.id == r.c.query_id)
                    .where(q.c.user_id == user)
                    .order_by(q.c.id.desc())
                    .limit(50)
                )
                .mappings()
                .all()
            )
            return [dict(row) for row in reversed(rows)]

    def rate(self, user, query, rating):
        with self.connect() as db:
            return db.execute(
                self.responses.update()
                .where(
                    self.responses.c.query_id == query,
                    self.responses.c.query_id.in_(
                        select(self.queries.c.id).where(self.queries.c.user_id == user)
                    ),
                )
                .values(rating=rating)
            ).rowcount

    def clear(self, user):
        with self.connect() as db:
            db.execute(self.queries.delete().where(self.queries.c.user_id == user))
            db.execute(self.users.delete().where(self.users.c.id == user))

    def stats(self):
        r = self.responses.c
        with self.connect() as db:
            row = dict(
                db.execute(
                    select(
                        func.count().label("total"),
                        func.coalesce(
                            func.sum(case((r.intent == "fallback", 1), else_=0)), 0
                        ).label("fallbacks"),
                        func.coalesce(func.avg(r.latency), 0).label("average_latency"),
                        func.coalesce(
                            func.sum(case((r.rating == 1, 1), else_=0)), 0
                        ).label("helpful"),
                        func.coalesce(
                            func.sum(case((r.rating == -1, 1), else_=0)), 0
                        ).label("unhelpful"),
                    ).select_from(self.responses)
                )
                .mappings()
                .one()
            )
            row["topics"] = [
                dict(x)
                for x in db.execute(
                    select(r.intent, func.count().label("count"))
                    .group_by(r.intent)
                    .order_by(func.count().desc())
                ).mappings()
            ]
            return row

    def update_entry(self, entry):
        with self.connect() as db:
            db.execute(
                self.knowledge.update()
                .where(self.knowledge.c.intent == entry["intent"])
                .values(data=json.dumps(entry))
            )
