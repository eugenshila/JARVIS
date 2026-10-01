"""
Tests for the resumption-handle recovery ladder in main.py.

Runs standalone (`python tests/test_resumption_recovery.py`) as well as under
pytest, like the rest of the suite — the point is that anyone can verify the
recovery rules without installing the hardware stack.

The incident these tests are written against (2026-10-01): a websocket close
1011 "Internal error encountered" from the Gemini Live server dropped the
session mid-conversation. The error surfaced inside the session TaskGroup, so
the run loop caught an ExceptionGroup whose own message is boilerplate —
"unhandled errors in a TaskGroup" — and "unhandled" contains the substring
"handle". The old "handle rejected" check matched that boilerplate, so EVERY
mid-session failure (a transient 1011 above all) threw away a perfectly good
resumption handle and the conversation started over.

The rules now under test:

  * a transient server error (1011 / 5xx / overloaded) with retry budget left
    reconnects WITH the handle — the conversation survives the blip;
  * a second consecutive transient failure, or an explicit server refusal of
    the handle, drops it and starts fresh — a handle the server keeps
    refusing must never wedge recovery;
  * everything else (network blip, quota, audio device errors) leaves the
    handle alone: the next connect still tries to resume.

Two layers: the helper/decision tests raise the same APIError objects the
server does; the end-to-end class then drives the REAL JarvisLive.run() loop
with a scripted fake Live client (hardware tasks neutralized) and replays the
incident through the actual ladder, asserting on the handle, the retry budget
and what the user sees.

The heavy imports (audio, Qt, system stats) are mocked so main.py loads on a
bare Python install; google-genai is real, because the tests raise the same
APIError objects the server does.
"""

from __future__ import annotations

import asyncio
import contextlib
import io
import sys
import time
import unittest
from unittest import mock

# main.py imports the whole hardware stack; mock the heavy modules so the
# module loads on a bare install. google-genai stays real — its APIError is
# the exact exception class the incident produced.
for _name in ("sounddevice", "numpy", "psutil",
              "PyQt6", "PyQt6.QtCore", "PyQt6.QtGui", "PyQt6.QtWidgets", "ui"):
    sys.modules.setdefault(_name, mock.MagicMock(name=_name))

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from google.genai import errors as _genai_errors        # noqa: E402

import main                                            # noqa: E402


def _api_error(code: int, message: str):
    """An APIError shaped the way the SDK raises it for a websocket close:
    `raise_error(code, close_reason, None)`."""
    return _genai_errors.APIError(code, message, None)


def _taskgroup_error(exc: BaseException) -> BaseException:
    """Raise `exc` inside a real asyncio.TaskGroup and return the group the
    run loop's `except BaseException` would catch — the same wrapping the
    incident's 1011 went through on its way to the ladder."""
    async def boom():
        raise exc

    async def driver():
        async with asyncio.TaskGroup() as tg:
            tg.create_task(boom())
            await asyncio.sleep(30)   # cancelled when the task fails

    try:
        asyncio.run(driver())
    except BaseException as group:
        return group
    raise AssertionError("TaskGroup did not propagate the exception")


def _err_1011() -> Exception:
    """The exact error from the incident log."""
    return _api_error(1011, "Internal error encountered")


class TestLeafExceptions(unittest.TestCase):
    """Unwrapping the TaskGroup group without touching its boilerplate."""

    def test_bare_exception_is_its_own_leaf(self):
        err = _err_1011()
        self.assertEqual(main._leaf_exceptions(err), [err])

    def test_flat_group_is_flattened(self):
        inner = [_err_1011(), OSError("network went away")]
        group = ExceptionGroup("session tasks failed", inner)
        self.assertEqual(main._leaf_exceptions(group), inner)

    def test_nested_groups_flatten_in_order(self):
        first = _err_1011()
        deep = ValueError("deep")
        group = ExceptionGroup("outer", [
            first,
            ExceptionGroup("inner", [deep]),
        ])
        self.assertEqual(main._leaf_exceptions(group), [first, deep])

    def test_real_taskgroup_1011_yields_the_apierror_leaf(self):
        group = _taskgroup_error(_err_1011())
        leaves = main._leaf_exceptions(group)
        self.assertEqual(len(leaves), 1)
        self.assertEqual(str(leaves[0]), "1011 None. Internal error encountered")


