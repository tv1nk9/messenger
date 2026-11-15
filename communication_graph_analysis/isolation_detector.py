"""Алгоритм выявления коммуникативной изоляции (задача 3 исследования).

Формальные критерии принадлежности пользователя u к «изолированным»
(задача 2) построены на четырёх группах признаков, вычисляемых по
направленному графу G за наблюдаемый период [t0, t1] и по последнему
временному окну W (скользящее окно длины ``window_days``):

  К1. Дефицит исходящей инициативы:
        A_out(u) = Σ_{v} w(u→v) / |W|  — среднее число исходящих сообщений в день;
        D_out(u) = |{v : ∃ ребро u→v в W}| — охват адресатов;
        признак C1 ⇔ A_out(u) ≤ θ_a  ИЛИ  D_out(u) ≤ θ_d.

  К2. Асимметрия направленности (односторонние контакты):
        R(u) = min(InW(u), OutW(u)) / (InW(u) + OutW(u) + 1) — индекс
        взаимности потока; низкий R означает, что u либо только получает
        рассылки (InW≫OutW), либо только вещает без отклика (OutW≫InW);
        признак C2 ⇔ R(u) ≤ θ_r  И  mutual(u) ≤ θ_m.

  К3. Временная фрагментация:
        S(u) — максимальная пауза молчания внутри окна наблюдения;
        L(u) — «время молчания» от последнего события до t1;
        E(u) — доля активных дней (active_days / total_days);
        признак C3 ⇔ (S(u) ≥ θ_s ИЛИ L(u) ≥ θ_l) И E(u) ≤ θ_e.

  К4. Периферийность в структуре графа (уточняющий критерий):
        PageRank(u) ≤ percentile_p и Closeness(u) ≤ θ_c — u лежит на
        периферии гигантской компоненты связности.

Итоговая классификация — взвешенная оценка «риска изоляции»:

        IsolationScore(u) = Σ_i β_i · f_i(u),  f_i ∈ [0..1] — нормированные
        степени нарушения каждого критерия, β_i — веса (настраиваются).

Пользователь признаётся изолированным, если:
    IsolationScore(u) ≥ threshold  И  выполнено не менее k обязательных
    базовых критериев (К1, К2 или К3) — это отсекает ложные срабатывания у
    «интровертных, но включённых» сотрудников (мало пишут, но оперативно
    отвечают и получают персональные сообщения).

Отличия от наивного правила «degree = 0»: алгоритм выявляет частичную
(функциональную) изоляцию, учитывает направление потоков и деградацию
активности во времени.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

import numpy as np
import networkx as nx

from .metrics import NodeMetrics, compute_node_metrics
from .models import CommunicationGraph


@dataclass
class IsolationConfig:
    """Пороги и веса алгоритма (калибруются на тестовых датасетах)."""

    # --- окно анализа
    window_days: int = 7
    # --- К1: дефицит исходящей инициативы
    theta_a: float = 0.5          # мин. исходящих сообщений в сутки за окно
    theta_d: int = 2              # мин. уникальных адресатов за всё наблюдение
    # --- К2: асимметрия направленности (односторонние контакты)
    theta_r: float = 0.15         # мин. индекс взаимности потока R(u)
    mu_out: int = 30              # «норма» объёма исходящих (для f2)
    mu_in: int = 60               # «норма» объёма входящих (для f2)
    theta_m: int = 2              # мин. число взаимных диалогических партнёров
    # --- К3: временная фрагментация
    theta_s: float = 5.0          # макс. допустимая пауза молчания, дней
    theta_l: float = 4.0          # макс. время молчания до конца наблюдения
    theta_e: float = 0.5          # мин. доля активных дней
    # --- К4: периферийность
    pagerank_percentile: float = 10.0   # нижний перцентиль PageRank
    theta_c: float = 0.15               # мин. closeness centrality
    # --- агрегирование
    weights: tuple[float, float, float, float] = (0.30, 0.40, 0.25, 0.05)
    score_threshold: float = 0.30
    required_criteria: int = 1      # минимум из {К1, К2, К3}
    # сотрудники, чьи сообщения являются массовыми рассылками (боты/оповещения)
    exclude_bots: bool = True
    bot_out_degree_share: float = 0.8  # пишет ≥80% коллег без входящих DM


@dataclass
class IsolationAssessment:
    user: str
    metrics: NodeMetrics
    criterion_c1: bool = False
    criterion_c2: bool = False
    criterion_c3: bool = False
    criterion_c4: bool = False
    f1: float = 0.0               # нормированные степени нарушения 0..1
    f2: float = 0.0
    f3: float = 0.0
    f4: float = 0.0
    score: float = 0.0
    isolated: bool = False
    reasons: list[str] = field(default_factory=list)
    is_bot: bool = False

    def to_dict(self) -> dict:
        return {
            "user": self.user,
            "score": round(self.score, 4),
            "isolated": self.isolated,
            "is_bot": self.is_bot,
            "c1_deficit_initiative": self.criterion_c1,
            "c2_flow_asymmetry": self.criterion_c2,
            "c3_temporal_fragmentation": self.criterion_c3,
            "c4_peripherality": self.criterion_c4,
            "f1": round(self.f1, 3),
            "f2": round(self.f2, 3),
            "f3": round(self.f3, 3),
            "f4": round(self.f4, 3),
            "out_weight": self.metrics.out_weight,
            "in_weight": self.metrics.in_weight,
            "personal_out_weight": self.metrics.personal_out_weight,
            "personal_in_weight": self.metrics.personal_in_weight,
            "mutual_partners": self.metrics.mutual_partners,
            "max_silence_days": round(self.metrics.max_silence_days, 2),
            "last_seen_gap_days": round(self.metrics.last_seen_gap_days, 2),
            "reasons": "; ".join(self.reasons),
        }


def _clip01(x: float) -> float:
    return float(min(max(x, 0.0), 1.0))


def detect_isolated_users(
    cg: CommunicationGraph,
    config: IsolationConfig | None = None,
) -> list[IsolationAssessment]:
    """Запуск алгоритма: возвращает оценки по всем пользователям,
    отсортированные по убыванию риска изоляции."""
    cfg = config or IsolationConfig()
    metrics = compute_node_metrics(cg)
    if not metrics:
        return []

    tr = cg.time_range
    assert tr is not None
    t0, t1 = tr
    total_days = max((t1 - t0).total_seconds() / 86400.0, 1e-9)
    win_start = t1 - timedelta(days=cfg.window_days)
    win_days = min(float(cfg.window_days), total_days)

    g = cg.graph
    n = cg.n_users

    # PageRank-перцентиль для критерия К4
    weak_components = list(nx.weakly_connected_components(g))
    giant = set(max(weak_components, key=len)) if weak_components else set()
    pr_values = np.array([m.pagerank for u, m in metrics.items() if u in giant])
    pr_cut = float(np.percentile(pr_values, cfg.pagerank_percentile))

    assessments: list[IsolationAssessment] = []
    for u, m in metrics.items():
        a = IsolationAssessment(user=u, metrics=m)

        # ---- обнаружение «ботов»/каналов оповещений
        out_deg_share = (m.out_degree / (n - 1)) if n > 1 else 0.0
        if (
            cfg.exclude_bots
            and out_deg_share >= cfg.bot_out_degree_share
            and m.in_weight == 0
        ):
            a.is_bot = True
            a.reasons.append("bot/broadcast: excluded from analysis")
            assessments.append(a)
            continue

        # ================= К1: дефицит исходящей инициативы ================
        win_out = sum(
            sum(ts >= win_start for ts in d["timestamps"])
            for _, _, d in g.out_edges(u, data=True)
        )
        avg_out_per_day = win_out / win_days
        a.criterion_c1 = (
            avg_out_per_day <= cfg.theta_a or m.out_degree <= cfg.theta_d
        )
        # степень нарушения: 1 при нулевой активности, плавно убывает
        a.f1 = _clip01(
            0.5 * (1 - _clip01(avg_out_per_day / (2 * cfg.theta_a)))
            + 0.5 * (1 - _clip01(m.out_degree / (2 * max(cfg.theta_d, 1))))
        )
        if a.criterion_c1:
            a.reasons.append(
                f"К1: low outgoing initiative "
                f"({avg_out_per_day:.2f} msg/day, out-degree={m.out_degree})"
            )

        # ============ К2: асимметрия направленных потоков ==================
        # Учитывается ИМЕНАПРАВЛЕННОСТЬ: ответные рёбра v→u (коллега ответил
        # пользователю u) — признак включённого диалога; односторонние потоки
        # (монологи без отклика или только групповой шум) — признак изоляции.
        response_personal = sum(
            d["reply_weight"] for v, _, d in g.in_edges(u, data=True)
            if v != "bot_notice" and g.has_edge(u, v)
        )  # replies from people with whom u has a two-way connection
        reciprocity_idx = min(m.personal_in_weight, m.personal_out_weight) / (
            m.personal_in_weight + m.personal_out_weight + 1
        )
        low_volume = (
            m.personal_out_weight < cfg.mu_out
            and m.personal_in_weight < cfg.mu_in
        )  # почти нет персональной переписки (кроме группового шума)
        no_dialogue = response_personal < 3 and m.mutual_partners <= cfg.theta_m
        a.criterion_c2 = (
            (reciprocity_idx <= cfg.theta_r or low_volume) and no_dialogue
        )
        asym = _clip01(1 - reciprocity_idx / max(cfg.theta_r, 1e-9))
        vol_def = _clip01(
            0.5 * (1 - _clip01(m.out_weight / cfg.mu_out))
            + 0.5 * (1 - _clip01(m.in_weight / cfg.mu_in))
        )
        dial_def = _clip01(1 - response_personal / 3.0)
        a.f2 = max(asym, vol_def) * max(dial_def, _clip01(
            1 - m.mutual_partners / (cfg.theta_m + 1)
        ))
        if a.criterion_c2:
            if m.personal_in_weight > 3 * max(m.personal_out_weight, 1):
                kind = "passive receiver (broadcast target)"
            elif m.personal_out_weight > 3 * max(m.personal_in_weight, 1):
                kind = "unanswered broadcaster"
            else:
                kind = "negligible personal dialogue"
            a.reasons.append(
                f"К2: flow asymmetry R={reciprocity_idx:.2f}, "
                f"personal responses={response_personal} → {kind}"
            )

        # =============== К3: временная фрагментация ========================
        # Оценивается деградация АКТИВНОСТИ ВО ВРЕМЕНИ: сравнение средней
        # исходящей активности в первом и последнем окне наблюдения.
        active_ratio = m.active_days / total_days if total_days else 0.0
        silence_bad = (
            m.max_silence_days >= cfg.theta_s
            or m.last_seen_gap_days >= cfg.theta_l
        )
        a.criterion_c3 = silence_bad and active_ratio <= cfg.theta_e
        early_cut = t0 + timedelta(days=max(1.0, total_days / 2))
        late_cut = t1 - timedelta(days=min(float(cfg.window_days), total_days / 2))
        sent_ts = [msg.timestamp for msg in cg.messages if msg.sender == u]
        early_cnt = sum(1 for t in sent_ts if t < early_cut)
        late_cnt = sum(1 for t in sent_ts if t >= late_cut)
        span_early = max((early_cut - t0).total_seconds() / 86400.0, 1e-9)
        span_late = max((t1 - late_cut).total_seconds() / 86400.0, 1e-9)
        decay = 1.0
        if early_cnt > 0:
            decay = _clip01((late_cnt / span_late) / (early_cnt / span_early))
        elif late_cnt == 0 and sent_ts:
            decay = 0.0
        temporal = _clip01(
            0.5 * _clip01(m.max_silence_days / (2 * cfg.theta_s))
            + 0.3 * _clip01(m.last_seen_gap_days / (2 * cfg.theta_l))
            + 0.2 * (1 - _clip01(active_ratio / max(cfg.theta_e, 1e-9)))
        )
        # деградация активности усиливает признак (вклад до +0.3)
        a.f3 = _clip01(temporal + 0.3 * (1 - decay))
        if a.criterion_c3:
            a.reasons.append(
                f"К3: temporal fragmentation "
                f"(max silence={m.max_silence_days:.1f}d, "
                f"gap to end={m.last_seen_gap_days:.1f}d, "
                f"active days ratio={active_ratio:.2f})"
            )

        # ================== К4: периферийность =============================
        if u in giant:
            a.criterion_c4 = (
                m.pagerank <= pr_cut and m.closeness <= cfg.theta_c
            )
            a.f4 = _clip01(
                0.5 * (1 - _clip01(m.closeness / max(cfg.theta_c, 1e-9)))
                + 0.5 * (1 - _clip01(m.pagerank / max(pr_cut, 1e-12)))
            )
        if a.criterion_c4:
            a.reasons.append(
                f"К4: peripherality (PR={m.pagerank:.5f} ≤ p{cfg.pagerank_percentile:.0f}, "
                f"closeness={m.closeness:.3f})"
            )

        # =================== итоговый скоринг ==============================
        b1, b2, b3, b4 = cfg.weights
        a.score = b1 * a.f1 + b2 * a.f2 + b3 * a.f3 + b4 * a.f4
        base_hits = (
            int(a.criterion_c1)
            + int(a.criterion_c2)
            + int(a.criterion_c3)
        )
        a.isolated = (not a.is_bot) and (
            a.score >= cfg.score_threshold
            and base_hits >= cfg.required_criteria
        )
        assessments.append(a)

    assessments.sort(key=lambda x: x.score, reverse=True)
    return assessments


def summary_table(assessments: list[IsolationAssessment]):
    """pandas.DataFrame со сводкой результатов."""
    import pandas as pd

    df = pd.DataFrame([a.to_dict() for a in assessments])
    return df.set_index("user") if not df.empty else df
