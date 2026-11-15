"""Визуализация графа коммуникаций и результатов изоляции (задача 4).

Используется matplotlib (Agg-бэкенд, работает без дисплея). Функции
возвращают пути к сохранённым PNG-файлам.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import networkx as nx  # noqa: E402

from .isolation_detector import IsolationAssessment  # noqa: E402
from .models import CommunicationGraph  # noqa: E402


def plot_communication_graph(
    cg: CommunicationGraph,
    assessments: list[IsolationAssessment],
    out_path: str | Path = "results/graph.png",
    title: str = "Граф коммуникаций: изолированные узлы выделены красным",
) -> Path:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    g = cg.graph
    isolated = {a.user for a in assessments if a.isolated}
    bots = {a.user for a in assessments if a.is_bot}

    pos = nx.spring_layout(g, seed=7, k=1.6 / max(1, len(g) ** 0.5))
    colors = []
    sizes = []
    for u in g.nodes():
        if u in bots:
            colors.append("#9e9e9e")
        elif u in isolated:
            colors.append("#e53935")
        else:
            colors.append("#42a5f5")
        total = g.in_degree(u) + g.out_degree(u)
        sizes.append(80 + 40 * total)

    fig, ax = plt.subplots(figsize=(11, 8))
    und = nx.Graph(g)
    nx.draw_networkx_edges(
        und, pos, ax=ax, alpha=0.35, width=1.0, edge_color="#616161"
    )
    nx.draw_networkx_nodes(g, pos, ax=ax, node_color=colors, node_size=sizes)
    small = [u for u in g.nodes() if g.degree(u) > 0]
    nx.draw_networkx_labels(g, pos, labels={u: u[-4:] for u in small}, font_size=6, ax=ax)
    ax.set_title(title)
    ax.axis("off")
    from matplotlib.lines import Line2D

    legend = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#42a5f5", markersize=10, label="normal"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#e53935", markersize=10, label="isolated"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#9e9e9e", markersize=10, label="bot/excluded"),
    ]
    ax.legend(handles=legend, loc="upper right")
    fig.tight_layout()
    fig.savefig(str(out), dpi=150)
    plt.close(fig)
    return out


def plot_isolation_scores(
    assessments: list[IsolationAssessment],
    out_path: str | Path = "results/scores.png",
    top: int = 20,
) -> Path:
    """Гистограмма риска изоляции по критериям К1–К4 для топ-N пользователей."""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    data = [a for a in assessments if not a.is_bot][:top]
    users = [a.user for a in data]
    import numpy as np

    f1 = np.array([a.f1 for a in data])
    f2 = np.array([a.f2 for a in data])
    f3 = np.array([a.f3 for a in data])
    f4 = np.array([a.f4 for a in data])
    x = np.arange(len(users))
    w = 0.2
    fig, ax = plt.subplots(figsize=(max(8, len(users) * 0.6), 5))
    ax.bar(x - 1.5 * w, f1, w, label="K1 initiative deficit")
    ax.bar(x - 0.5 * w, f2, w, label="K2 flow asymmetry")
    ax.bar(x + 0.5 * w, f3, w, label="K3 temporal fragmentation")
    ax.bar(x + 1.5 * w, f4, w, label="K4 peripherality")
    marks = [a.score for a in data]
    for xi, s, iso in zip(x, marks, [a.isolated for a in data]):
        ax.annotate(
            f"{s:.2f}",
            xy=(xi, s + 0.03),
            ha="center", fontsize=7,
            color="#b71c1c" if iso else "#333333",
        )
    ax.axhline(0.55, ls="--", c="red", lw=1, label="threshold")
    ax.set_xticks(x)
    ax.set_xticklabels(users, rotation=60, fontsize=7)
    ax.set_ylabel("normalized criterion violation (0..1)")
    ax.set_title("Risk of communication isolation by criteria")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(str(out), dpi=150)
    plt.close(fig)
    return out