class TestErrorText(unittest.TestCase):
    """The ladder must match against what the server said, never the group's
    own wrapper text."""

    def test_boilerplate_never_leaks_into_error_text(self):
        # The trap, verbatim: the group's own message contains "handle"
        # inside "unhandled". The unwrapped text must not.
        group = _taskgroup_error(_err_1011())
        self.assertIn("handle", str(group).lower())          # the trap exists
        text = main._error_text(group)
        self.assertNotIn("unhandled", text.lower())
        self.assertNotIn("TaskGroup", text)
        self.assertNotIn("handle", text.lower())             # and is bypassed
        self.assertEqual(text, "1011 None. Internal error encountered")

    def test_duplicate_leaves_are_collapsed(self):
        # Several session tasks routinely raise the same APIError when the
        # socket dies under them; the text should say it once.
        group = ExceptionGroup("dups", [_err_1011(), _err_1011()])
        self.assertEqual(main._error_text(group), "1011 None. Internal error encountered")

    def test_bare_exception_text_matches_str(self):
        err = _api_error(404, "not found")
        self.assertEqual(main._error_text(err), str(err))

    def test_multiple_leaves_are_all_present(self):
        group = ExceptionGroup("mixed", [_err_1011(), OSError("device vanished")])
        text = main._error_text(group)
        self.assertIn("1011", text)
        self.assertIn("device vanished", text)


class TestTransientServerError(unittest.TestCase):
    """Which failures are Google's bad moment rather than a real answer."""

    def test_1011_is_transient(self):
        self.assertTrue(main._is_transient_server_error(_err_1011()))

    def test_1011_inside_taskgroup_is_transient(self):
        # The incident's exact shape: group-wrapped, so str() is boilerplate.
        self.assertTrue(main._is_transient_server_error(_taskgroup_error(_err_1011())))

    def test_http_5xx_is_transient(self):
        for code in (500, 502, 503, 504):
            with self.subTest(code=code):
                self.assertTrue(main._is_transient_server_error(_api_error(code, "oops")))

    def test_internal_error_text_without_a_code_is_transient(self):
        self.assertTrue(main._is_transient_server_error(
            RuntimeError("Internal error encountered, please retry")))

    def test_overloaded_is_transient(self):
        self.assertTrue(main._is_transient_server_error(
            _api_error(503, "The model is overloaded. Please try again later.")))

    def test_quota_429_is_not_transient(self):
        # A real answer, not a hiccup — belongs to the model ladder.
        self.assertFalse(main._is_transient_server_error(_api_error(
            429, "RESOURCE_EXHAUSTED: Quota exceeded for Live API requests.")))

    def test_gone_404_is_not_transient(self):
        self.assertFalse(main._is_transient_server_error(_api_error(
            404, "NOT_FOUND: model not available to this key")))

    def test_handle_rejection_is_not_transient(self):
        self.assertFalse(main._is_transient_server_error(_api_error(
            400, "INVALID_ARGUMENT: session resumption handle expired")))

    def test_network_error_is_not_transient(self):
        self.assertFalse(main._is_transient_server_error(OSError("network went away")))

    def test_mixed_group_is_transient_if_any_leaf_is(self):
        group = ExceptionGroup("mixed", [OSError("device vanished"), _err_1011()])
        self.assertTrue(main._is_transient_server_error(group))

    def test_non_numeric_code_is_ignored(self):
        # Something odd with code="1011" as text must not crash or match.
        self.assertFalse(main._is_transient_server_error(OSError("code said 1011")))


