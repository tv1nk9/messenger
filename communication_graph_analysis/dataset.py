"""Загрузка и экспорт логов переписки (CSV-формат исследования).

Формат CSV-файла:
    sender,recipient,chat_id,timestamp,event_type,length_chars
    recipient пуст для групповых сообщений; timestamp в ISO 8601.
"""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .models import EVENT_DIRECT, MessageRecord


def load_messages_csv(path: str | Path) -> list[MessageRecord]:
    msgs: list[MessageRecord] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {"sender", "recipient", "chat_id", "timestamp"}
        if not required.issubset(set(reader.fieldnames or [])):
            raise ValueError(
                f"CSV {path}: обязательные колонки {sorted(required)}, "
                f"найдено {reader.fieldnames}"
            )
        for row in reader:
            ts_raw = row["timestamp"].strip()
            try:
                ts = datetime.fromisoformat(ts_raw)
            except ValueError:
                ts = datetime.strptime(ts_raw, "%Y-%m-%d %H:%M:%S")
            msgs.append(
                MessageRecord(
                    sender=row["sender"].strip(),
                    recipient=(row["recipient"].strip() or None),
                    chat_id=row["chat_id"].strip(),
                    timestamp=ts,
                    event_type=(row.get("event_type") or EVENT_DIRECT).strip(),
                    length_chars=int(row.get("length_chars") or 0),
                )
            )
    return msgs


def save_messages_csv(messages: Iterable[MessageRecord], path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            ["sender", "recipient", "chat_id", "timestamp", "event_type", "length_chars"]
        )
        for m in messages:
            w.writerow(
                [
                    m.sender,
                    m.recipient or "",
                    m.chat_id,
                    m.timestamp.isoformat(sep=" "),
                    m.event_type,
                    m.length_chars,
                ]
            )
