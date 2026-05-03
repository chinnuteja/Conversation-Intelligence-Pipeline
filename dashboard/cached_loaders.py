"""
Streamlit cache_data loaders kept in a small module so inspect.getsource() succeeds.

Python 3.13 + Streamlit can raise tokenize.TokenError when hashing cache keys for
functions defined in the same file as very large string literals (e.g. CSS).
"""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"
DATA_DIR = ROOT / "data"


def _output_cache_signature() -> tuple[float, float, float]:
    paths = (
        OUTPUT_DIR / "report.json",
        OUTPUT_DIR / "all_evaluations.json",
        OUTPUT_DIR / "clusters.json",
    )

    def _mtime(p: Path) -> float:
        return p.stat().st_mtime if p.is_file() else 0.0

    return (_mtime(paths[0]), _mtime(paths[1]), _mtime(paths[2]))


@st.cache_data(show_spinner=False)
def load_report(_output_sig: tuple[float, float, float]):
    path = OUTPUT_DIR / "report.json"
    if not path.exists():
        st.error(f"Missing {path}. Run `python pipeline.py` first.")
        st.stop()
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data(show_spinner=False)
def load_all_evaluations(_output_sig: tuple[float, float, float]):
    path = OUTPUT_DIR / "all_evaluations.json"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def load_messages_index():
    path = DATA_DIR / "messages.json"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    idx: dict[str, list[dict]] = {}
    for seq, m in enumerate(raw):
        cid = str(m.get("conversationId", ""))
        idx.setdefault(cid, []).append(
            {
                "sender": m.get("sender"),
                "text": (m.get("text") or "")[:8000],
                "timestamp": str(m.get("timestamp", "")),
                "messageType": m.get("messageType", "text"),
                "_id": str(m.get("_id", "")),
                "_seq": seq,
            }
        )
    for cid in idx:
        idx[cid].sort(key=lambda x: (x["timestamp"], x["_id"], x["_seq"]))
    return idx