class TestResumeAction(unittest.TestCase):
    """The keep-or-drop decision the ladder acts on, given the retry budget."""

    def test_incident_1011_with_budget_is_retried_with_handle(self):
        # The whole point: group-wrapped 1011, budget unspent -> the
        # conversation is worth one reconnect WITH the handle, not a cold
        # start. (Old behavior: the group boilerplate matched "handle" and
        # the handle was dropped on the spot.)
        group = _taskgroup_error(_err_1011())
        self.assertEqual(main._resume_action(group, retries_left=1), "retry")

    def test_1011_after_budget_spent_drops_handle(self):
        # "Only drop it if the resume fails a second time."
        group = _taskgroup_error(_err_1011())
        self.assertEqual(main._resume_action(group, retries_left=0), "drop")

    def test_explicit_handle_rejection_drops_handle(self):
        err = _api_error(400, "INVALID_ARGUMENT: session resumption handle expired")
        self.assertEqual(main._resume_action(err, retries_left=1), "drop")
        self.assertEqual(main._resume_action(_taskgroup_error(err), retries_left=1), "drop")

    def test_not_found_drops_handle(self):
        self.assertEqual(main._resume_action(
            _api_error(404, "NOT_FOUND"), retries_left=1), "drop")

    def test_network_error_keeps_handle(self):
        # The handle was never tested — dropping it on a network blip would
        # waste the conversation for nothing. The next connect still resumes.
        group = _taskgroup_error(OSError("network went away"))
        self.assertEqual(main._resume_action(group, retries_left=1), "keep")
        self.assertEqual(main._resume_action(group, retries_left=0), "keep")

    def test_quota_error_keeps_handle(self):
        # Quota steps down the model ladder; whether the handle survives the
        # model change is the server's call, decided on the next connect.
        err = _api_error(429, "RESOURCE_EXHAUSTED: Quota exceeded")
        self.assertEqual(main._resume_action(err, retries_left=1), "keep")

    def test_rejection_text_in_any_leaf_drops_handle(self):
        group = ExceptionGroup("mixed", [
            OSError("device vanished"),
            _api_error(400, "INVALID_ARGUMENT: resumption handle not found"),
        ])
        self.assertEqual(main._resume_action(group, retries_left=1), "drop")

    def test_transient_wins_over_rejection_text_when_budget_remains(self):
        # A 1011 whose text mentions neither handle nor resumption is the
        # common case; even if a rejection-looking string rides along, the
        # unspent budget gets the cheap rescue attempt first.
        group = ExceptionGroup("mixed", [_err_1011(), _api_error(400, "INVALID_ARGUMENT")])
        self.assertEqual(main._resume_action(group, retries_left=1), "retry")


class TestRecoveryLoopWiring(unittest.TestCase):
    """The retry budget the run loop carries for the handle it holds."""

    def _jarvis(self):
        # __init__ only touches the mocked UI and reads no hardware, so a
        # bare instance is enough to inspect the budget state. Its plugin
        # discovery is chatty (and harmlessly rejects optional-dependency
        # plugins), so it is muted — a failing __init__ still raises here.
        with contextlib.redirect_stdout(io.StringIO()), \
             contextlib.redirect_stderr(io.StringIO()):
            return main.JarvisLive(ui=mock.MagicMock())

    def test_budget_starts_at_one_shot(self):
        self.assertEqual(main._RESUME_TRANSIENT_RETRIES, 1)
        j = self._jarvis()
        self.assertEqual(j._resume_retries_left, 1)

    def test_budget_is_one_shot_per_handle(self):
        # retry branch decrements; a second transient failure with nothing
        # left must report "drop", which the ladder turns into a fresh start.
        j = self._jarvis()
        group = _taskgroup_error(_err_1011())
        self.assertEqual(main._resume_action(group, j._resume_retries_left), "retry")
        j._resume_retries_left -= 1
        self.assertEqual(main._resume_action(group, j._resume_retries_left), "drop")


# ── End-to-end: the real run() loop, a scripted fake server ──────────────────

class _HarnessDone(Exception):
    """Raised from ui.set_state("SLEEPING") to end run() cleanly.

    KeyboardInterrupt/SystemExit are no good here: raised inside a task step
    they are special-cased by asyncio and tear down the whole event loop.
    run() calls set_state("SLEEPING") at the bottom of every iteration,
    OUTSIDE its try/except, so this ends the loop with an ordinary exception.
    """


