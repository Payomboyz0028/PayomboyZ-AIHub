"""Load Discord only when a caller requests the bot entry points."""

__all__ = ["bot", "start_bot"]


def __getattr__(name):
    if name in __all__:
        from .discord_bot import bot, start_bot

        globals().update(bot=bot, start_bot=start_bot)
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
