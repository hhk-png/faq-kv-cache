"""Simple user store - number-based login, auto-create."""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from filelock import FileLock

from app.core.config import settings

USERS_FILE = Path(settings.data_dir) / "users.json"
LOCK_FILE = Path(settings.data_dir) / "users.lock"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _ensure_file():
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not USERS_FILE.exists():
        USERS_FILE.write_text("[]", encoding="utf-8")


def _read() -> list[dict]:
    _ensure_file()
    with FileLock(str(LOCK_FILE)):
        raw = USERS_FILE.read_text(encoding="utf-8")
        return json.loads(raw) if raw.strip() else []


def _write(data: list[dict]):
    _ensure_file()
    with FileLock(str(LOCK_FILE)):
        USERS_FILE.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def login(user_id: str) -> dict:
    """Login with a user ID. Creates the user if not exists."""
    users = _read()
    for u in users:
        if u["id"] == user_id:
            return u
    # Auto-create
    now = _now()
    user = {"id": user_id, "created_at": now}
    users.append(user)
    _write(users)
    return user
