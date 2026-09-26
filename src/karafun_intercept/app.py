"""Minimal Textual TUI application."""

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Static


class KarafunInterceptApp(App):
    """Karafun Intercept."""

    CSS = """
    Screen {
        layout: vertical;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Karafun Intercept")
        yield Footer()


def main() -> None:
    """Entry point for the karafun-intercept TUI."""
    KarafunInterceptApp().run()


if __name__ == "__main__":
    main()
