"""
Migrate data from data/claude_generated.xlsx into PostgreSQL.

Usage:
    python scripts/migrate_excel_to_db.py          # uses localhost
    POSTGRES_SERVER=postgresdb python scripts/migrate_excel_to_db.py  # Docker

The script is self-contained — it defines its own SQLAlchemy models
mirroring models.py so it can run independently of the app.
"""

import os
import sys
import enum
import uuid
from datetime import datetime
from pathlib import Path

import openpyxl
from sqlalchemy import (
    Column, String, Text, DateTime, Boolean, Enum, JSON,
    create_engine, text, MetaData,
)
from sqlalchemy.dialects.postgresql import UUID, insert as pg_insert
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# ---------------------------------------------------------------------------
# Resolve paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXCEL_PATH = PROJECT_ROOT / "data" / "claude_generated.xlsx"
ENV_PATH = PROJECT_ROOT / ".env"

# ---------------------------------------------------------------------------
# Load .env manually (avoid extra dependency)
# ---------------------------------------------------------------------------
def load_env(path: Path):
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)

load_env(ENV_PATH)

# Override POSTGRES_SERVER to localhost for local execution (outside Docker)
if os.environ.get("POSTGRES_SERVER") in ("postgresdb", None):
    os.environ["POSTGRES_SERVER"] = "localhost"

