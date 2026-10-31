import os
from unittest.mock import MagicMock


def test_isolated_survives_child_death():
    from src.bot import TradingBot
    bot = TradingBot.__new__(TradingBot)
    bot.heartbeat = MagicMock()

    def _boom():
        os._exit(9)
    bot._isolated(_boom)
    name = bot.heartbeat._put_file.call_args[0][0]
    assert name.startswith("experiment") and name.endswith("_results.md")

    bot.heartbeat.reset_mock()
    def _ok():
        pass
    bot._isolated(_ok)
    bot.heartbeat._put_file.assert_not_called()
