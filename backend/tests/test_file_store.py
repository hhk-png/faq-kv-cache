import pytest
import os

from app.core.config import settings
from app.storage.file_store import JsonFileStore


class TestJsonFileStore:
    def _temp_path(self, name: str) -> str:
        return os.path.join(os.path.dirname(settings.faq_file), name)

    def test_init_creates_file(self):
        path = self._temp_path("test_init.json")
        store = JsonFileStore(path)
        assert os.path.exists(path)
        assert store.read_all() == []
        os.remove(path)

    def test_insert_and_read(self):
        path = self._temp_path("test_crud.json")
        store = JsonFileStore(path)
        item = {"id": "1", "name": "test"}
        store.insert(item)
        assert len(store.read_all()) == 1
        assert store.read_all()[0]["name"] == "test"
        os.remove(path)

    def test_find_by_id(self):
        path = self._temp_path("test_find.json")
        store = JsonFileStore(path)
        store.insert({"id": "a1", "value": 10})
        store.insert({"id": "b2", "value": 20})
        assert store.find_by_id("a1")["value"] == 10
        assert store.find_by_id("b2")["value"] == 20
        assert store.find_by_id("c3") is None
        os.remove(path)

    def test_update(self):
        path = self._temp_path("test_update.json")
        store = JsonFileStore(path)
        store.insert({"id": "1", "name": "old"})
        updated = store.update("1", {"name": "new"})
        assert updated["name"] == "new"
        assert store.find_by_id("1")["name"] == "new"
        os.remove(path)

    def test_delete(self):
        path = self._temp_path("test_delete.json")
        store = JsonFileStore(path)
        store.insert({"id": "1"})
        store.insert({"id": "2"})
        assert store.delete("1") is True
        assert store.count() == 1
        assert store.delete("3") is False
        os.remove(path)

    def test_count(self):
        path = self._temp_path("test_count.json")
        store = JsonFileStore(path)
        assert store.count() == 0
        store.insert({"id": "1"})
        store.insert({"id": "2"})
        assert store.count() == 2
        os.remove(path)
