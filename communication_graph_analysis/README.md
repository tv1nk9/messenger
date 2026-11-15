# Анализ коммуникативной изоляции
Модуль `communication_graph_analysis` реализует графовый анализ переписки в
мессенджере и выявление пользователей с признаками функциональной
коммуникативной изоляции.
Модуль предназначен для исследовательских экспериментов и аналитических
прототипов. Он не интерпретирует низкую активность как доказательство
социальной изоляции и не заменяет проверку специалистом: результатом является
риск-оценка, основанная только на наблюдаемом потоке коммуникаций.
## Возможности
- построение направленного взвешенного графа коммуникаций;
- поддержка личных сообщений, групповых сообщений и ответов;
- агрегация сообщений по рёбрам с сохранением временных меток;
- расчёт узловых и глобальных SNA-метрик;
- выявление изоляции по четырём группам признаков;
- объяснение результата через сработавшие критерии и текстовые причины;
- генерация воспроизводимого синтетического датасета с ground truth;
- сравнение с простыми базовыми алгоритмами;
- экспорт CSV, GEXF, PNG и JSON-отчётов.
## Структура
| Файл | Назначение |
| --- | --- |
| `models.py` | `MessageRecord`, `CommunicationGraph`, типы событий и агрегированные рёбра |
| `metrics.py` | `NodeMetrics`, `GlobalMetrics`, расчёт SNA-метрик |
| `isolation_detector.py` | конфигурация и алгоритм обнаружения изоляции |
| `synthetic_generator.py` | синтетические профили и эталонная разметка |
| `dataset.py` | импорт и экспорт CSV |
| `visualize.py` | PNG-граф коммуникаций и график компонент риска |
| `run_research.py` | полный воспроизводимый эксперимент |
| `results/` | результаты последнего запуска исследования |
Публичные объекты также экспортируются из `communication_graph_analysis`:
```python
from communication_graph_analysis import (
    CommunicationGraph,
    IsolationConfig,
    MessageRecord,
    compute_global_metrics,
    compute_node_metrics,
    detect_isolated_users,
)
```
## Установка
Зависимости модуля входят в общий `requirements.txt` репозитория. Для отдельной
проверки удобно использовать виртуальное окружение:
```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
```
Ключевые библиотеки:
- `networkx` — графовая модель и SNA-метрики;
- `numpy` — численные операции и перцентили;
- `pandas` — табличные отчёты;
- `matplotlib` — визуализация;
- `scipy` — backend некоторых алгоритмов NetworkX, включая PageRank.
## Модель данных
Каждое событие переписки описывается `MessageRecord`:
```python
from datetime import datetime
from communication_graph_analysis.models import (
    EVENT_DIRECT,
    MessageRecord,
)
record = MessageRecord(
    sender="employee_01",
    recipient="employee_02",
    chat_id="dm_employee_01_employee_02",
    timestamp=datetime(2026, 1, 15, 10, 30),
    event_type=EVENT_DIRECT,
    length_chars=120,
)
```
Поддерживаются следующие типы событий:
| Тип | `recipient` | Семантика |
| --- | --- | --- |
| `direct` | обязателен | личное сообщение `sender → recipient` |
| `reply` | обязателен | ответ `sender → recipient`; дополнительно увеличивает `reply_weight` |
| `group` | обычно `None` | сообщение в групповой чат, транслируемое остальным участникам |
Для группового сообщения участники определяются по пользователям, которые
встречаются в событиях с тем же `chat_id`. При загрузке полного лога
`CommunicationGraph` предварительно собирает участников всех сообщений, поэтому
результат не зависит от порядка строк. В прикладном логе каждый участник группы
должен быть представлен хотя бы одним событием.
### Граф
Граф `G = (V, E)` — `networkx.DiGraph`:
- узел — пользователь;
- направленное ребро `u → v` — сообщение от `u` к `v`;
- `weight` — число всех сообщений на ребре;
- `personal_weight` — число `direct` и `reply` событий;
- `group_weight` — число событий, возникших из групповой коммуникации;
- `reply_weight` — число ответов;
- `timestamps` — список времён событий;
- `first_seen` и `last_seen` — границы активности ребра.
Пример построения графа:
```python
from datetime import datetime, timedelta
from communication_graph_analysis import CommunicationGraph, MessageRecord
start = datetime(2026, 1, 1, 9, 0)
messages = [
    MessageRecord("alice", "bob", "dm-1", start),
    MessageRecord(
        "bob", "alice", "dm-1",
        start + timedelta(minutes=10),
        event_type="reply",
    ),
]
graph = CommunicationGraph(messages, window_days=7)
print(graph.n_users, graph.n_edges, graph.time_range)
```
## Импорт и экспорт CSV
Формат CSV:
```text
sender,recipient,chat_id,timestamp,event_type,length_chars
alice,bob,dm-1,2026-01-01 09:00:00,direct,120
bob,alice,dm-1,2026-01-01 09:10:00,reply,80
alice,,team,2026-01-01 10:00:00,group,200
```
Обязательные колонки: `sender`, `recipient`, `chat_id`, `timestamp`.
`event_type` по умолчанию равен `direct`, `length_chars` — `0`.
Поддерживаются ISO 8601 и формат `%Y-%m-%d %H:%M:%S`.
```python
from communication_graph_analysis import (
    CommunicationGraph,
    load_messages_csv,
    save_messages_csv,
)
messages = load_messages_csv("messages.csv")
graph = CommunicationGraph(messages)
save_messages_csv(graph.messages, "results/messages-copy.csv")
```
## Расчёт метрик
```python
from communication_graph_analysis import (
    compute_global_metrics,
    compute_node_metrics,
)
node_metrics = compute_node_metrics(graph)
global_metrics = compute_global_metrics(graph)
alice = node_metrics["alice"]
print(alice.out_weight, alice.in_weight)
print(alice.personal_out_weight, alice.personal_in_weight)
print(alice.mutual_partners, alice.reply_in_weight)
print(global_metrics.density, global_metrics.reciprocity)
```
### Узловые признаки
`NodeMetrics` включает:
- `in_degree`, `out_degree` — число уникальных входящих и исходящих партнёров;
- `in_weight`, `out_weight` — объём всех входящих и исходящих событий;
- `personal_in_weight`, `personal_out_weight` — объём личной переписки без
  группового шума;
