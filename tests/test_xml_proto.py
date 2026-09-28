from karafun_intercept.xml_proto import (
    PLAYER_HOST,
    PLAYER_PORT,
    POLL_INTERVAL,
    POLL_TIMEOUT_GAP,
    RECONNECT_MAX_DELAY,
    RECONNECT_MIN_DELAY,
    build_get_status_action,
    parse_status,
)


def test_parse_status_basic(status1_xml):
    s = parse_status(status1_xml)
    assert s.state == "playing"
    assert s.position == 12
    assert s.pitch == 0
    assert s.tempo == 100
    assert len(s.queue) == 2
    first = s.queue[0]
    assert first.id == 0
    assert first.title == "Song A"
    assert first.artist == "Artist A"
    assert first.year == 2020
    assert first.duration == 180
    assert first.singer == "Alice"
    assert first.item_state == "ready"


def test_parse_status_optional_fields():
    # No <position>/<pitch>/<tempo> in this fragment -> all optional/None.
    xml = (
        '<status state="playing">'
        "<queue>"
        '<item id="0" status="ready">'
        "<title>Only</title><artist>Uno</artist><singer>Alice</singer>"
        "</item>"
        "</queue></status>"
    )
    s = parse_status(xml)
    assert s.position is None
    assert s.pitch is None
    assert s.tempo is None
    assert len(s.queue) == 1
    assert s.queue[0].singer == "Alice"


def test_parse_status_singer_absent_when_missing():
    s = parse_status('<status state="idle"><queue></queue></status>')
    assert s.state == "idle"
    assert s.queue == []


def test_build_get_status_action_has_no_queue():
    xml = build_get_status_action(noqueue=False)
    assert xml == '<action type="getStatus"></action>'


def test_build_get_status_action_noqueue():
    xml = build_get_status_action(noqueue=True)
    assert xml == '<action type="getStatus" noqueue></action>'


def test_constants():
    assert PLAYER_HOST == "127.0.0.1"
    assert PLAYER_PORT == 57570
    assert POLL_INTERVAL == 2.0
    assert POLL_TIMEOUT_GAP == 3.0
    assert RECONNECT_MIN_DELAY == 5.0
    assert RECONNECT_MAX_DELAY == 30.0
