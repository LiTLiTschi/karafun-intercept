from karafun_intercept.model import SessionModel
from karafun_intercept.xml_proto import parse_status


def _idle_status():
    return parse_status('<status state="idle"><queue></queue></status>')


def _kinds(notes):
    """Order-independent check of notification (kind, singer), ignoring timestamps."""
    return [(type(n).__name__, n.singer) for n in notes]


def test_first_status_emits_new_singers_and_turn(status1_xml):
    m = SessionModel()
    notes = m.apply_status(parse_status(status1_xml))
    assert _kinds(notes) == [
        ("NewSinger", "Alice"),
        ("NewSinger", "Bob"),
        ("TurnAdvanced", "Alice"),
    ]
    assert m.current_singer == "Alice"
    assert m.current_song == ("Song A", "Artist A")
    assert m.position == 12
    assert m.tempo == 100
    assert m.queue[0].title == "Song A"
    assert m.known_singers == {"Alice", "Bob"}
    assert m.state == "playing"


def test_second_status_emits_new_singer_and_turn(status1_xml, status2_xml):
    m = SessionModel()
    m.apply_status(parse_status(status1_xml))
    notes = m.apply_status(parse_status(status2_xml))
    # Bob already known; Cara is new. Front moves Alice -> Bob.
    assert _kinds(notes) == [
        ("NewSinger", "Cara"),
        ("TurnAdvanced", "Bob"),
    ]
    assert m.current_singer == "Bob"
    assert m.current_song == ("Song B", "Artist B")


def test_no_change_is_silent(status1_xml):
    m = SessionModel()
    m.apply_status(parse_status(status1_xml))
    # Same status again: all singers known, front unchanged -> no notifications.
    assert m.apply_status(parse_status(status1_xml)) == []


def test_singer_recency_tracks_all_singers(status1_xml, status2_xml):
    m = SessionModel()
    m.apply_status(parse_status(status1_xml))
    m.apply_status(parse_status(status2_xml))
    assert set(m.singer_recency) == {"Alice", "Bob", "Cara"}
    assert m.current_singer == "Bob"
    assert m.singer_last_seen["Cara"] >= m.singer_first_seen["Cara"]


def test_idle_yields_no_notification(status1_xml):
    m = SessionModel()
    m.apply_status(parse_status(status1_xml))
    notes = m.apply_status(_idle_status())
    assert notes == []  # spec §6 rule 4
    assert m.state == "idle"
    assert m.current_singer is None
    # recencies are retained (roster still shows them)
    assert {"Alice", "Bob"} <= set(m.singer_recency)


def test_absent_singer_not_counted():
    # An unassigned slot (no <singer>) is ignored entirely.
    xml = (
        '<status state="playing"><queue>'
        '<item id="0" status="ready"><title>T</title><artist>A</artist></item>'
        "</queue></status>"
    )
    m = SessionModel()
    notes = m.apply_status(parse_status(xml))
    assert notes == []
    assert m.current_singer is None
    assert m.known_singers == set()
    assert m.singer_recency == []
