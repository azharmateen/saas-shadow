"""SQLite storage backend for tasks, boards, wiki pages, and change history."""

import sqlite3
import json
import time
from typing import Optional


_db_path = "./saas_shadow.db"


def set_db_path(path: str):
    global _db_path
    _db_path = path


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS boards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL DEFAULT 'Main Board',
            columns_json TEXT DEFAULT '["Todo","In Progress","Review","Done"]',
            created_at REAL DEFAULT (strftime('%s','now'))
        );

        CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            board_id INTEGER NOT NULL DEFAULT 1,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            column_name TEXT NOT NULL DEFAULT 'Todo',
            position INTEGER DEFAULT 0,
            color TEXT DEFAULT '',
            created_at REAL DEFAULT (strftime('%s','now')),
            updated_at REAL DEFAULT (strftime('%s','now')),
            FOREIGN KEY (board_id) REFERENCES boards(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            assignee TEXT DEFAULT '',
            due_date TEXT DEFAULT '',
            priority TEXT DEFAULT 'medium' CHECK(priority IN ('low','medium','high','urgent')),
            status TEXT DEFAULT 'open' CHECK(status IN ('open','in_progress','review','done','cancelled')),
            tags TEXT DEFAULT '[]',
            created_at REAL DEFAULT (strftime('%s','now')),
            updated_at REAL DEFAULT (strftime('%s','now'))
        );

        CREATE TABLE IF NOT EXISTS wiki_pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            slug TEXT UNIQUE NOT NULL,
            content TEXT DEFAULT '',
            parent_id INTEGER DEFAULT NULL,
            created_at REAL DEFAULT (strftime('%s','now')),
            updated_at REAL DEFAULT (strftime('%s','now')),
            FOREIGN KEY (parent_id) REFERENCES wiki_pages(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS change_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_type TEXT NOT NULL,
            entity_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            data TEXT DEFAULT '{}',
            timestamp REAL DEFAULT (strftime('%s','now'))
        );
    """)

    # Ensure a default board exists
    if not conn.execute("SELECT 1 FROM boards LIMIT 1").fetchone():
        conn.execute("INSERT INTO boards (name) VALUES ('Main Board')")

    conn.commit()
    conn.close()


def _record_change(conn, entity_type: str, entity_id: int, action: str, data: dict = None):
    conn.execute(
        "INSERT INTO change_history (entity_type, entity_id, action, data) VALUES (?,?,?,?)",
        (entity_type, entity_id, action, json.dumps(data or {}))
    )


# === Board / Card CRUD ===

def get_board(board_id: int = 1) -> dict:
    conn = get_db()
    board = conn.execute("SELECT * FROM boards WHERE id=?", (board_id,)).fetchone()
    if not board:
        conn.close()
        return {}
    columns = json.loads(board["columns_json"])
    cards = conn.execute(
        "SELECT * FROM cards WHERE board_id=? ORDER BY position", (board_id,)
    ).fetchall()
    conn.close()

    result = {"id": board["id"], "name": board["name"], "columns": {}}
    for col in columns:
        result["columns"][col] = []
    for card in cards:
        col = card["column_name"]
        if col not in result["columns"]:
            result["columns"][col] = []
        result["columns"][col].append(dict(card))
    return result


def create_card(title: str, column: str = "Todo", board_id: int = 1,
                description: str = "", color: str = "") -> int:
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO cards (board_id, title, description, column_name, color) VALUES (?,?,?,?,?)",
        (board_id, title, description, column, color)
    )
    card_id = cursor.lastrowid
    _record_change(conn, "card", card_id, "created", {"title": title, "column": column})
    conn.commit()
    conn.close()
    return card_id


def move_card(card_id: int, target_column: str, position: int = 0) -> bool:
    conn = get_db()
    conn.execute(
        "UPDATE cards SET column_name=?, position=?, updated_at=strftime('%s','now') WHERE id=?",
        (target_column, position, card_id)
    )
    _record_change(conn, "card", card_id, "moved", {"column": target_column})
    conn.commit()
    conn.close()
    return True


def delete_card(card_id: int) -> bool:
    conn = get_db()
    conn.execute("DELETE FROM cards WHERE id=?", (card_id,))
    _record_change(conn, "card", card_id, "deleted", {})
    conn.commit()
    conn.close()
    return True


def update_card(card_id: int, **kwargs) -> bool:
    conn = get_db()
    allowed = {"title", "description", "column_name", "color", "position"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        conn.close()
        return False
    set_clause = ", ".join(f"{k}=?" for k in updates)
    values = list(updates.values()) + [card_id]
    conn.execute(
        f"UPDATE cards SET {set_clause}, updated_at=strftime('%s','now') WHERE id=?",
        values
    )
    _record_change(conn, "card", card_id, "updated", updates)
    conn.commit()
    conn.close()
    return True


# === Task CRUD ===

def get_tasks(status: str = None, priority: str = None,
              assignee: str = None, sort_by: str = "created_at") -> list:
    conn = get_db()
    query = "SELECT * FROM tasks WHERE 1=1"
    params = []
    if status:
        query += " AND status=?"
        params.append(status)
    if priority:
        query += " AND priority=?"
        params.append(priority)
    if assignee:
        query += " AND assignee=?"
        params.append(assignee)

    allowed_sorts = {"created_at", "updated_at", "due_date", "priority", "title"}
    if sort_by in allowed_sorts:
        query += f" ORDER BY {sort_by} DESC"
    else:
        query += " ORDER BY created_at DESC"

    rows = conn.execute(query, params).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["tags"] = json.loads(d["tags"]) if d["tags"] else []
        result.append(d)
    return result


def get_task(task_id: int) -> Optional[dict]:
    conn = get_db()
    row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    d["tags"] = json.loads(d["tags"]) if d["tags"] else []
    return d


def create_task(title: str, description: str = "", assignee: str = "",
                due_date: str = "", priority: str = "medium",
                status: str = "open", tags: list = None) -> int:
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO tasks (title, description, assignee, due_date, priority, status, tags) VALUES (?,?,?,?,?,?,?)",
        (title, description, assignee, due_date, priority, status, json.dumps(tags or []))
    )
    task_id = cursor.lastrowid
    _record_change(conn, "task", task_id, "created", {"title": title})
    conn.commit()
    conn.close()
    return task_id


def update_task(task_id: int, **kwargs) -> bool:
    conn = get_db()
    allowed = {"title", "description", "assignee", "due_date", "priority", "status", "tags"}
    updates = {}
    for k, v in kwargs.items():
        if k in allowed:
            updates[k] = json.dumps(v) if k == "tags" else v
    if not updates:
        conn.close()
        return False
    set_clause = ", ".join(f"{k}=?" for k in updates)
    values = list(updates.values()) + [task_id]
    conn.execute(
        f"UPDATE tasks SET {set_clause}, updated_at=strftime('%s','now') WHERE id=?", values
    )
    _record_change(conn, "task", task_id, "updated", kwargs)
    conn.commit()
    conn.close()
    return True


def delete_task(task_id: int) -> bool:
    conn = get_db()
    conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    _record_change(conn, "task", task_id, "deleted", {})
    conn.commit()
    conn.close()
    return True


# === Wiki CRUD ===

def get_wiki_pages(parent_id: int = None) -> list:
    conn = get_db()
    if parent_id is not None:
        rows = conn.execute(
            "SELECT id, title, slug, parent_id, updated_at FROM wiki_pages WHERE parent_id=? ORDER BY title",
            (parent_id,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, title, slug, parent_id, updated_at FROM wiki_pages ORDER BY title"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_wiki_page(slug: str) -> Optional[dict]:
    conn = get_db()
    row = conn.execute("SELECT * FROM wiki_pages WHERE slug=?", (slug,)).fetchone()
    conn.close()
    return dict(row) if row else None


def create_wiki_page(title: str, content: str = "", parent_id: int = None) -> dict:
    import re
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    conn = get_db()
    # Ensure unique slug
    existing = conn.execute("SELECT 1 FROM wiki_pages WHERE slug=?", (slug,)).fetchone()
    if existing:
        slug = f"{slug}-{int(time.time()) % 10000}"
    cursor = conn.execute(
        "INSERT INTO wiki_pages (title, slug, content, parent_id) VALUES (?,?,?,?)",
        (title, slug, content, parent_id)
    )
    page_id = cursor.lastrowid
    _record_change(conn, "wiki", page_id, "created", {"title": title, "slug": slug})
    conn.commit()
    conn.close()
    return {"id": page_id, "slug": slug}


def update_wiki_page(slug: str, title: str = None, content: str = None) -> bool:
    conn = get_db()
    page = conn.execute("SELECT id FROM wiki_pages WHERE slug=?", (slug,)).fetchone()
    if not page:
        conn.close()
        return False
    updates = {}
    if title is not None:
        updates["title"] = title
    if content is not None:
        updates["content"] = content
    if not updates:
        conn.close()
        return False
    set_clause = ", ".join(f"{k}=?" for k in updates)
    values = list(updates.values()) + [slug]
    conn.execute(
        f"UPDATE wiki_pages SET {set_clause}, updated_at=strftime('%s','now') WHERE slug=?", values
    )
    _record_change(conn, "wiki", page["id"], "updated", updates)
    conn.commit()
    conn.close()
    return True


def delete_wiki_page(slug: str) -> bool:
    conn = get_db()
    page = conn.execute("SELECT id FROM wiki_pages WHERE slug=?", (slug,)).fetchone()
    if not page:
        conn.close()
        return False
    conn.execute("DELETE FROM wiki_pages WHERE slug=?", (slug,))
    _record_change(conn, "wiki", page["id"], "deleted", {})
    conn.commit()
    conn.close()
    return True


def search_wiki(query: str) -> list:
    conn = get_db()
    rows = conn.execute(
        "SELECT id, title, slug, parent_id FROM wiki_pages WHERE title LIKE ? OR content LIKE ? ORDER BY updated_at DESC",
        (f"%{query}%", f"%{query}%")
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


class Storage:
    """Convenience class wrapping the module-level storage functions.

    Usage:
        s = Storage("/tmp/test.db")
        task_id = s.create_task(title="Test", description="Desc", priority="high")
        tasks = s.list_tasks()
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        set_db_path(db_path)
        init_db()

    # === Tasks ===
    def create_task(self, **kwargs) -> int:
        return create_task(**kwargs)

    def get_task(self, task_id: int) -> Optional[dict]:
        return get_task(task_id)

    def list_tasks(self, **kwargs) -> list:
        return get_tasks(**kwargs)

    def update_task(self, task_id: int, **kwargs) -> bool:
        return update_task(task_id, **kwargs)

    def delete_task(self, task_id: int) -> bool:
        return delete_task(task_id)

    # === Kanban ===
    def create_card(self, **kwargs) -> int:
        return create_card(**kwargs)

    def get_board(self, board_id: int = 1) -> dict:
        return get_board(board_id)

    def move_card(self, card_id: int, target_column: str, position: int = 0) -> bool:
        return move_card(card_id, target_column, position)

    def update_card(self, card_id: int, **kwargs) -> bool:
        return update_card(card_id, **kwargs)

    def delete_card(self, card_id: int) -> bool:
        return delete_card(card_id)

    # === Wiki ===
    def create_wiki_page(self, **kwargs) -> dict:
        return create_wiki_page(**kwargs)

    def get_wiki_page(self, slug: str) -> Optional[dict]:
        return get_wiki_page(slug)

    def list_wiki_pages(self, parent_id: int = None) -> list:
        return get_wiki_pages(parent_id)

    def update_wiki_page(self, slug: str, **kwargs) -> bool:
        return update_wiki_page(slug, **kwargs)

    def delete_wiki_page(self, slug: str) -> bool:
        return delete_wiki_page(slug)

    def search_wiki(self, query: str) -> list:
        return search_wiki(query)