- `mutual_partners` — число партнёров с двусторонней личной связью;
- `reply_in_weight`, `reply_out_weight` — число ответов;
- `degree_centrality`, `betweenness`, `closeness`, `pagerank`,
  `clustering`;
- `active_days`, `last_seen_gap_days`, `max_silence_days`,
  `silence_gaps`, `mean_burstiness`.
Closeness рассчитывается на неориентированной проекции графа: структурная
близость не зависит от направления сообщения. Направленность анализируется
отдельно через входящие/исходящие объёмы, взаимность и ответы.
## Алгоритм обнаружения изоляции
Основная функция:
```python
from communication_graph_analysis import (
    IsolationConfig,
    detect_isolated_users,
)
config = IsolationConfig(
    window_days=7,
    score_threshold=0.30,
)
assessments = detect_isolated_users(graph, config)
for item in assessments:
    print(item.user, item.score, item.isolated, item.reasons)
```
Результат — список `IsolationAssessment`, отсортированный по убыванию
`score`. Для табличного представления:
```python
from communication_graph_analysis.isolation_detector import summary_table
report = summary_table(assessments)
report.to_csv("results/isolation_report.csv")
```
### Критерий К1: дефицит исходящей инициативы
Проверяется активность пользователя в последнем окне длиной `window_days`:
- среднее число исходящих сообщений в сутки;
- число уникальных адресатов.
К1 срабатывает, если выполняется хотя бы одно условие:
```text
average_outgoing_per_day <= theta_a
или
out_degree <= theta_d
```
Сообщения считаются по индивидуальным `timestamps`, а не по всему ребру. Поэтому
старые сообщения не попадают в последнее окно только потому, что у ребра было
более позднее событие.
### Критерий К2: асимметрия потока
К2 предназначен для выявления односторонних коммуникаций:
- пользователь почти только получает сообщения;
- пользователь пишет без ответов;
- личного диалога практически нет.
Используются только `personal_in_weight` и `personal_out_weight`; групповые
сообщения не должны создавать ложное ощущение вовлечённости. Индекс взаимности:
```text
R(u) = min(personal_in, personal_out)
       / (personal_in + personal_out + 1)
```
Ответы учитываются отдельно через `reply_weight`. Наличие обратного ребра без
ответных событий не считается полноценным диалогическим откликом.
### Критерий К3: временная фрагментация
К3 учитывает:
- максимальную паузу между событиями;
- паузу от последнего события до конца наблюдения;
- долю активных дней;
- деградацию активности между первой и последней частью периода.
Критерий срабатывает при длинной паузе или длительном молчании до конца
периода, если доля активных дней не превышает `theta_e`.
### Критерий К4: периферийность
К4 использует PageRank и closeness. Перцентиль PageRank вычисляется для
крупнейшей слабосвязной компоненты графа. Пользователь считается структурно
периферийным, если его PageRank находится ниже `pagerank_percentile`, а
closeness ниже `theta_c`.
К4 является уточняющим признаком и не является обязательным для классификации.
### Итоговый score
Для каждого пользователя вычисляются нормированные компоненты `f1..f4`:
```text
IsolationScore =
    beta_1 * f1 +
    beta_2 * f2 +
    beta_3 * f3 +
    beta_4 * f4
```
Текущая конфигурация по умолчанию:
| Параметр | Значение | Назначение |
| --- | ---: | --- |
| `window_days` | `7` | размер последнего окна |
| `theta_a` | `0.5` | порог исходящих сообщений в сутки |
| `theta_d` | `2` | минимальный исходящий охват |
| `theta_r` | `0.15` | порог взаимности |
| `mu_out` | `30` | ориентир нормального личного исходящего объёма |
| `mu_in` | `60` | ориентир нормального личного входящего объёма |
| `theta_m` | `2` | допустимое число взаимных партнёров |
| `theta_s` | `5` | порог максимальной паузы, дни |
| `theta_l` | `4` | порог молчания до конца, дни |
| `theta_e` | `0.5` | минимальная доля активных дней |
| `pagerank_percentile` | `10` | нижний перцентиль PageRank |
| `theta_c` | `0.15` | порог closeness |
| `weights` | `(0.30, 0.40, 0.25, 0.05)` | веса К1–К4 |
| `score_threshold` | `0.30` | порог итогового score |
| `required_criteria` | `1` | минимум критериев К1–К3 |
Боты и каналы массовых рассылок по умолчанию исключаются, если их исходящий
охват составляет не менее `bot_out_degree_share` и входящий объём равен нулю.
## Полный исследовательский запуск
Из корня репозитория:
```bash
python -m communication_graph_analysis.run_research
```
Параметры:
```bash
python -m communication_graph_analysis.run_research \
  --days 30 \
  --seed 42 \
  --window-days 7
```
- `--days` — длина синтетического периода;
- `--seed` — seed генератора для воспроизводимости;
- `--window-days` — длина последнего окна анализа.
Сценарий выполняет пять шагов:
1. генерирует синтетический датасет;
2. строит граф и считает глобальные/узловые метрики;
3. запускает детектор изоляции;
4. сравнивает его с базовыми методами;
5. строит визуализации и экспортирует граф.
### Профили синтетического генератора
Генератор создаёт следующие профили:
| Профиль | Описание | Ground truth |
| --- | --- | --- |
| `active` | регулярная взаимная переписка | не изолирован |
| `hub` | высокий входящий и исходящий охват | не изолирован |
| `introvert` | мало пишет, но получает личные сообщения и отвечает | не изолирован |
| `drifting` | активен в начале, затем замолкает | изолирован |
| `peripheral` | получает групповые оповещения, почти не инициирует общение | изолирован |
| `ignored` | пишет другим без устойчивых ответов | изолирован |
| `bot` | массовая рассылка без входящего потока | исключается |
Пример прямого использования:
```python
from communication_graph_analysis import generate_synthetic_dataset
graph, labels = generate_synthetic_dataset(
    days=30,
    seed=42,
    with_bot=True,
)
```
## Выходные файлы
По умолчанию файлы сохраняются в `communication_graph_analysis/results/`:
| Файл | Содержимое |
| --- | --- |
| `messages.csv` | синтетический лог событий |
| `metrics_global.json` | глобальные метрики графа |
| `node_metrics.csv` | метрики каждого пользователя |
| `isolation_report.csv` | score, критерии, компоненты и причины |
| `baseline_comparison.csv` | TP/FP/FN/TN, precision, recall, F1, accuracy |
| `scores_by_profile.csv` | средний score по синтетическим профилям |
| `graph.png` | граф коммуникаций |
| `scores.png` | компоненты риска для пользователей с наибольшим score |
| `graph.gexf` | граф для Gephi и других совместимых инструментов |
## Проверка и тесты
Focused-тесты модуля:
```bash
pytest -q tests/test_communication_isolation.py
```
Тесты проверяют:
- корректный подсчёт сообщений в последнем окне;
- использование `reply_weight` при оценке диалога;
- корректный учёт участников группового чата независимо от порядка событий;
- разделение входящих и исходящих ответов;
- separation synthetic-профилей при конфигурации по умолчанию.
Для полного набора тестов репозитория требуется настроенная инфраструктура
приложения, включая `TEST_DATABASE_URL`.
## Ограничения и интерпретация
1. **Это наблюдательная модель.** Отсутствие сообщений не доказывает отсутствие
   рабочих контактов: коммуникация может проходить вне анализируемого
   мессенджера.
