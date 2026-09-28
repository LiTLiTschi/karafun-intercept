import datetime as dt
import logging

import pytest


@pytest.fixture(autouse=True)
def restore_logging():
    """Save and restore the root logger's handlers/level after each test."""
    root = logging.getLogger()
    saved_handlers = root.handlers[:]
    saved_level = root.level
    yield
    for h in root.handlers:
        if h not in saved_handlers:
            h.close()
    root.handlers = saved_handlers
    root.level = saved_level


@pytest.fixture
def fake_now():
    """Deterministic clock; advance via monkeypatching this callable if needed."""
    base = dt.datetime(2026, 1, 1, 12, 0, 0, tzinfo=dt.timezone.utc)
    state = {"t": base}

    def now():
        return state["t"]

    def _advance(delta: dt.timedelta):
        state["t"] = state["t"] + delta

    now.advance = _advance  # type: ignore[attr-defined]
    now.base = base  # type: ignore[attr-defined]
    return now


# Recorded XML fragments captured against the live player (see Open Question 11).
STATUS1_XML = """\
<status state="playing">
  <position>12</position>
  <volumeList><general caption="General">80</general></volumeList>
  <pitch>0</pitch>
  <tempo>100</tempo>
  <queue>
    <item id="0" status="ready">
      <title>Song A</title> <artist>Artist A</artist>
      <year>2020</year> <duration>180</duration>
      <singer>Alice</singer>
    </item>
    <item id="1" status="ready">
      <title>Song B</title> <artist>Artist B</artist>
      <year>2019</year> <duration>200</duration>
      <singer>Bob</singer>
    </item>
  </queue>
</status>"""

STATUS2_XML = """\
<status state="playing">
  <position>20</position>
  <pitch>0</pitch>
  <tempo>100</tempo>
  <queue>
    <item id="0" status="ready">
      <title>Song B</title> <artist>Artist B</artist>
      <year>2019</year> <duration>200</duration>
      <singer>Bob</singer>
    </item>
    <item id="1" status="ready">
      <title>Song C</title> <artist>Artist C</artist>
      <year>2021</year> <duration>190</duration>
      <singer>Cara</singer>
    </item>
  </queue>
</status>
"""


@pytest.fixture
def status1_xml():
    return STATUS1_XML


@pytest.fixture
def status2_xml():
    return STATUS2_XML
