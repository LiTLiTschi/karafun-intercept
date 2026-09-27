import asyncio

from textual.widgets import OptionList, Static

from karafun_intercept.app import KaraFunInterceptApp
from karafun_intercept.xml_proto import parse_status


def _run(coro, timeout=2.0):
    return asyncio.run(asyncio.wait_for(coro, timeout))


def test_first_snap_renders_current_queue_singers(status1_xml):
    app = KaraFunInterceptApp()

    async def main():
        async with app.run_test() as pilot:
            app.feed_snapshot(parse_status(status1_xml))
            await pilot.pause()
            cur = str(app.query_one("#current", Static).content).lower()
            assert "song a" in cur and "artist a" in cur and "playing" in cur
            ql = app.query_one("#queue", OptionList)
            assert ql.option_count == 2
            qlabels = [str(ql.get_option_at_index(i).prompt) for i in range(ql.option_count)]
            assert any("song a" in s.lower() for s in qlabels)
            sl = app.query_one("#singers", OptionList)
            slabels = [str(sl.get_option_at_index(i).prompt) for i in range(sl.option_count)]
            assert any("alice" in s.lower() for s in slabels)
            assert any("bob" in s.lower() for s in slabels)
            # NewSinger + TurnAdvanced for Alice/Bob land in the banner.
            note = str(app.query_one("#notifications", Static).content).lower()
            assert "alice" in note

    _run(main())


def test_new_song_produces_notification(status1_xml, status2_xml):
    app = KaraFunInterceptApp()

    async def main():
        async with app.run_test() as pilot:
            app.feed_snapshot(parse_status(status1_xml))
            app.feed_snapshot(parse_status(status2_xml))
            await pilot.pause()
            note = str(app.query_one("#notifications", Static).content).lower()
            assert "bob" in note  # NewSinger + TurnAdvanced for Bob
            assert "song b" in str(app.query_one("#current", Static).content).lower()

    _run(main())


def test_empty_snapshot_renders_idle():
    app = KaraFunInterceptApp()
    idle = parse_status('<status state="idle"><queue></queue></status>')

    async def main():
        async with app.run_test() as pilot:
            app.feed_snapshot(idle)
            await pilot.pause()
            assert "idle" in str(app.query_one("#current", Static).content).lower()
            assert app.query_one("#queue", OptionList).option_count == 0
            assert app.query_one("#singers", OptionList).option_count == 0

    _run(main())


def test_refresh_action_renames_current(status1_xml):
    app = KaraFunInterceptApp()

    async def main():
        async with app.run_test() as pilot:
            app.feed_snapshot(parse_status(status1_xml))
            await pilot.pause()
            app.action_refresh()
            await pilot.pause()
            assert "song a" in str(app.query_one("#current", Static).content).lower()

    _run(main())