# ---------------------------------------------------------------------------
# DB connection
# ---------------------------------------------------------------------------
DATABASE_URL = (
    f"postgresql://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}"
    f"@{os.environ['POSTGRES_SERVER']}/{os.environ['POSTGRES_DB']}"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# ---------------------------------------------------------------------------
# Enums (mirror common/models.py)
# ---------------------------------------------------------------------------
class RoleEnum(str, enum.Enum):
    USER = "USER"
    IT_AGENT = "IT_AGENT"
    ADMIN = "ADMIN"

class StatusEnum(str, enum.Enum):
    NOT_ASSIGNED = "NOT_ASSIGNED"
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"

class PriorityEnum(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class SourceEnum(str, enum.Enum):
    chatbot = "chatbot"
    portal = "portal"
    email = "email"

# ---------------------------------------------------------------------------
# ORM models (self-contained, mirrors common/models.py)
# ---------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    role = Column(Enum(RoleEnum), default=RoleEnum.USER)
    encrypted_password = Column(String(255), nullable=False)
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class Category(Base):
    __tablename__ = "categories"
    category_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False)

class SubCategory(Base):
    __tablename__ = "sub_categories"
    sub_category_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_id = Column(UUID(as_uuid=True), nullable=False)
    name = Column(String(255), nullable=False)

class Ticket(Base):
    __tablename__ = "tickets"
    ticket_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(Enum(StatusEnum), default=StatusEnum.NOT_ASSIGNED)
    priority = Column(Enum(PriorityEnum), default=PriorityEnum.MEDIUM)
    category_id = Column(UUID(as_uuid=True), nullable=True)
    sub_category_id = Column(UUID(as_uuid=True), nullable=True)
    created_by = Column(UUID(as_uuid=True), nullable=False)
    assigned_to = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    sla_due_at = Column(DateTime, nullable=True)
    source = Column(Enum(SourceEnum), default=SourceEnum.chatbot)

class KnowledgeBase(Base):
    __tablename__ = "knowledge_base"
    kb_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    problem_description = Column(Text, nullable=False)
    solution_steps = Column(Text, nullable=False)
    category_id = Column(UUID(as_uuid=True), nullable=True)
    tags = Column(JSON, nullable=True)
    created_by = Column(UUID(as_uuid=True), nullable=False)
    approved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class TicketComment(Base):
    __tablename__ = "ticket_comments"
    comment_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(UUID(as_uuid=True), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    comment_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# ---------------------------------------------------------------------------
# Deterministic UUID generation
# ---------------------------------------------------------------------------
NAMESPACE = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")

def make_uuid(table: str, int_id: int) -> uuid.UUID:
    """Return a deterministic UUID for a given table + integer id."""
    return uuid.uuid5(NAMESPACE, f"{table}:{int_id}")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def parse_datetime(val) -> datetime | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    return datetime.fromisoformat(str(val))

def parse_bool(val) -> bool:
    if val is None:
        return True
    if isinstance(val, bool):
        return val
    return str(val).strip().lower() in ("true", "1", "yes")

def read_sheet(wb, sheet_name: str) -> list[dict]:
    ws = wb[sheet_name]
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []
    headers = [str(h).strip() for h in rows[0]]
    return [dict(zip(headers, row)) for row in rows[1:]]

# ---------------------------------------------------------------------------
# Migration functions (one per table, in FK-dependency order)
# ---------------------------------------------------------------------------

def migrate_users(session: Session, wb) -> dict[int, uuid.UUID]:
    rows = read_sheet(wb, "users")
    id_map: dict[int, uuid.UUID] = {}
    count = 0
    # Placeholder hash for "Password@123" (should match app's hashing if possible)
    # Using a simple string for now if the app is currently undergoing redesign
    placeholder_password = "encrypted_password_placeholder" 
    
    for r in rows:
        int_id = int(r["user_id"])
        uid = make_uuid("users", int_id)
        id_map[int_id] = uid
        
        full_name = str(r["name"]).strip()
        name_parts = full_name.split(" ", 1)
        f_name = name_parts[0]
        l_name = name_parts[1] if len(name_parts) > 1 else "Unknown"
        
        stmt = pg_insert(User.__table__).values(
            id=uid,
            first_name=f_name,
            last_name=l_name,
            email=str(r["email"]),
            role=RoleEnum(r["role"]) if r.get("role") else RoleEnum.USER,
            encrypted_password=placeholder_password,
            is_available=parse_bool(r.get("is_available")),
            created_at=parse_datetime(r.get("created_at")),
            updated_at=parse_datetime(r.get("created_at")),
        ).on_conflict_do_nothing(index_elements=["id"])
        result = session.execute(stmt)
        count += result.rowcount
    session.commit()
    print(f"  users: {count} inserted (of {len(rows)} rows)")
    return id_map


def migrate_categories(session: Session, wb) -> dict[int, uuid.UUID]:
    rows = read_sheet(wb, "categories")
    id_map: dict[int, uuid.UUID] = {}
    count = 0
    for r in rows:
        int_id = int(r["category_id"])
        uid = make_uuid("categories", int_id)
        id_map[int_id] = uid
        stmt = pg_insert(Category.__table__).values(
            category_id=uid,
            name=str(r["name"]),
        ).on_conflict_do_nothing(index_elements=["category_id"])
        result = session.execute(stmt)
        count += result.rowcount
    session.commit()
    print(f"  categories: {count} inserted (of {len(rows)} rows)")
    return id_map


def migrate_sub_categories(session: Session, wb, cat_map: dict[int, uuid.UUID]) -> dict[int, uuid.UUID]:
    rows = read_sheet(wb, "sub_categories")
    id_map: dict[int, uuid.UUID] = {}
    count = 0
    for r in rows:
        int_id = int(r["sub_category_id"])
        uid = make_uuid("sub_categories", int_id)
        id_map[int_id] = uid
        cat_int = int(r["category_id"])
        stmt = pg_insert(SubCategory.__table__).values(
            sub_category_id=uid,
            category_id=cat_map[cat_int],
            name=str(r["name"]),
        ).on_conflict_do_nothing(index_elements=["sub_category_id"])
        result = session.execute(stmt)
        count += result.rowcount
    session.commit()
    print(f"  sub_categories: {count} inserted (of {len(rows)} rows)")
    return id_map


def migrate_tickets(
    session: Session, wb,
    user_map: dict[int, uuid.UUID],
    cat_map: dict[int, uuid.UUID],
    subcat_map: dict[int, uuid.UUID],
) -> dict[int, uuid.UUID]:
    rows = read_sheet(wb, "tickets")
    id_map: dict[int, uuid.UUID] = {}
    count = 0
    for r in rows:
        int_id = int(r["ticket_id"])
        uid = make_uuid("tickets", int_id)
        id_map[int_id] = uid
        cat_id = cat_map.get(int(r["category_id"])) if r.get("category_id") is not None else None
        subcat_id = subcat_map.get(int(r["sub_category_id"])) if r.get("sub_category_id") is not None else None
        created_by = user_map[int(r["created_by"])]
        assigned_to = user_map.get(int(r["assigned_to"])) if r.get("assigned_to") is not None else None
        stmt = pg_insert(Ticket.__table__).values(
            ticket_id=uid,
            title=str(r["title"]),
            description=str(r["description"]),
            status=StatusEnum(r["status"]) if r.get("status") else StatusEnum.NOT_ASSIGNED,
            priority=PriorityEnum(r["priority"]) if r.get("priority") else PriorityEnum.MEDIUM,
            category_id=cat_id,
            sub_category_id=subcat_id,
            created_by=created_by,
            assigned_to=assigned_to,
            created_at=parse_datetime(r.get("created_at")),
            updated_at=parse_datetime(r.get("updated_at")),
            resolved_at=parse_datetime(r.get("resolved_at")),
            sla_due_at=None,
            source=SourceEnum.chatbot,
        ).on_conflict_do_nothing(index_elements=["ticket_id"])
        result = session.execute(stmt)
        count += result.rowcount
    session.commit()
    print(f"  tickets: {count} inserted (of {len(rows)} rows)")
    return id_map


def migrate_knowledge_base(
    session: Session, wb,
    user_map: dict[int, uuid.UUID],
    cat_map: dict[int, uuid.UUID],
) -> dict[int, uuid.UUID]:
    rows = read_sheet(wb, "knowledge_base")
    id_map: dict[int, uuid.UUID] = {}
    count = 0
    for r in rows:
        int_id = int(r["kb_id"])
        uid = make_uuid("knowledge_base", int_id)
        id_map[int_id] = uid
        cat_id = cat_map.get(int(r["category_id"])) if r.get("category_id") is not None else None
        created_by = user_map[int(r["created_by"])]
        # Convert comma-separated tags string → JSON list
        tags_raw = r.get("tags")
        if tags_raw and str(tags_raw).strip():
            tags = [t.strip() for t in str(tags_raw).split(",") if t.strip()]
        else:
            tags = None
        stmt = pg_insert(KnowledgeBase.__table__).values(
            kb_id=uid,
            title=str(r["title"]),
            problem_description=str(r["problem_description"]),
            solution_steps=str(r["solution_steps"]),
            category_id=cat_id,
            tags=tags,
            created_by=created_by,
            approved=parse_bool(r.get("approved")),
            created_at=parse_datetime(r.get("created_at")),
        ).on_conflict_do_nothing(index_elements=["kb_id"])
        result = session.execute(stmt)
        count += result.rowcount
    session.commit()
    print(f"  knowledge_base: {count} inserted (of {len(rows)} rows)")
    return id_map


def migrate_ticket_comments(
    session: Session, wb,
    ticket_map: dict[int, uuid.UUID],
    user_map: dict[int, uuid.UUID],
):
    rows = read_sheet(wb, "ticket_comments")
    count = 0
    for r in rows:
        int_id = int(r["comment_id"])
        uid = make_uuid("ticket_comments", int_id)
        ticket_id = ticket_map[int(r["ticket_id"])]
        user_id = user_map[int(r["user_id"])]
        stmt = pg_insert(TicketComment.__table__).values(
            comment_id=uid,
            ticket_id=ticket_id,
            user_id=user_id,
            comment_text=str(r["comment_text"]),
            created_at=parse_datetime(r.get("created_at")),
        ).on_conflict_do_nothing(index_elements=["comment_id"])
        result = session.execute(stmt)
        count += result.rowcount
    session.commit()
    print(f"  ticket_comments: {count} inserted (of {len(rows)} rows)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print(f"Connecting to: {DATABASE_URL.replace(os.environ['POSTGRES_PASSWORD'], '***')}")
    print(f"Excel file:    {EXCEL_PATH}\n")

    if not EXCEL_PATH.exists():
        print(f"ERROR: Excel file not found at {EXCEL_PATH}")
        sys.exit(1)

    # Create tables if they don't exist
    Base.metadata.create_all(engine)
    print("Tables ensured.\n")

    wb = openpyxl.load_workbook(str(EXCEL_PATH), read_only=True)
    session = SessionLocal()

    try:
        print("Migrating data (in FK-dependency order)...")
        user_map = migrate_users(session, wb)
        cat_map = migrate_categories(session, wb)
        subcat_map = migrate_sub_categories(session, wb, cat_map)
        ticket_map = migrate_tickets(session, wb, user_map, cat_map, subcat_map)
        migrate_knowledge_base(session, wb, user_map, cat_map)
        migrate_ticket_comments(session, wb, ticket_map, user_map)

        # Verification: print actual DB counts
        print("\n--- Verification (DB row counts) ---")
        for tbl in ["users", "categories", "sub_categories", "tickets", "knowledge_base", "ticket_comments"]:
            result = session.execute(text(f"SELECT count(*) FROM {tbl}"))
            print(f"  {tbl}: {result.scalar()}")

        print("\n✅ Migration complete!")

    except Exception as e:
        session.rollback()
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        session.close()
        wb.close()


if __name__ == "__main__":
    main()
