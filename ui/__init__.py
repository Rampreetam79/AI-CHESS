"""User interfaces for the chess application."""

__all__ = ["ChessGUI"]


def __getattr__(name: str):
    """Load the optional Pygame GUI only when it is explicitly requested."""
    if name == "ChessGUI":
        from .gui import ChessGUI

        return ChessGUI
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
