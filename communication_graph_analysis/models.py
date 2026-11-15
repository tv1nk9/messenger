"""Графовая модель коммуникаций (задача 2 исследования).

Описание формальной модели:

    G = (V, E, W, T)
    V — множество узлов (сотрудников / аккаунтов мессенджера);
    E ⊆ V × V — множество НАПРАВЛЕННЫХ рёбер: ребро (u, v) существует, если
        пользователь u отправил хотя бы одно сообщение пользователю v;
    W: E → R+ — весовая функция (количество сообщений между парой за окно);
    T: E → {t_1..t_n} — временные атрибуты рёбер (первое/последнее время
        взаимодействия, посекундная активность).

Различаются три типа коммуникационных событий:
    * direct      — личное сообщение u → v;
    * group       — сообщение u в групповой чат (транслируется в клику
                    участников группы, кроме автора);
    * reply       — ответ u на сообщение v (усиливает ребро u→v:
                    учитывается как направленный отклик, признак диалога).

Изоляция определяется математическими критериями, реализованными в
модуле isolation_detector.py.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, Iterator, Mapping

import networkx as nx

# Типы событий, поддерживаемые моделью.
EVENT_DIRECT = "direct"
EVENT_GROUP = "group"
EVENT_REPLY = "reply"
VALID_EVENT_TYPES = {EVENT_DIRECT, EVENT_GROUP, EVENT_REPLY}


@dataclass(frozen=True)
class MessageRecord:
    """Атомарное событие обмена сообщениями (строка лога мессенджера)."""

    sender: str
    recipient: str | None          # None для групповых сообщений
    chat_id: str                   # идентификатор диалога/группы
    timestamp: datetime
    event_type: str = EVENT_DIRECT
    length_chars: int = 0

    def __post_init__(self) -> None:
        if self.event_type not in VALID_EVENT_TYPES:
            raise ValueError(
                f"Недопустимый тип события: {self.event_type!r}. "
                f"Ожидается один из {sorted(VALID_EVENT_TYPES)}"
            )
        if self.event_type == EVENT_DIRECT and self.recipient is None:
            raise ValueError("Для direct-сообщения обязателен recipient")


@dataclass
class CommunicationEdge:
    """Агрегированное направленное ребро u → v."""

    source: str
    target: str
    weight: int = 0                          # число сообщений u → v
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    reply_weight: int = 0                    # число ответов (диалогических связей)
    personal_weight: int = 0                 # direct + reply, без group-шумa
    group_weight: int = 0
    timestamps: list[datetime] = field(default_factory=list)

    @property
    def span(self) -> timedelta | None:
        if self.first_seen and self.last_seen:
            return self.last_seen - self.first_seen
        return None


class CommunicationGraph:
    """Ориентированный взвешенный граф коммуникаций + временная ось.

    Параметры:
        window_days  — размер временного окна агрегации (для скользящего
                       анализа активности);
        time_unit    — базовая единица дискретизации времени.
    """

    def __init__(
        self,
        messages: Iterable[MessageRecord] = (),
        window_days: int = 7,
        chat_members: Mapping[str, Iterable[str]] | None = None,
    ) -> None:
        self.graph = nx.DiGraph()
        self.window_days = window_days
        self._messages: list[MessageRecord] = []
        self._members_by_chat: dict[str, set[str]] = {}
        for chat_id, members in (chat_members or {}).items():
            self._members_by_chat[chat_id] = set(members)
        message_list = list(messages)
        # Group membership is a property of the chat, not of message order.
        # Pre-register observed participants so earlier group messages are not
        # lost merely because a participant first appears later in the log.
        for m in message_list:
            self._members_by_chat.setdefault(m.chat_id, set()).add(m.sender)
            if m.recipient:
                self._members_by_chat[m.chat_id].add(m.recipient)
        for m in message_list:
            self.add_message(m)

    def register_chat_members(
        self, chat_id: str, members: Iterable[str]
    ) -> None:
        """Registers explicit chat membership before group events are added."""
        self._members_by_chat.setdefault(chat_id, set()).update(members)

    # ------------------------------------------------------------------ build
    def add_message(self, msg: MessageRecord) -> None:
        """Добавляет событие в модель и обновляет граф."""
        self._messages.append(msg)
        self._members_by_chat.setdefault(msg.chat_id, set()).add(msg.sender)
        if msg.recipient:
            self._members_by_chat[msg.chat_id].add(msg.recipient)

        targets: Iterable[str] = ()
        if msg.event_type in (EVENT_DIRECT, EVENT_REPLY) and msg.recipient:
            targets = [msg.recipient]
        elif msg.event_type == EVENT_GROUP:
            # групповое сообщение транслируется всем остальным участникам чата
            targets = (
                u for u in self._members_by_chat.get(msg.chat_id, set())
                if u != msg.sender
            )

        for tgt in targets:
            self._ensure_node(msg.sender)
            self._ensure_node(tgt)
            self._add_edge_event(msg.sender, tgt, msg)

    def _ensure_node(self, user: str) -> None:
        if user not in self.graph:
            self.graph.add_node(
                user,
                first_seen=None,
                last_seen=None,
                sent=0,
                received=0,
                active_days=set(),
            )

    def _add_edge_event(self, u: str, v: str, msg: MessageRecord) -> None:
        if self.graph.has_edge(u, v):
            d = self.graph[u][v]
        else:
            self.graph.add_edge(
                u,
                v,
                weight=0,
                first_seen=msg.timestamp,
                last_seen=msg.timestamp,
                reply_weight=0,
                personal_weight=0,
                group_weight=0,
                timestamps=[],
            )
            d = self.graph[u][v]
        d["weight"] += 1
        d["first_seen"] = min(d["first_seen"], msg.timestamp)
        d["last_seen"] = max(d["last_seen"], msg.timestamp)
        d["timestamps"].append(msg.timestamp)
        if msg.event_type == EVENT_REPLY:
            d["reply_weight"] += 1
        if msg.event_type == EVENT_GROUP:
            d["group_weight"] += 1
        else:
            d["personal_weight"] += 1

        nd = self.graph.nodes[u]
        nd["sent"] += 1
        nd["last_seen"] = (
            msg.timestamp
            if nd["last_seen"] is None or msg.timestamp > nd["last_seen"]
            else nd["last_seen"]
        )
        nd["first_seen"] = (
            msg.timestamp
            if nd["first_seen"] is None or msg.timestamp < nd["first_seen"]
            else nd["first_seen"]
        )
        nd["active_days"].add(msg.timestamp.date())

        nd_v = self.graph.nodes[v]
        nd_v["received"] += 1
        nd_v["last_seen"] = (
            msg.timestamp
            if nd_v["last_seen"] is None or msg.timestamp > nd_v["last_seen"]
            else nd_v["last_seen"]
        )
        nd_v["first_seen"] = (
            msg.timestamp
            if nd_v["first_seen"] is None or msg.timestamp < nd_v["first_seen"]
            else nd_v["first_seen"]
        )

    # ---------------------------------------------------------------- access
    @property
    def messages(self) -> list[MessageRecord]:
        return list(self._messages)

    @property
    def n_users(self) -> int:
        return self.graph.number_of_nodes()

    @property
    def n_edges(self) -> int:
        return self.graph.number_of_edges()

    @property
    def time_range(self) -> tuple[datetime, datetime] | None:
        if not self._messages:
            return None
        ts = [m.timestamp for m in self._messages]
        return min(ts), max(ts)

    def edges_aggregated(self) -> Iterator[CommunicationEdge]:
        for u, v, d in self.graph.edges(data=True):
            yield CommunicationEdge(
                source=u,
                target=v,
                weight=d["weight"],
                first_seen=d["first_seen"],
                last_seen=d["last_seen"],
                reply_weight=d["reply_weight"],
                personal_weight=d["personal_weight"],
                group_weight=d["group_weight"],
                timestamps=list(d["timestamps"]),
            )

    # ------------------------------------------------------------- slicing
    def subgraph_window(
        self, start: datetime, end: datetime
    ) -> "CommunicationGraph":
        """Перестроить граф только по событам в интервале [start, end).

        Используется алгоритмом изоляции для анализа временных окон.
        """
        win = CommunicationGraph(window_days=self.window_days)
        for m in self._messages:
            if start <= m.timestamp < end:
                win.add_message(m)
        return win

    def mutual_pairs(self) -> list[tuple[str, str]]:
        """Пары (u, v), u < v, между которыми есть двусторонние рёбра."""
        out = []
        seen = set()
        for u, v in self.graph.edges():
            key = tuple(sorted((u, v)))
            if key in seen:
                continue
            seen.add(key)
            if self.graph.has_edge(v, u):
                out.append(key)
        return out

    def reciprocity(self) -> float:
        """Локальная реципрокность графа (доля взаимных рёбер)."""
        e = self.graph.number_of_edges()
        if e == 0:
            return 0.0
        mutual = sum(
            1 for u, v in self.graph.edges() if self.graph.has_edge(v, u)
        )
        return mutual / e

    def activity_per_day(self, user: str) -> dict:
        """Активность пользователя по дням (число исходящих сообщений)."""
        res: dict = {}
        for m in self._messages:
            if m.sender == user:
                day = m.timestamp.date()
                res[day] = res.get(day, 0) + 1
        return res

    # ------------------------------------------------------------- io
    @classmethod
    def from_csv(cls, path: str | Path) -> "CommunicationGraph":
        """Загрузка из CSV: sender,recipient,chat_id,timestamp,event_type,length."""
        from .dataset import load_messages_csv

        msgs = load_messages_csv(path)
        return cls(msgs)

    def to_gexf(self, path: str | Path) -> None:
        g = self.graph.copy()
        for _, _, d in g.edges(data=True):
            d.pop("timestamps", None)
            for key in ("first_seen", "last_seen"):
                if isinstance(d.get(key), datetime):
                    d[key] = d[key].isoformat()
        for _, nd in g.nodes(data=True):
            nd["active_days"] = len(nd.get("active_days", set()))
            for key in ("first_seen", "last_seen"):
                if isinstance(nd.get(key), datetime):
                    nd[key] = nd[key].isoformat()
        nx.write_gexf(g, str(path))

    def density(self) -> float:
        n = self.n_users
        if n < 2:
            return 0.0
        return self.n_edges / (n * (n - 1))

    def __repr__(self) -> str:  # pragma: no cover
        tr = self.time_range
        return (
            f"CommunicationGraph(users={self.n_users}, edges={self.n_edges}, "
            f"messages={len(self._messages)}, "
            f"range={tr[0].date() if tr else '—'}..{tr[1].date() if tr else '—'})"
        )


def silience_gap_days(user: str, graph: CommunicationGraph, now: datetime | None = None) -> float:
    """Время молчания: дни с последнего любого участия пользователя."""
    tr = graph.time_range
    if tr is None:
        return math.inf
    ref = now or tr[1]
    nd = graph.graph.nodes.get(user)
    if not nd or nd["last_seen"] is None:
        return math.inf
    return (ref - nd["last_seen"]).total_seconds() / 86400.0