2. **Групповой чат — приближение.** Сообщение транслируется участникам,
   известным по событиям с тем же `chat_id`; явный справочник членства в текущем
   API отсутствует.
3. **Пороговые значения не универсальны.** `IsolationConfig` нужно калибровать
   под размер команды, частоту сообщений, типы чатов и длину наблюдения.
4. **Синтетический F1 не переносится автоматически на production.** Идеальная
   метрика на фиксированном seed показывает согласованность с заданным
   ground truth, но не качество на реальных данных.
5. **Анонимизация обязательна.** Для реального использования следует применять
   псевдонимы пользователей, ограничивать доступ к исходным логам и хранить
   только необходимые признаки.
6. **Временная зона должна быть согласована.** Все события одного графа должны
   использовать совместимые `datetime`; смешивание naive и timezone-aware
   значений приведёт к ошибкам сравнения.
7. **Калибровка требует валидации.** Порог `score_threshold` и веса нужно
   оценивать на отложенной разметке, а не подбирать только по одному
   синтетическому запуску.
## Минимальный production-пайплайн
```python
from communication_graph_analysis import (
    CommunicationGraph,
    IsolationConfig,
    detect_isolated_users,
    load_messages_csv,
)
messages = load_messages_csv("anonymized_messages.csv")
graph = CommunicationGraph(messages, window_days=14)
config = IsolationConfig(
    window_days=14,
    score_threshold=0.35,
    required_criteria=1,
)
assessments = detect_isolated_users(graph, config)
for item in assessments:
    if item.isolated:
        print({
            "user": item.user,
            "score": round(item.score, 3),
            "reasons": item.reasons,
        })
```
Рекомендуется сохранять не только список срабатываний, но и полный список
`IsolationAssessment`: он нужен для аудита, сравнения периодов и разбора
ложных срабатываний.
## Интеграция с приложением Messenger
В репозитории есть административный endpoint, который строит анализ напрямую
из таблиц приложения `messages`, `chats` и `group_chat_members`:
```http
GET /api/v1/analysis/isolation?days=30&window_days=7
Authorization: Bearer <admin-access-token>
```
Endpoint доступен только пользователю с ролью `admin`. Он возвращает JSON с
периодом анализа и отсортированным списком оценок:
```json
{
  "period_start": "2026-10-01T12:00:00Z",
  "period_end": "2026-10-31T12:00:00Z",
  "window_days": 7,
  "users": [
    {
      "user_id": "…",
      "score": 0.61,
      "isolated": true,
      "is_bot": false,
      "criterion_c1": false,
      "criterion_c2": true,
      "criterion_c3": true,
      "criterion_c4": false,
      "f1": 0.12,
      "f2": 0.88,
      "f3": 0.71,
      "f4": 0.0,
      "personal_in_weight": 2,
      "personal_out_weight": 29,
      "mutual_partners": 0,
      "max_silence_days": 8.4,
      "last_seen_gap_days": 0.4,
      "reasons": [
        "К2: flow asymmetry R=0.06, personal responses=0 → unanswered broadcaster",
        "К3: temporal fragmentation (…) "
      ]
    }
  ]
}
```
Пример вызова:
```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  "http://localhost:8000/api/v1/analysis/isolation?days=30&window_days=7"
```
Интеграция не выгружает содержимое сообщений: в анализ передаются только
идентификаторы, тип чата, timestamps и длина текста. Групповые чаты используют
явное членство из `group_chat_members`, поэтому участник учитывается даже если
он не отправлял сообщений в выбранном периоде. Текущая схема приложения не
хранит отдельное поле `is_reply`; такие сообщения анализируются как `direct`,
пока в модель сообщений не будет добавлен признак ответа.