_STOP = "STOP"   # script step: arm the exit, then fail the connect generically


class _FakeSession:
    async def receive(self):
        await asyncio.Event().wait()   # neutralized: nothing iterates this

    async def send(self, *a, **k):
        pass


class _FakeConnect:
    """async CM returned by the fake client. The script is a list: None opens
    a session, an exception is raised at connect time, _STOP arms the exit
    and fails the connect; running past the end repeats the last step."""

    def __init__(self, h, attempt):
        self.h, self.attempt = h, attempt

    async def __aenter__(self):
        step = self.h.script[min(self.attempt - 1, len(self.h.script) - 1)]
        if step == _STOP:
            self.h.stop_now = True
            raise Exception("scripted stop")
        if step is not None:
            raise step
        self.h.session_count += 1
        return _FakeSession()

    async def __aexit__(self, *exc):
        return False


class _Harness(main.JarvisLive):
    """The real run() loop with every hardware task replaced by a sleeper.

    `_run_system_monitor` doubles as the failure injector: set `h.inject_next`
    to an exception and it fires from inside the session TaskGroup — exactly
    how the incident's 1011 arrived (a task noticed the dead socket)."""

    def __init__(self, script):
        self.ui = mock.MagicMock()
        with contextlib.redirect_stdout(io.StringIO()), \
             contextlib.redirect_stderr(io.StringIO()):
            super().__init__(self.ui)
        self.log = []
        self.ui.write_log = self.log.append
        self.script = script
        self.session_count = 0
        self.inject_next = None
        self.attempt = 0
        self.stop_now = False

        def _set_state(state):
            if self.stop_now and state == "SLEEPING":
                raise _HarnessDone()

        self.ui.set_state.side_effect = _set_state

    def fake_client(self, **kw):
        h = self

        class _Aio:
            class _Live:
                @staticmethod
                def connect(model=None, config=None):
                    h.attempt += 1
                    return _FakeConnect(h, h.attempt)
            live = _Live()
        client = mock.MagicMock()
        client.aio = _Aio
        return client

    # ── neutralized session tasks ───────────────────────────────────────
    async def _sleep(self):
        await asyncio.Event().wait()

    async def _send_realtime(self):          await self._sleep()
    async def _listen_audio(self):           await self._sleep()
    async def _receive_audio(self):          await self._sleep()
    async def _play_audio(self):             await self._sleep()
    async def _run_background_monitor(self): await self._sleep()
    async def _run_proactive_mode(self):     await self._sleep()
    async def _send_startup_briefing(self):  await self._sleep()
    async def _run_sleep_watch(self):        await self._sleep()
    async def _ensure_wake_detector(self):   pass

    async def _run_system_monitor(self):
        # Poll for the injected failure so it can be armed at any moment.
        while self.inject_next is None:
            await asyncio.sleep(0.002)
        err, self.inject_next = self.inject_next, None
        raise err


async def _e2e_wait_until(pred, timeout=10.0, what=""):
    end = time.monotonic() + timeout
    while not pred():
        if time.monotonic() > end:
            raise TimeoutError(f"timed out waiting for: {what}")
        await asyncio.sleep(0.002)


async def _e2e_stop(task):
    """Best-effort exit for a run() loop that swallows single cancellations:
    keep cancelling until one lands outside its try (the bottom sleep)."""
    for _ in range(200):
        if task.done():
            return
        task.cancel()
        with contextlib.suppress(BaseException):
            await asyncio.wait([task], timeout=0.05)
    if not task.done():
        raise AssertionError("run() task could not be stopped")


