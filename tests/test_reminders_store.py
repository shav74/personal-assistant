from assistant.reminders.store import ReminderStore


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
