import sqlite3

from assistant.reminders.store import ReminderStore


def test_get_returns_full_row_including_google_event_id(tmp_path):
    store = ReminderStore(tmp_path / "reminders.db")
    reminder_id = store.add("buy solder", due_at="2026-09-01T09:00:00", google_event_id="evt-1")
    assert store.get(reminder_id) == (reminder_id, "buy solder", "2026-09-01T09:00:00", False, "evt-1")
    assert store.get(9999) is None


def test_migrates_pre_existing_db_missing_google_event_id_column(tmp_path):
    db_path = tmp_path / "legacy_reminders.db"
    # Simulate a database created before google_event_id existed.
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            due_at TEXT,
            done INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "INSERT INTO reminders (text, created_at) VALUES ('pre-existing', '2026-01-01T00:00:00')"
    )
    conn.commit()
    conn.close()

    store = ReminderStore(db_path)  # should migrate, not raise
    assert store.list()[0][1] == "pre-existing"
    new_id = store.add("new reminder", google_event_id="evt-2")
    assert store.get(new_id)[4] == "evt-2"


def test_set_google_event_id(tmp_path):
    store = ReminderStore(tmp_path / "reminders.db")
    reminder_id = store.add("call the dentist")
    assert store.get(reminder_id)[4] is None

    assert store.set_google_event_id(reminder_id, "evt-99") is True
    assert store.get(reminder_id)[4] == "evt-99"
    assert store.set_google_event_id(9999, "evt-x") is False


def test_add_and_list(tmp_path):
    store = ReminderStore(tmp_path / "reminders.db")
    reminder_id = store.add("buy solder")
    assert store.list() == [(reminder_id, "buy solder", None, False)]


def test_list_excludes_done_by_default(tmp_path):
    store = ReminderStore(tmp_path / "reminders.db")
    reminder_id = store.add("water the plants")
    store.complete(reminder_id)
    assert store.list() == []
    assert store.list(include_done=True) == [(reminder_id, "water the plants", None, True)]


def test_list_orders_by_due_date_then_undated_last(tmp_path):
    store = ReminderStore(tmp_path / "reminders.db")
    undated_id = store.add("someday task")
    later_id = store.add("later task", due_at="2026-12-01T09:00:00")
    sooner_id = store.add("sooner task", due_at="2026-09-01T09:00:00")

    ordered_ids = [r[0] for r in store.list()]
    assert ordered_ids == [sooner_id, later_id, undated_id]


def test_complete_and_delete(tmp_path):
    store = ReminderStore(tmp_path / "reminders.db")
    reminder_id = store.add("temp reminder")

    assert store.complete(reminder_id) is True
    assert store.complete(9999) is False

    assert store.delete(reminder_id) is True
    assert store.delete(reminder_id) is False
    assert store.list(include_done=True) == []
