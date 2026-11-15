"""Сценарий проведения эксперимента (задача 4): демонстрация эффективности.

Запуск из корня репозитория:

    python -m communication_graph_analysis.run_research [--days 30] [--seed 42]

Результаты складываются в communication_graph_analysis/results/:
    * metrics_global.json     — глобальные SNA-метрики датасета;
    * isolation_report.csv    — оценки по каждому сотруднику;
    * confusion_matrix.csv    — TP/FP/FN/TN относительно ground truth;
    * baseline_comparison.csv — сравнение с наивными базлайнами;
    * graph.png, scores.png   — визуализации;
    * messages.csv            — выгрузка синтетического лога переписки.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from .dataset import save_messages_csv
from .isolation_detector import IsolationConfig, detect_isolated_users, summary_table
from .metrics import compute_global_metrics, compute_node_metrics, metrics_to_dataframe
from .synthetic_generator import generate_synthetic_dataset
from .visualize import plot_communication_graph, plot_isolation_scores

RESULTS_DIR = Path(__file__).resolve().parent / "results"


# --------------------------------------------------------------- baselines
def baseline_zero_degree(cg, labels) -> set[str]:
    """Классический SNA-критерий: изолирован ⇔ полная степень = 0."""
    g = cg.graph
    return {u for u in g.nodes() if g.in_degree(u) == 0 and g.out_degree(u) == 0}


def baseline_low_degree_percentile(cg, labels, pct: float = 15.0) -> set[str]:
    """Базлайн: нижний перцентиль суммарной степени."""
    g = cg.graph
    import numpy as np

    deg = np.array([g.in_degree(u) + g.out_degree(u) for u in g.nodes()])
    cut = float(np.percentile(deg, pct))
    users = list(g.nodes())
    return {
        u
        for u, d in zip(users, deg)
        if d <= cut and labels.get(u, {}).get("profile") != "bot"
    }


def evaluate(pred: set[str], labels: dict) -> dict:
    gt = {u for u, l in labels.items() if l["isolated"]}
    tp = len(pred & gt)
    fp = len(pred - gt)
    fn = len(gt - pred)
    tn = len(labels) - tp - fp - fn
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    acc = (tp + tn) / len(labels) if labels else 0.0
    return {
        "TP": tp, "FP": fp, "FN": fn, "TN": tn,
        "precision": round(prec, 3),
        "recall": round(rec, 3),
        "f1": round(f1, 3),
        "accuracy": round(acc, 3),
    }


# ------------------------------------------------------------------ main
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--window-days", type=int, default=7)
    args = ap.parse_args(argv)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 78)
    print("Практическая часть исследования: оценка вовлеченности сотрудников")
    print("по графу взаимодействий в мессенджере")
    print("=" * 78)

    # --- Шаг 1. Формирование тестового набора данных (задача 4)
    print("\n[1] Генерация синтетического датасета коммуникаций…")
    cg, labels = generate_synthetic_dataset(
        days=args.days, seed=args.seed, with_bot=True
    )
    print(f"    {cg!r}")
    profile_counts = pd.Series([l["profile"] for l in labels.values()]).value_counts()
    print("    Профили (ground truth):")
    for p, c in profile_counts.items():
        print(f"      {p:<10} {c:>3}")

    csv_path = RESULTS_DIR / "messages.csv"
    save_messages_csv(cg.messages, csv_path)
    print(f"    Лог переписки сохранён: {csv_path}")

    # --- Шаг 2. Графовая модель и метрики (задачи 1–2)
    print("\n[2] Расчёт SNA-метрик графа коммуникаций…")
    gm = compute_global_metrics(cg)
    gm_dict = asdict(gm)
    print(json.dumps(gm_dict, indent=2, ensure_ascii=False))
    (RESULTS_DIR / "metrics_global.json").write_text(
        json.dumps(gm_dict, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    nm = compute_node_metrics(cg)
    metrics_df = metrics_to_dataframe(nm)
    metrics_df.to_csv(RESULTS_DIR / "node_metrics.csv")
    print(f"    Метрики {metrics_df.shape[0]} узлов → results/node_metrics.csv")

    # --- Шаг 3. Алгоритм выявления изоляции (задача 3)
    print("\n[3] Запуск алгоритма выявления коммуникативной изоляции…")
    cfg = IsolationConfig(window_days=args.window_days)
    assessments = detect_isolated_users(cg, cfg)
    report = summary_table(assessments)
    report.to_csv(RESULTS_DIR / "isolation_report.csv", encoding="utf-8-sig")

    isolated = {a.user for a in assessments if a.isolated}
    bots = {a.user for a in assessments if a.is_bot}
    print(f"    Выявлено изолированных: {len(isolated)}; ботов исключено: {len(bots)}")
    print("\n    Топ рисков:")
    cols = ["score", "isolated", "c1_deficit_initiative",
            "c2_flow_asymmetry", "c3_temporal_fragmentation", "c4_peripherality"]
    print(report.drop(columns=["reasons"]).head(12)[cols].to_string())

    # --- Шаг 4. Оценка эффективности и сравнение с базлайнами (задача 4)
    print("\n[4] Оценка эффективности (сравнение с ground truth)…")
    rows = {
        "proposed_algorithm": evaluate(isolated, labels),
        "baseline_degree0": evaluate(baseline_zero_degree(cg, labels), labels),
        "baseline_low_degree_p15": evaluate(
            baseline_low_degree_percentile(cg, labels), labels
        ),
    }
    cmp_df = pd.DataFrame(rows).T
    cmp_df.to_csv(RESULTS_DIR / "baseline_comparison.csv")
    print(cmp_df.to_string())

    # детализация ошибок метода
    gt = {u for u, l in labels.items() if l["isolated"]}
    fp_users = sorted(isolated - gt)
    fn_users = sorted(gt - isolated)
    print(f"\n    Ложные срабатывания (FP): {fp_users or '—'}")
    print(f"    Пропуски (FN):            {fn_users or '—'}")
    by_profile = {}
    for a in assessments:
        prof = labels[a.user]["profile"]
        by_profile.setdefault(prof, []).append(a.score)
    prof_stats = {
        p: {"mean_score": round(float(sum(s) / len(s)), 3), "n": len(s)}
        for p, s in by_profile.items()
    }
    pd.DataFrame(prof_stats).T.to_csv(RESULTS_DIR / "scores_by_profile.csv")
    print("\n    Средний риск изоляции по профилям:")
    print(pd.DataFrame(prof_stats).T.to_string())

    # --- Визуализация
    print("\n[5] Визуализация…")
    p1 = plot_communication_graph(cg, assessments, RESULTS_DIR / "graph.png")
    p2 = plot_isolation_scores(assessments, RESULTS_DIR / "scores.png")
    cg.to_gexf(RESULTS_DIR / "graph.gexf")
    print(f"    {p1}\n    {p2}\n    {RESULTS_DIR / 'graph.gexf'}")

    print("\nГотово. Все артефакты в:", RESULTS_DIR)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