class TestRecoveryLoopEndToEnd(unittest.TestCase):
    """Replays the incident (and its neighbors) through the actual run()
    ladder, with a scripted fake Live server and neutralized hardware."""

    def _new_harness(self, script):
        h = _Harness(script)
        h._resume_handle = "handle-abc"          # an ongoing conversation
        h._resume_retries_left = main._RESUME_TRANSIENT_RETRIES
        return h

    def _drive(self, script, inject_first=None):
        """Run a scripted scenario start to finish, in its own loop."""
        async def go():
            h = self._new_harness(script)
            h.inject_next = inject_first
            out = io.StringIO()
            with mock.patch.object(main, "genai") as fake_genai, \
                 contextlib.redirect_stdout(out), \
                 contextlib.redirect_stderr(io.StringIO()):
                fake_genai.Client = h.fake_client
                task = asyncio.create_task(h.run())
                try:
                    await asyncio.wait_for(asyncio.shield(task), timeout=30)
                except _HarnessDone:
                    pass
                finally:
                    await _e2e_stop(task)
            return h, out.getvalue()
        return asyncio.run(go())

    def test_incident_1011_retries_with_handle_and_restores(self):
        """The 2026-10-01 incident: a Google-side 1011 mid-conversation must
        reconnect WITH the handle and restore the conversation, not start
        over. (Old behavior: cold start, context lost.)"""
        async def go():
            h = self._new_harness([None, None, _STOP])
            out = io.StringIO()
            with mock.patch.object(main, "genai") as fake_genai, \
                 contextlib.redirect_stdout(out), \
                 contextlib.redirect_stderr(io.StringIO()):
                fake_genai.Client = h.fake_client
                task = asyncio.create_task(h.run())
                try:
                    # session 1 opens, then the incident's 1011 fires from a
                    # task, exactly like the dead socket did
                    await _e2e_wait_until(lambda: h.session_count == 1,
                                          what="session 1 open")
                    h.inject_next = _err_1011()
                    # the ladder retries WITH the handle — immediate, like
                    # every ladder branch, so the budget is proven by the
                    # twice-failing scenario below instead
                    await _e2e_wait_until(lambda: h.session_count == 2,
                                          what="session 2 (resumed) open")
                    return h, out.getvalue()
                finally:
                    h.stop_now = True
                    h.inject_next = h.inject_next or Exception("end of test")
                    await _e2e_stop(task)
        h, out = asyncio.run(go())

        self.assertEqual(h._resume_handle, "handle-abc",
                         "the handle must be replayed, not dropped")
        self.assertIn("⚡ Transient server error — reconnecting with the "
                      "conversation intact", out)
        self.assertNotIn("starting fresh", "".join(h.log))
        self.assertIn("SYS: Reconnected — conversation restored.", h.log)
        self.assertEqual(h._resume_retries_left, 1,
                         "a handle that reached a live session refills the budget")

    def test_second_consecutive_1011_drops_the_handle(self):
        """'Only drop it if the resume fails a second time.'"""
        h, out = self._drive([None, _err_1011(), _STOP], inject_first=_err_1011())
        self.assertIsNone(h._resume_handle)
        self.assertIn("Resume retried, still failing", out)
        self.assertTrue(any("starting fresh" in l for l in h.log))

    def test_explicit_handle_rejection_drops_the_handle(self):
        err = _api_error(400, "INVALID_ARGUMENT: session resumption handle expired")
        h, out = self._drive([None, _STOP], inject_first=err)
        self.assertIsNone(h._resume_handle)
        self.assertIn("Resumption handle rejected", out)
        self.assertEqual(h._resume_retries_left, main._RESUME_TRANSIENT_RETRIES,
                         "a rejection never spends the transient-retry budget")

    def test_network_blip_keeps_the_handle(self):
        """A network error says nothing about the handle — the old code
        dropped it via the 'unhandled'→'handle' bug on every such failure."""
        h, out = self._drive([None, _STOP], inject_first=OSError("network went away"))
        self.assertEqual(h._resume_handle, "handle-abc")
        self.assertEqual(h._resume_retries_left, main._RESUME_TRANSIENT_RETRIES)
        self.assertFalse(any("starting fresh" in l for l in h.log))


if __name__ == "__main__":
    unittest.main(verbosity=2)
