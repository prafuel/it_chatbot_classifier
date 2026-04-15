"""
CRUD operations for PostgreSQL — ChatSession table.
"""

import uuid
import logging
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.common.models import ChatSession

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CREATE
# ---------------------------------------------------------------------------

def create_chat(db: Session, data: dict) -> ChatSession:
    """
    Insert a new chat session row.

    Expected keys in `data`:
        ip, country, country_code, region, region_code, city, zip,
        lat, lon, timezone, isp, organization, asn, query, response
    """
    chat = ChatSession(**data)
    db.add(chat)
    db.commit()
    db.refresh(chat)
    logger.info(f"Chat session saved: id={chat.id}")
    return chat


# ---------------------------------------------------------------------------
# READ
# ---------------------------------------------------------------------------

def get_all_chats(db: Session, page: int = 1, batch_size: int = 50) -> list[ChatSession]:
    """Return paginated list of all chat sessions using page and batch_size, newest first."""
    skip = (page - 1) * batch_size
    return (
        db.query(ChatSession)
        .order_by(ChatSession.created_at.desc())
        .offset(skip)
        .limit(batch_size)
        .all()
    )


def get_chats_grouped_by_ip(db: Session, page: int = 1, batch_size: int = 50) -> tuple[list[ChatSession], int]:
    """
    Return a list of unique IPs, each represented by their most recent ChatSession record.
    The response includes ALL historical chats for those IPs.
    Returns (sessions, total_unique_ips).
    """
    # 1. Get total number of unique IPs
    total_ips = db.query(ChatSession.ip).distinct().count()

    # 2. Get unique IPs ordered by their latest chat activity
    # Subquery to find the latest created_at for each IP
    latest_per_ip = (
        db.query(ChatSession.ip, func.max(ChatSession.created_at).label("latest_at"))
        .group_by(ChatSession.ip)
        .order_by(text("latest_at DESC"))
        .offset((page - 1) * batch_size)
        .limit(batch_size)
        .subquery()
    )

    # 3. Join back to get the full session record for those latest timestamps
    # This provides the metadata (country, city, etc.) for the latest interaction
    sessions = (
        db.query(ChatSession)
        .join(latest_per_ip, (ChatSession.ip == latest_per_ip.c.ip) & (ChatSession.created_at == latest_per_ip.c.latest_at))
        .all()
    )

    return sessions, total_ips


def get_chat_by_id(db: Session, chat_id: uuid.UUID) -> ChatSession | None:
    """Return a single chat session by its UUID, or None if not found."""
    return db.query(ChatSession).filter(ChatSession.id == chat_id).first()


# Columns that are exposed for filtering (exclude id / created_at)
_FILTERABLE_COLUMNS: list[str] = [
    col.name for col in ChatSession.__table__.columns
    if col.name not in ("id", "created_at")
]


def get_filterable_columns() -> list[str]:
    """Return the list of ChatSession column names available for filtering."""
    return list(_FILTERABLE_COLUMNS)


def get_distinct_column_values(db: Session, column_name: str) -> list[str]:
    """
    Return sorted, distinct non-null values for a given column.
    Raises ValueError if the column name is not filterable.
    """
    if column_name not in _FILTERABLE_COLUMNS:
        raise ValueError(f"Invalid column: {column_name}")

    col = getattr(ChatSession, column_name)
    rows = (
        db.query(col)
        .filter(col.isnot(None))
        .distinct()
        .all()
    )
    return sorted(str(r[0]) for r in rows)


