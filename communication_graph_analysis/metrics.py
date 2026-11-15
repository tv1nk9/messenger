"""SNA-метрики для графа коммуникаций (задачи 1 и 2).

Реализованы классические метрики анализа социальных сетей, применяемые к
ориентированному взвешенному графу переписки:

    * degree centrality (in/out/total) — интенсивность контактов;
    * weighted in/out degree            — объём сообщений;
    * betweenness centrality            — роль «мостика» между группами;
    * closeness centrality (dijkstra)   — удалённость от остальных;
    * eigenvector / PageRank            — «престиж» через связи с влиятельными;
    * clustering coefficient            — транзитивность локального окружения;
    * reciprocity                       — доля взаимных диалогов;
    * плотность, компоненты связности   — глобальные характеристики.

Ограничения классических SNA-метрик при работе с мессенджерами
(обоснование необходимости авторского алгоритма, задача 1):
    1. Метрики не различают «шумовую» массовую рассылку и осмысленный диалог
       (high out-degree без входящих ответов — спам/оповещения).
    2. Degree-метрики чувствительны к объёму, но игнорируют временные разрывы:
       сотрудник мог написать 100 сообщений в первый день недели и замолчать.
    3. Betweenness/Closeness на направленных разреженных графах нестабильны
       при малом числе рёбер и не учитывают направление «кто инициирует».
    4. Классическая изоляция = нулевая степень, что не выявляет частичную
       («функциональную») изоляцию: формально присутствует, фактически — нет.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import networkx as nx
import numpy as np

from .models import CommunicationGraph


@dataclass
class NodeMetrics:
    """Вектор признаков пользователя для критериев изоляции."""

    user: str
    out_degree: int = 0            # число уникальных адресатов
    in_degree: int = 0             # число уникальных отправителей ему
    out_weight: int = 0            # всего исходящих сообщений
    in_weight: int = 0             # всего входящих сообщений
    total_weight: int = 0
    mutual_partners: int = 0       # партнёры с двусторонней связью
    reply_in_weight: int = 0       # ответов ПРИШЛО пользователю (v→u reply_weight? см. ниже)
    reply_out_weight: int = 0      # ответов ОТПРАВИЛ пользователь
    degree_centrality: float = 0.0
    betweenness: float = 0.0
    closeness: float = 0.0
    pagerank: float = 0.0
    clustering: float = 0.0
    active_days: int = 0           # дней с исходящими сообщениями
    last_seen_gap_days: float = 0.0  # дни молчания до конца наблюдения
    silence_gaps: list[float] = field(default_factory=list)  # межсообщенческие паузы (дни)
    max_silence_days: float = 0.0
    mean_burstiness: float = 0.0   # неравномерность потока сообщений (Fano-подобная)


def _undigraph(g: nx.DiGraph) -> nx.Graph:
    return nx.DiGraph.to_undirected(g)


def compute_node_metrics(cg: CommunicationGraph) -> dict[str, NodeMetrics]:
    """Рассчитывает полный набор метрик по всем узлам графа."""
    g = cg.graph
    users = list(g.nodes())
    if not users:
        return {}

    und = _undigraph(g)
    betweenness = nx.betweenness_centrality(g)
    try:
        closeness = nx.closeness_centrality(g)
    except Exception:  # pragma: no cover - пустой граф
        closeness = {u: 0.0 for u in users}
    pagerank = nx.pagerank(g, weight="weight")
    clustering = nx.clustering(und)

    n = len(users)
    metrics: dict[str, NodeMetrics] = {}
    for u in users:
        nd = g.nodes[u]
        m = NodeMetrics(user=u)
        m.out_degree = g.out_degree(u)
        m.in_degree = g.in_degree(u)
        m.out_weight = sum(d["weight"] for _, _, d in g.out_edges(u, data=True))
        m.in_weight = sum(d["weight"] for _, _, d in g.in_edges(u, data=True))
        m.total_weight = m.out_weight + m.in_weight
        m.reply_out_weight = sum(
            d["reply_weight"] for _, _, d in g.out_edges(u, data=True)
        )
        m.reply_in_weight = sum(
            d["reply_weight"] for _, _, d in g.in_edges(u, data=True)
        )
        partners_out = {v for _, v in g.out_edges(u)}
        partners_in = {v for v, _ in g.in_edges(u)}
        m.mutual_partners = len(partners_out & partners_in)
        deg = m.out_degree + m.in_degree
        m.degree_centrality = deg / (n - 1) if n > 1 else 0.0
        m.betweenness = betweenness.get(u, 0.0)
        m.closeness = closeness.get(u, 0.0)
        m.pagerank = pagerank.get(u, 0.0)
        m.clustering = clustering.get(u, 0.0)

        # Временные признаки по исходящим сообщениям пользователя.
        ts = sorted(msg.timestamp for msg in cg.messages if msg.sender == u)
        all_ts: list = list(ts)
        # если исходящих нет — используем входящие события как «присутствие»
        if not all_ts:
            all_ts = sorted(
                t
                for _, v, d in g.in_edges(u, data=True)
                for t in d["timestamps"]
            )
        m.active_days = len(nd.get("active_days", set()))
        tr = cg.time_range
        if tr is not None:
            last = nd["last_seen"] or (all_ts[-1] if all_ts else tr[0])
            m.last_seen_gap_days = (tr[1] - last).total_seconds() / 86400.0
        if len(all_ts) >= 2:
            gaps = np.diff(
                np.array([t.timestamp() for t in all_ts], dtype=float)
            ) / 86400.0
            m.silence_gaps = gaps.tolist()
            m.max_silence_days = float(gaps.max())
            # burstiness: (sigma^2 - mu)/mu по дневным объёмам (0 = пуассоновский)
            days: dict = {}
            for t in all_ts:
                days[t.date()] = days.get(t.date(), 0) + 1
            counts = np.array(list(days.values()), dtype=float)
            if counts.size and counts.mean() > 0:
                m.mean_burstiness = float(
                    (counts.var() - counts.mean()) / counts.mean()
                )
        metrics[u] = m
    return metrics


@dataclass
class GlobalMetrics:
    n_users: int
    n_messages: int
    n_edges: int
    density: float
    avg_degree: float
    reciprocity: float
    n_weak_components: int
    n_strong_components: int
    largest_component_share: float
    avg_path_length: float | None
    avg_clustering: float
    isolated_zero_degree_share: float  # доля узлов с полной нулевой степенью


def compute_global_metrics(cg: CommunicationGraph) -> GlobalMetrics:
    g = cg.graph
    n = g.number_of_nodes()
    weak = list(nx.weakly_connected_components(g))
    strong = list(nx.strongly_connected_components(g))
    largest = max((len(c) for c in weak), default=0)
    try:
        apl = nx.average_shortest_path_length(
            nx.DiGraph.subgraph(g, max(weak, key=len))
        ) if weak and len(max(weak, key=len)) > 1 else None
    except nx.NetworkXError:  # pragma: no cover
        apl = None
    zero_deg = sum(
        1 for u in g.nodes() if g.in_degree(u) == 0 and g.out_degree(u) == 0
    )
    return GlobalMetrics(
        n_users=n,
        n_messages=len(cg.messages),
        n_edges=g.number_of_edges(),
        density=cg.density(),
        avg_degree=(g.number_of_edges() / n) if n else 0.0,
        reciprocity=cg.reciprocity(),
        n_weak_components=len(weak),
        n_strong_components=len(strong),
        largest_component_share=(largest / n) if n else 0.0,
        avg_path_length=apl,
        avg_clustering=nx.average_clustering(_undigraph(g)) if n else 0.0,
        isolated_zero_degree_share=(zero_deg / n) if n else 0.0,
    )


def metrics_to_dataframe(metrics: dict[str, NodeMetrics]):
    """NodeMetrics → pandas.DataFrame (для отчётов и машинного обучения)."""
    import pandas as pd

    rows = []
    for m in metrics.values():
        d = {k: v for k, v in m.__dict__.items()}
        d.pop("silence_gaps", None)
        rows.append(d)
    df = pd.DataFrame(rows).set_index("user")
    return df.sort_values("total_weight")
