"""test_reconnect.py — ShowdownClient reconnect / backoff loop.

Regression for the live failure during the 0.7.x ladder runs: a transient
DNS / network blip raised ``socket.gaierror`` inside ``connect()`` and, with
no retry, killed the process (the supervising wrapper had to restart it).
``run()`` now retries with exponential backoff and reconnects automatically
when an established stream drops.

No pytest-asyncio in this repo, so coroutines are driven with ``asyncio.run``
and the network is fully mocked (``connect`` / ``asyncio.sleep`` patched), so
these tests touch no sockets and never really sleep.
"""
from __future__ import annotations

import asyncio
import socket
from unittest.mock import patch, MagicMock, AsyncMock

from main import (
    ShowdownClient,
    RECONNECT_DELAY_INITIAL,
    RECONNECT_DELAY_MAX,
)


class _FakeWS:
    """Async-iterable websocket stub: yields *messages* then the stream ends."""

    def __init__(self, messages=()):
        self._messages = list(messages)

    def __aiter__(self):
        return self._gen()

    async def _gen(self):
        for m in self._messages:
            yield m

    async def close(self):
        pass


class TestReconnectBackoff:
    def test_connect_retries_with_exponential_backoff_capped(self):
        """Repeated connect failures back off 5→10→20…→300 (capped), and the
        loop exits once _stopping is set."""
        client = ShowdownClient()
        delays: list[float] = []

        async def fail_connect():
            raise socket.gaierror(11001, "getaddrinfo failed")

        async def fake_sleep(d):
            delays.append(d)
            if len(delays) >= 8:
                client._stopping = True   # let the loop terminate

        with patch.object(client, "connect", side_effect=fail_connect), \
             patch("main.asyncio.sleep", side_effect=fake_sleep):
            asyncio.run(client.run())

        assert delays == [5, 10, 20, 40, 80, 160, 300, 300]
        assert delays[0] == RECONNECT_DELAY_INITIAL
        assert max(delays) == RECONNECT_DELAY_MAX

    def test_reconnects_after_stream_drops(self):
        """A dropped/ended stream triggers a state reset and a fresh connect
        rather than killing the loop."""
        client = ShowdownClient()
        n = {"connects": 0}

        async def ok_connect():
            n["connects"] += 1
            client.ws = _FakeWS([])          # empty stream → ends immediately
            if n["connects"] >= 2:
                client._stopping = True

        reset_spy = MagicMock(wraps=client._reset_connection_state)
        with patch.object(client, "connect", side_effect=ok_connect), \
             patch.object(client, "_reset_connection_state", reset_spy), \
             patch("main.asyncio.sleep", new=AsyncMock()):
            asyncio.run(client.run())

        assert n["connects"] == 2          # reconnected after the first drop
        assert reset_spy.call_count == 1   # state reset between the two connects

    def test_backoff_resets_after_a_successful_connect(self):
        """Connect fails twice (backoff grows), then succeeds; the next drop
        must restart backoff from INITIAL, not the grown value."""
        client = ShowdownClient()
        delays: list[float] = []
        seq = iter([False, False, True])   # connect outcomes: fail, fail, succeed

        async def flaky_connect():
            if next(seq):
                client.ws = _FakeWS([])    # success → stream ends → reconnect
                client._stopping = True    # stop after the successful leg
            else:
                raise OSError("refused")

        async def fake_sleep(d):
            delays.append(d)

        with patch.object(client, "connect", side_effect=flaky_connect), \
             patch("main.asyncio.sleep", side_effect=fake_sleep):
            asyncio.run(client.run())

        # Two failures before success → backoff 5, 10 recorded.
        assert delays == [5, 10]


class TestResetConnectionState:
    def test_clears_per_connection_state(self):
        client = ShowdownClient()
        client.parsers["b1"] = object()
        client.finished_battles.add("b1")
        client._joining_battles.add("b2")
        client._recorders["b1"] = object()
        client._requeue_pending = True
        task = MagicMock()
        task.done.return_value = False
        client._requeue_task = task
        client.ws = object()

        client._reset_connection_state()

        task.cancel.assert_called_once()
        assert client._requeue_task is None
        assert client._requeue_pending is False
        assert client.parsers == {}
        assert client.finished_battles == set()
        assert client._joining_battles == set()
        assert client._recorders == {}
        assert client.ws is None

    def test_elo_tracker_preserved_across_reset(self):
        """Cross-session ELO state must survive a reconnect."""
        client = ShowdownClient()
        elo = client._elo
        client._reset_connection_state()
        assert client._elo is elo


class TestShutdownStopsLoop:
    def test_shutdown_sets_stopping_flag(self):
        client = ShowdownClient()
        asyncio.run(client.shutdown())
        assert client._stopping is True