def get_chats_by_filter(
    db: Session,
    column_name: str,
    value: str,
    skip: int = 0,
    limit: int = 50,
) -> list[ChatSession]:
    """
    Return paginated chat sessions filtered by *column_name == value*.
    Uses case-insensitive ILIKE for string columns.
    Raises ValueError if the column name is not filterable.
    """
    if column_name not in _FILTERABLE_COLUMNS:
        raise ValueError(f"Invalid column: {column_name}")

    col = getattr(ChatSession, column_name)

    # Use ilike for string/text columns, exact match for numeric
    if hasattr(col.type, "length") or str(col.type) == "TEXT":
        condition = col.ilike(value)
    else:
        condition = col == value

    return (
        db.query(ChatSession)
        .filter(condition)
        .order_by(ChatSession.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_chats_by_filters(
    db: Session,
    filters: dict,
    sort_by: str = None,
    sort_type: str = "desc",
) -> tuple[list[ChatSession], int]:
    """
    Return all chat sessions matching ALL key/value pairs in *filters*, with optional sorting.
    Returns (chats, total_count).

    Each key must be a valid filterable column name; raises ValueError otherwise.
    String/text columns are matched case-insensitively (ILIKE).
    Multiple filters are combined with AND.
    An empty *filters* dict returns all chats (no conditions applied).
    """
    # Validate every requested column up-front
    invalid = [k for k in filters if k not in _FILTERABLE_COLUMNS]
    if invalid:
        raise ValueError(f"Invalid column(s): {', '.join(invalid)}")

    query = db.query(ChatSession)

    for column_name, value in filters.items():
        col = getattr(ChatSession, column_name)
        # Use ILIKE for string/text columns, exact match for numeric
        if hasattr(col.property.columns[0].type, "length") or \
                str(col.property.columns[0].type) in ("TEXT", "VARCHAR"):
            query = query.filter(col.ilike(value))
        else:
            query = query.filter(col == value)

    # Get total count before applying limit/offset
    total_count = query.count()

    # Sorting
    if sort_by:
        if sort_by not in [col.name for col in ChatSession.__table__.columns]:
             raise ValueError(f"Invalid sort column: {sort_by}")
        
        sort_col = getattr(ChatSession, sort_by)
        if sort_type.lower() == "desc":
            query = query.order_by(sort_col.desc())
        else:
            query = query.order_by(sort_col.asc())
    else:
        # Default sort
        query = query.order_by(ChatSession.created_at.desc())

    chats = query.all()
    return chats, total_count


def get_grouped_chats_by_filters(
    db: Session,
    filters: dict,
    sort_by: str = None,
    sort_type: str = "desc",
) -> tuple[list[ChatSession], int]:
    """
    Return unique IPs that match the given filters, each represented by their latest session.
    Similar to get_chats_grouped_by_ip but with filtering support.
    """
    # 1. Validate columns
    invalid = [k for k in filters if k not in _FILTERABLE_COLUMNS]
    if invalid:
        raise ValueError(f"Invalid column(s): {', '.join(invalid)}")

    # 2. Base query for filtered sessions
    base_query = db.query(ChatSession)
    for column_name, value in filters.items():
        col = getattr(ChatSession, column_name)
        if hasattr(col.property.columns[0].type, "length") or \
                str(col.property.columns[0].type) in ("TEXT", "VARCHAR"):
            base_query = base_query.filter(col.ilike(value))
        else:
            base_query = base_query.filter(col == value)

    # 3. Get distinct IPs and their count
    # We use a subquery to find IPs that have at least one session matching the filters
    matching_ips_subquery = base_query.with_entities(ChatSession.ip).distinct().subquery()
    total_ips = db.query(func.count(matching_ips_subquery.c.ip)).scalar()

    # 4. Find the latest session per unique filtered IP
    latest_per_ip = (
        db.query(ChatSession.ip, func.max(ChatSession.created_at).label("latest_at"))
        .filter(ChatSession.ip.in_(db.query(matching_ips_subquery.c.ip)))
        .group_by(ChatSession.ip)
        .subquery()
    )

    # 5. Join back to get full records and apply sorting
    query = (
        db.query(ChatSession)
        .join(latest_per_ip, (ChatSession.ip == latest_per_ip.c.ip) & (ChatSession.created_at == latest_per_ip.c.latest_at))
    )

    if sort_by:
        if sort_by not in [col.name for col in ChatSession.__table__.columns]:
             raise ValueError(f"Invalid sort column: {sort_by}")
        sort_col = getattr(ChatSession, sort_by)
        query = query.order_by(sort_col.desc() if sort_type.lower() == "desc" else sort_col.asc())
    else:
        query = query.order_by(ChatSession.created_at.desc())

    sessions = query.all()
    return sessions, total_ips


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------

def delete_chat(db: Session, chat_id: uuid.UUID) -> bool:
    """
    Delete a chat session by UUID.
    Returns True if deleted, False if not found.
    """
    chat = get_chat_by_id(db, chat_id)
    if not chat:
        return False
    db.delete(chat)
    db.commit()
    logger.info(f"Chat session deleted: id={chat_id}")
    return True