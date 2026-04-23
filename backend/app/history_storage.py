from __future__ import annotations

import json
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
HISTORY_FILE = DATA_DIR / "generations_history.json"
MAX_HISTORY_ITEMS = int(os.getenv("MAX_HISTORY_ITEMS", "200"))

_LOCK = threading.Lock()


def _ensure_storage() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not HISTORY_FILE.exists():
        HISTORY_FILE.write_text("[]", encoding="utf-8")


def _read_all() -> list[dict[str, Any]]:
    _ensure_storage()
    raw = HISTORY_FILE.read_text(encoding="utf-8").strip()
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


def _write_all(items: list[dict[str, Any]]) -> None:
    _ensure_storage()
    HISTORY_FILE.write_text(
        json.dumps(items, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _extract_metadata(upper_graph: dict[str, Any], generation_time: int) -> dict[str, Any]:
    clusters = upper_graph.get("clusters", []) if isinstance(upper_graph, dict) else []
    if not isinstance(clusters, list):
        clusters = []

    high_demand_count = 0
    commercial_count = 0
    parent_themes: set[str] = set()

    for cluster in clusters:
        if not isinstance(cluster, dict):
            continue
        if cluster.get("demand_level") == "High":
            high_demand_count += 1
        if cluster.get("gpt_intent") == "commercial":
            commercial_count += 1
        parent_theme = cluster.get("parent_theme")
        if isinstance(parent_theme, str) and parent_theme.strip():
            parent_themes.add(parent_theme.strip())

    return {
        "generationTime": int(generation_time),
        "clusterCount": len(clusters),
        "highDemandCount": high_demand_count,
        "commercialCount": commercial_count,
        "parentThemes": sorted(parent_themes),
    }


def list_generations() -> list[dict[str, Any]]:
    with _LOCK:
        items = _read_all()
        items.sort(key=lambda item: int(item.get("timestamp", 0)), reverse=True)
        return items


def get_generation(generation_id: str) -> dict[str, Any] | None:
    with _LOCK:
        for item in _read_all():
            if item.get("id") == generation_id:
                return item
    return None


def save_generation(
    *,
    topic: str,
    intents: list[str],
    locale: str,
    upper_graph: dict[str, Any],
    generation_time: int,
) -> dict[str, Any]:
    with _LOCK:
        items = _read_all()
        for item in items:
            item["isActive"] = False

        generation_id = f"gen_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
        history_item = {
            "id": generation_id,
            "timestamp": int(time.time() * 1000),
            "topic": topic,
            "intents": intents,
            "locale": locale,
            "upperGraph": upper_graph,
            "metadata": _extract_metadata(upper_graph, generation_time),
            "version": 1,
            "isActive": True,
        }

        items.insert(0, history_item)
        if len(items) > MAX_HISTORY_ITEMS:
            items = items[:MAX_HISTORY_ITEMS]

        _write_all(items)
        return history_item


def restore_generation(generation_id: str) -> dict[str, Any] | None:
    with _LOCK:
        items = _read_all()
        target: dict[str, Any] | None = None

        for item in items:
            is_target = item.get("id") == generation_id
            item["isActive"] = is_target
            if is_target:
                target = item

        if target is None:
            return None

        _write_all(items)
        return target


def delete_generation(generation_id: str) -> bool:
    with _LOCK:
        items = _read_all()
        filtered = [item for item in items if item.get("id") != generation_id]
        if len(filtered) == len(items):
            return False

        if filtered and not any(bool(item.get("isActive")) for item in filtered):
            filtered[0]["isActive"] = True

        _write_all(filtered)
        return True
