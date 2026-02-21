"""Repository for activity_logs table."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.postgresql import Base

logger = logging.getLogger(__name__)


class ActivityLogRepository:
    """CRUD for activity_logs table using raw SQL for SQLite test compatibility."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert an activity log row."""
        row_id = data.get("id") or str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        import json

        metadata_val = json.dumps(data.get("metadata_json")) if data.get("metadata_json") else None
        entity_id_val = str(data["entity_id"]) if data.get("entity_id") else None
        user_id_val = str(data["user_id"]) if data.get("user_id") else None

        await self.session.execute(
            text(
                "INSERT INTO activity_logs "
                "(id, event_type, entity_type, entity_id, user_id, action, "
                "title, description, severity, metadata_json, created_at) "
                "VALUES (:id, :event_type, :entity_type, :entity_id, :user_id, :action, "
                ":title, :description, :severity, :metadata_json, :created_at)"
            ),
            {
                "id": row_id,
                "event_type": data["event_type"],
                "entity_type": data["entity_type"],
                "entity_id": entity_id_val,
                "user_id": user_id_val,
                "action": data["action"],
                "title": data["title"],
                "description": data.get("description"),
                "severity": data.get("severity", "info"),
                "metadata_json": metadata_val,
                "created_at": now,
            },
        )
        await self.session.commit()

        return {
            "id": row_id,
            "event_type": data["event_type"],
            "entity_type": data["entity_type"],
            "entity_id": entity_id_val,
            "user_id": user_id_val,
            "action": data["action"],
            "title": data["title"],
            "description": data.get("description"),
            "severity": data.get("severity", "info"),
            "metadata_json": data.get("metadata_json"),
            "created_at": now,
        }

    async def get_feed(
        self,
        limit: int = 50,
        offset: int = 0,
        event_type: Optional[str] = None,
        entity_type: Optional[str] = None,
        severity: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Paginated activity feed, newest first."""
        import json

        where_clauses: List[str] = []
        params: Dict[str, Any] = {"limit": limit, "offset": offset}

        if event_type:
            where_clauses.append("event_type = :event_type")
            params["event_type"] = event_type
        if entity_type:
            where_clauses.append("entity_type = :entity_type")
            params["entity_type"] = entity_type
        if severity:
            where_clauses.append("severity = :severity")
            params["severity"] = severity

        where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        # Count
        count_result = await self.session.execute(
            text(f"SELECT COUNT(*) FROM activity_logs{where_sql}"), params
        )
        total = count_result.scalar() or 0

        # Items
        rows_result = await self.session.execute(
            text(
                f"SELECT id, event_type, entity_type, entity_id, user_id, action, "
                f"title, description, severity, metadata_json, created_at "
                f"FROM activity_logs{where_sql} "
                f"ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
            ),
            params,
        )
        rows = rows_result.fetchall()

        items = []
        for row in rows:
            meta = row[9]
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except (json.JSONDecodeError, TypeError):
                    meta = None

            items.append({
                "id": str(row[0]),
                "event_type": row[1],
                "entity_type": row[2],
                "entity_id": str(row[3]) if row[3] else None,
                "user_id": str(row[4]) if row[4] else None,
                "action": row[5],
                "title": row[6],
                "description": row[7],
                "severity": row[8],
                "metadata_json": meta,
                "created_at": row[10],
            })

        return {"items": items, "total": total, "limit": limit, "offset": offset}

    async def get_by_entity(
        self,
        entity_type: str,
        entity_id: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get activity logs for a specific entity."""
        import json

        result = await self.session.execute(
            text(
                "SELECT id, event_type, entity_type, entity_id, user_id, action, "
                "title, description, severity, metadata_json, created_at "
                "FROM activity_logs "
                "WHERE entity_type = :entity_type AND entity_id = :entity_id "
                "ORDER BY created_at DESC LIMIT :limit"
            ),
            {"entity_type": entity_type, "entity_id": entity_id, "limit": limit},
        )
        rows = result.fetchall()

        items = []
        for row in rows:
            meta = row[9]
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except (json.JSONDecodeError, TypeError):
                    meta = None

            items.append({
                "id": str(row[0]),
                "event_type": row[1],
                "entity_type": row[2],
                "entity_id": str(row[3]) if row[3] else None,
                "user_id": str(row[4]) if row[4] else None,
                "action": row[5],
                "title": row[6],
                "description": row[7],
                "severity": row[8],
                "metadata_json": meta,
                "created_at": row[10],
            })

        return items
