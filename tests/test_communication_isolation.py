from datetime import datetime, timedelta
from communication_graph_analysis.isolation_detector import (
    IsolationConfig,
    detect_isolated_users,
)
from communication_graph_analysis.models import (
    EVENT_DIRECT,
    EVENT_GROUP,
    EVENT_REPLY,
    CommunicationGraph,
    MessageRecord,
)
from communication_graph_analysis.synthetic_generator import (
    ISOLATED_PROFILES,
    generate_synthetic_dataset,
)
def message(sender, recipient, timestamp, event_type=EVENT_DIRECT, chat_id="dm"):
    return MessageRecord(
        sender=sender,
        recipient=recipient,
        chat_id=chat_id,
        timestamp=timestamp,
        event_type=event_type,
    )
def assessment_for(graph, user, **kwargs):
    assessments = detect_isolated_users(
        graph,
        IsolationConfig(
            score_threshold=0.0,
            required_criteria=0,
            exclude_bots=False,
            **kwargs,
        ),
    )
    return next(item for item in assessments if item.user == user)
def test_last_window_counts_messages_not_whole_edges():
    start = datetime(2026, 1, 1)
    graph = CommunicationGraph(
        [
            *(
                message("u", "v", start + timedelta(days=i))
                for i in range(5)
            ),
            message("u", "v", start + timedelta(days=9)),
            message("v", "u", start + timedelta(days=9, hours=1)),
        ]
    )
    assessment = assessment_for(graph, "u", window_days=2)
    assert any("0.50 msg/day" in reason for reason in assessment.reasons)
def test_reply_weight_is_used_for_dialogue_evidence():
    start = datetime(2026, 1, 1)
    graph = CommunicationGraph(
        [
            message("u", "v", start, EVENT_DIRECT),
            message("v", "u", start + timedelta(hours=1), EVENT_DIRECT),
        ]
    )
    assessment = assessment_for(graph, "u")
    assert assessment.metrics.mutual_partners == 1
    assert any("personal responses=0" in reason for reason in assessment.reasons)
def test_group_members_are_known_independently_of_message_order():
    start = datetime(2026, 1, 1)
    graph = CommunicationGraph(
        [
            message("core", None, start, EVENT_GROUP, "team"),
            message("peripheral", None, start + timedelta(days=1), EVENT_GROUP, "team"),
        ]
    )
    assert graph.graph.has_edge("core", "peripheral")
    assert graph.graph.has_edge("peripheral", "core")
def test_reply_events_are_recorded_as_incoming_dialogue():
    start = datetime(2026, 1, 1)
    graph = CommunicationGraph(
        [
            message("u", "v", start, EVENT_DIRECT),
            message("v", "u", start + timedelta(hours=1), EVENT_REPLY),
        ]
    )
    metrics = assessment_for(graph, "u").metrics
    assert metrics.reply_in_weight == 1
    assert metrics.reply_out_weight == 0
def test_synthetic_profiles_are_separated_by_default_configuration():
    graph, labels = generate_synthetic_dataset(seed=42, days=30)
    assessments = detect_isolated_users(graph)
    by_user = {item.user: item for item in assessments}
    assert all(
        by_user[user].isolated
        for user, label in labels.items()
        if label["profile"] in ISOLATED_PROFILES
    )
    assert all(
        not by_user[user].isolated
        for user, label in labels.items()
        if label["profile"] == "introvert"
    )