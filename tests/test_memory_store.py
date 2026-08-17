from assistant.memory.store import RECALL_THRESHOLD, RECALL_TOP_K, MemoryStore


def test_save_and_list_facts(tmp_path):
    store = MemoryStore(tmp_path / "memory.db")
    fact_id = store.save_fact("likes tea", "preference")
    assert store.all_facts() == [(fact_id, "likes tea", "preference")]


def test_delete_fact(tmp_path):
    store = MemoryStore(tmp_path / "memory.db")
    fact_id = store.save_fact("temp fact", "general")
    assert store.delete_fact(fact_id) is True
    assert store.delete_fact(fact_id) is False  # already gone
    assert store.all_facts() == []


def test_format_for_prompt_empty(tmp_path):
    store = MemoryStore(tmp_path / "memory.db")
    assert store.format_for_prompt() == ""


def test_format_for_prompt_dumps_everything_below_threshold(tmp_path):
    store = MemoryStore(tmp_path / "memory.db")
    for i in range(5):
        store.save_fact(f"fact {i}", "general")
    prompt = store.format_for_prompt("a query that matches nothing in particular")
    assert len(prompt.splitlines()) == 5


def test_recall_narrows_down_above_threshold(tmp_path):
    store = MemoryStore(tmp_path / "memory.db")
    topics = [
        "hiking", "gardening", "python", "guitar", "chess", "baking",
        "cycling", "painting", "astronomy", "skiing", "poetry",
        "woodworking", "fishing", "yoga", "photography", "chemistry",
        "origami", "sailing", "birdwatching", "coffee", "sculpture",
    ]
    assert len(topics) > RECALL_THRESHOLD
    for t in topics:
        store.save_fact(f"is interested in {t}", "general")

    prompt = store.format_for_prompt("outdoor activities")
    lines = prompt.splitlines()
    assert len(lines) <= RECALL_TOP_K
    assert any("hiking" in line for line in lines)


def test_delete_fact_removes_from_recall(tmp_path):
    store = MemoryStore(tmp_path / "memory.db")
    fact_id = store.save_fact("owns a 3D printer", "personal")
    store.delete_fact(fact_id)
    assert store.recall("3D printer") == []
