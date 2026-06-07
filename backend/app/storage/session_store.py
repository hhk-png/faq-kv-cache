"""Session store for conversation persistence (file-based, per-user)."""
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from filelock import FileLock

from app.core.config import settings

BASE_DIR = Path(settings.data_dir) / "sessions"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _new_id() -> str:
    return "session_" + uuid.uuid4().hex[:8]


def _user_dir(user_id: str) -> Path:
    return BASE_DIR / user_id


def _index_file(user_id: str) -> Path:
    return _user_dir(user_id) / "index.json"


def _lock_file(user_id: str) -> Path:
    return _user_dir(user_id) / "index.lock"


def _msg_file(user_id: str, session_id: str) -> Path:
    return _user_dir(user_id) / f"{session_id}.json"


def _load_index(user_id: str) -> list[dict]:
    idx_file = _index_file(user_id)
    idx_file.parent.mkdir(parents=True, exist_ok=True)
    if not idx_file.exists():
        idx_file.write_text("[]", encoding="utf-8")
    with FileLock(str(_lock_file(user_id))):
        raw = idx_file.read_text(encoding="utf-8")
        return json.loads(raw) if raw.strip() else []


def _save_index(user_id: str, index: list[dict]):
    idx_file = _index_file(user_id)
    idx_file.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(str(_lock_file(user_id))):
        idx_file.write_text(
            json.dumps(index, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def list_sessions(user_id: str) -> list[dict]:
    """List sessions for a specific user (isolated per user)."""
    index = _load_index(user_id)
    index.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return index


def create_session(user_id: str, title: str = "新对话") -> dict:
    """Create a new session for a specific user."""
    session_id = _new_id()
    now = _now()
    session = {
        "id": session_id,
        "title": title,
        "created_at": now,
        "updated_at": now,
    }
    index = _load_index(user_id)
    index.append(session)
    _save_index(user_id, index)
    msg_f = _msg_file(user_id, session_id)
    msg_f.parent.mkdir(parents=True, exist_ok=True)
    msg_f.write_text("[]", encoding="utf-8")
    return session


def get_session(user_id: str, session_id: str) -> Optional[dict]:
    """Get session metadata for a specific user."""
    index = _load_index(user_id)
    for s in index:
        if s["id"] == session_id:
            return s
    return None


def get_messages(user_id: str, session_id: str) -> list[dict]:
    """Get all messages for a session of a specific user."""
    msg_f = _msg_file(user_id, session_id)
    if not msg_f.exists():
        return []
    raw = msg_f.read_text(encoding="utf-8")
    return json.loads(raw) if raw.strip() else []


def save_messages(user_id: str, session_id: str, messages: list[dict]):
    """Save messages for a session of a specific user."""
    msg_f = _msg_file(user_id, session_id)
    msg_f.parent.mkdir(parents=True, exist_ok=True)
    msg_f.write_text(
        json.dumps(messages, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    index = _load_index(user_id)
    for s in index:
        if s["id"] == session_id:
            s["updated_at"] = _now()
            if s["title"] == "新对话" and messages:
                for msg in messages:
                    if msg["role"] == "user":
                        s["title"] = msg["content"][:30]
                        break
            break
    _save_index(user_id, index)


def append_messages(user_id: str, session_id: str, new_messages: list[dict]):
    """Append messages to a session of a specific user."""
    existing = get_messages(user_id, session_id)
    existing.extend(new_messages)
    save_messages(user_id, session_id, existing)


def update_session_title(user_id: str, session_id: str, title: str) -> bool:
    """Update session title for a specific user."""
    index = _load_index(user_id)
    for s in index:
        if s["id"] == session_id:
            s["title"] = title
            s["updated_at"] = _now()
            _save_index(user_id, index)
            return True
    return False


def delete_session(user_id: str, session_id: str) -> bool:
    """Delete a session and its messages for a specific user."""
    index = _load_index(user_id)
    new_index = [s for s in index if s["id"] != session_id]
    if len(new_index) == len(index):
        return False
    _save_index(user_id, new_index)
    msg_f = _msg_file(user_id, session_id)
    if msg_f.exists():
        msg_f.unlink()
    return True
