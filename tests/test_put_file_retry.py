"""
Regression test: _put_file must retry on a 409/422 conflict (stale SHA) instead
of silently dropping the write — the race that lost a finished backtest report
while the bot pushed several files at once.
"""
from unittest.mock import patch, MagicMock
from src.monitoring.heartbeat import Heartbeat


def _resp(status_ok, code, sha="abc"):
    m = MagicMock()
    m.ok = status_ok
    m.status_code = code
    m.json.return_value = {"sha": sha}
    return m


def test_put_file_retries_on_conflict():
    hb = Heartbeat()
    hb.token = "x"
    get_resp = _resp(True, 200)
    # PUT: first a 409 conflict, then success
    put_responses = [_resp(False, 409), _resp(True, 201)]
    with patch("src.monitoring.heartbeat.requests.get", return_value=get_resp), \
         patch("src.monitoring.heartbeat.requests.put", side_effect=put_responses) as put_mock, \
         patch("src.monitoring.heartbeat.time.sleep"):
        ok = hb._put_file("x.md", b"data", "msg")
    assert ok is True
    assert put_mock.call_count == 2            # retried after the conflict


def test_put_file_gives_up_after_attempts():
    hb = Heartbeat()
    hb.token = "x"
    with patch("src.monitoring.heartbeat.requests.get", return_value=_resp(True, 200)), \
         patch("src.monitoring.heartbeat.requests.put", return_value=_resp(False, 409)), \
         patch("src.monitoring.heartbeat.time.sleep"):
        ok = hb._put_file("x.md", b"data", "msg", attempts=3)
    assert ok is False


def test_put_file_no_token_returns_false():
    hb = Heartbeat()
    hb.token = ""
    assert hb._put_file("x.md", b"d", "m") is False
