"""Модуль практической части исследования.

Тема: «Методика оценки вовлеченности сотрудников на основе анализа графа
взаимодействий в системах обмена сообщениями».

Цель: разработка графовой модели коммуникаций и алгоритма выявления
пользователей с признаками коммуникативной изоляции.

Структура модуля (по задачам исследования):
    * models.py             — графовая модель коммуникаций (узлы, направленные
                              рёбра, веса) — задача 2;
    * metrics.py            — расчёт SNA-метрик (центральность, betweenness,
                              плотность и др.) — задачи 1, 2;
    * isolation_detector.py — алгоритм выявления коммуникативной изоляции с
                              учётом направленности и временных
                              характеристик — задача 3;
    * synthetic_generator.py— генератор синтетических датасетов — задача 4;
    * dataset.py            — загрузка/экспорт логов переписки (CSV);
    * visualize.py          — визуализация графа и результатов;
    * run_research.py       — сценарий проведения эксперимента (задача 4).
"""

__version__ = "1.0.0"

from .models import CommunicationEdge, CommunicationGraph, MessageRecord
from .metrics import NodeMetrics, compute_global_metrics, compute_node_metrics
from .isolation_detector import (
    IsolationAssessment,
    IsolationConfig,
    detect_isolated_users,
)
from .synthetic_generator import generate_synthetic_dataset
from .dataset import load_messages_csv, save_messages_csv

__all__ = [
    "CommunicationEdge",
    "CommunicationGraph",
    "MessageRecord",
    "NodeMetrics",
    "compute_global_metrics",
    "compute_node_metrics",
    "IsolationAssessment",
    "IsolationConfig",
    "detect_isolated_users",
    "generate_synthetic_dataset",
    "load_messages_csv",
    "save_messages_csv",
]
