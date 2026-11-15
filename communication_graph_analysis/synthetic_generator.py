"""Генератор синтетических датасетов коммуникаций (задача 4).

Формирует тестовые наборы с известной разметкой («ground truth»), чтобы
количественно оценить точность алгоритма изоляции (precision/recall/F1).

Профили сотрудников:
    * "active"     — регулярная двусторонняя переписка, несколько партнёров;
    * "hub"        — лидер мнений, высокий in/out degree;
    * "introvert"  — мало пишет, но быстро отвечает и получает личные
                     сообщения (включён в сеть; НЕ изолирован — проверка
                     на ложные срабатывания);
    * "drifting"   — активность деградирует во времени, длинные паузы
                     (ИЗОЛИРОВАН постепенная/временна́я изоляция);
    * "peripheral" — только получает оповещения группы, почти не отвечает
                     (ИЗОЛИРОВАН пассивная изоляция);
    * "ignored"    — много пишет в общий чат/коллегам, откликов нет
                     (ИЗОЛИРОВАН «невидимый» сотрудник);
    * "bot"        — массовая рассылка всем (исключается алгоритмом).
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta

from .models import (
    EVENT_DIRECT,
    EVENT_GROUP,
    EVENT_REPLY,
    CommunicationGraph,
    MessageRecord,
)

ISOLATED_PROFILES = {"drifting", "peripheral", "ignored"}


def generate_synthetic_dataset(
    n_active: int = 20,
    n_hubs: int = 3,
    n_introverts: int = 5,
    n_drifting: int = 4,
    n_peripheral: int = 4,
    n_ignored: int = 3,
    with_bot: bool = True,
    days: int = 30,
    seed: int = 42,
    start: datetime | None = None,
):
    """Собирает (graph, labels), где labels: user -> {profile, isolated}."""
    rng = random.Random(seed)
    start = start or datetime(2026, 1, 1, 9, 0, 0)
    end = start + timedelta(days=days)

    users: dict[str, str] = {}
    for i in range(n_active):
        users[f"emp_a{i:02d}"] = "active"
    for i in range(n_hubs):
        users[f"emp_h{i:02d}"] = "hub"
    for i in range(n_introverts):
        users[f"emp_i{i:02d}"] = "introvert"
    for i in range(n_drifting):
        users[f"emp_d{i:02d}"] = "drifting"
    for i in range(n_peripheral):
        users[f"emp_p{i:02d}"] = "peripheral"
    for i in range(n_ignored):
        users[f"emp_g{i:02d}"] = "ignored"
    if with_bot:
        users["bot_notice"] = "bot"

    names = [u for u, p in users.items() if p != "bot"]
    hubs = [u for u, p in users.items() if p == "hub"]
    messages: list[MessageRecord] = []

    def rnd_time(a: datetime, b: datetime) -> datetime:
        delta = (b - a).total_seconds()
        return a + timedelta(seconds=rng.uniform(0, max(delta, 1)))

    def push(sender, recipient, chat, t, etype):
        messages.append(
            MessageRecord(
                sender=sender,
                recipient=recipient,
                chat_id=chat,
                timestamp=t,
                event_type=etype,
                length_chars=rng.randint(20, 400),
            )
        )

    # --- активные и хабы: устойчивая взаимная переписка весь период.
    # Ответы (reply) генерируются ТОЛЬКО внутри пар «active/hub ↔ active/hub»,
    # чтобы peripheral/ignored-сотрудники не получали диалогических связей
    # (иначе ground truth был бы нарушен).
    core = [u for u, p in users.items() if p in ("active", "hub")]
    ignored_users = [u for u, p in users.items() if p == "ignored"]
    non_isolated = [
        u for u, p in users.items()
        if p not in ISOLATED_PROFILES and p != "bot"
    ]
    for u in core:
        prof = users[u]
        # партнёры выбираются только из core (активные/хабы): так изолированные
        # профили не включаются в устойчивые диалогические кластеры
        candidates = [v for v in core if v != u]
        partners = rng.sample(
            candidates, k=min(len(candidates), rng.randint(4, 8))
        )
        rate = rng.uniform(3.0, 6.0) if prof == "hub" else rng.uniform(1.5, 3.0)
        for p in partners:
            n_msgs = int(rate * days * rng.uniform(0.3, 1.0) / len(partners)) + 2
            for _ in range(n_msgs):
                t = rnd_time(start, end)
                push(u, p, f"dm_{min(u,p)}_{max(u,p)}", t, EVENT_DIRECT)
                # ответная реакция (диалогичность)
                if rng.random() < 0.7:
                    t2 = t + timedelta(minutes=rng.uniform(1, 240))
                    if t2 < end:
                        push(p, u, f"dm_{min(u,p)}_{max(u,p)}", t2, EVENT_REPLY)
        # участие в общем чате
        for _ in range(int(days * rng.uniform(0.5, 1.5))):
            push(u, None, "team_general", rnd_time(start, end), EVENT_GROUP)

    # --- интроверты: редко пишут первыми, но получают персональные DM от
    # нескольких коллег и оперативно отвечают (reply) — включены в сеть.
    for u, prof in users.items():
        if prof != "introvert":
            continue
        buddies = rng.sample(hubs + core, k=min(3, len(core)))
        for buddy in buddies:
            for _ in range(rng.randint(2, 4)):  # его редкие личные сообщения
                t = rnd_time(start, end)
                push(u, buddy, f"dm_{min(u,buddy)}_{max(u,buddy)}", t, EVENT_DIRECT)
            for _ in range(rng.randint(6, 10)):  # входящие DM + быстрые ответы
                t = rnd_time(start, end)
                push(buddy, u, f"dm_{min(u,buddy)}_{max(u,buddy)}", t, EVENT_DIRECT)
                t2 = t + timedelta(minutes=rng.uniform(1, 30))
                if t2 < end and rng.random() < 0.85:
                    push(u, buddy, f"dm_{min(u,buddy)}_{max(u,buddy)}", t2, EVENT_REPLY)

    # --- drifting: первая часть периода активна, затем длительное молчание
    for u, prof in users.items():
        if prof != "drifting":
            continue
        mid = start + timedelta(days=int(days * 0.35))
        partners = rng.sample(
            [v for v in non_isolated if v != u],
            k=min(3, len(non_isolated)),
        )
        for p in partners:
            for _ in range(rng.randint(6, 12)):
                t = rnd_time(start, mid)
                push(u, p, f"dm_{min(u,p)}_{max(u,p)}", t, EVENT_DIRECT)
        # единичное «присутствие» в конце периода — формально не изолирован
        # по степени, но временные признаки деградированы
        push(u, None, "team_general", end - timedelta(hours=6), EVENT_GROUP)

    # --- peripheral: только получатель групповых оповещений, сам почти молчит
    for u, prof in users.items():
        if prof != "peripheral":
            continue
        if rng.random() < 0.3:  # изредка одиночное сообщение в группу
            push(u, None, "team_general", rnd_time(start, end), EVENT_GROUP)

    # --- ignored: много пишет коллегам, но НЕ получает ни одного ответа.
    # Чтобы в его адрес не возникало ответных рёбер, активные сотрудники
    # выбирают партнёров только внутри ядра (core), а «игнорируемые» пишут
    # регулярные монологи в пустоту (~1 сообщение в день на адресата).
    for u in ignored_users:
        targets = rng.sample(
            [v for v in non_isolated if v != u],
            k=min(4, len(non_isolated)),
        )
        for tg in targets:
            for _ in range(max(2, days)):
                t = rnd_time(start, end)
                push(u, tg, f"dm_{min(u,tg)}_{max(u,tg)}", t, EVENT_DIRECT)

    # --- bot: рассылка всем без ответного потока
    if with_bot:
        for v in names:
            for _ in range(rng.randint(1, 3)):
                push("bot_notice", v, "dm_bot_" + v, rnd_time(start, end), EVENT_DIRECT)

    # очистим сообщения вне диапазона и упорядочим по времени
    messages = [m for m in messages if start <= m.timestamp <= end]
    messages.sort(key=lambda m: m.timestamp)

    graph = CommunicationGraph(messages, window_days=min(7, days))
    labels = {
        u: {"profile": prof, "isolated": prof in ISOLATED_PROFILES}
        for u, prof in users.items()
    }
    return graph, labels
