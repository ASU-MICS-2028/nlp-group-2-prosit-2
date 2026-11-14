import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer

import pytest

from agent import llm


@pytest.fixture(autouse=True)
def settings(monkeypatch):
    """Use a fake provider and never really wait."""
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    monkeypatch.setenv("LLM_MODEL", "fake-model")
    monkeypatch.setattr(llm, "_sleep", lambda seconds: None)


def use_fake(monkeypatch, fake):
    monkeypatch.setitem(llm.PROVIDERS, "fake", fake)


def test_returns_the_reply_trimmed(monkeypatch):
    use_fake(monkeypatch, lambda prompt, system, model: "  hello  \n")

    assert llm.generate("hi") == "hello"


def test_passes_prompt_system_and_model_to_the_provider(monkeypatch):
    seen = {}

    def fake(prompt, system, model):
        seen.update(prompt=prompt, system=system, model=model)
        return "ok"

    use_fake(monkeypatch, fake)
    llm.generate("write a route", system="be brief")

    assert seen == {"prompt": "write a route", "system": "be brief", "model": "fake-model"}


def test_empty_prompt_is_refused(monkeypatch):
    use_fake(monkeypatch, lambda prompt, system, model: "ok")

    with pytest.raises(llm.LLMError, match="empty"):
        llm.generate("   ")


def test_huge_prompt_is_refused_without_calling_the_model(monkeypatch):
    calls = []
    use_fake(monkeypatch, lambda prompt, system, model: calls.append(1) or "ok")

    with pytest.raises(llm.LLMError, match="too long"):
        llm.generate("a" * (llm.MAX_PROMPT_CHARS + 1))
    assert calls == []


def test_empty_reply_is_an_error(monkeypatch):
    use_fake(monkeypatch, lambda prompt, system, model: "   ")

    with pytest.raises(llm.LLMError, match="empty reply"):
        llm.generate("hi")


def test_rate_limit_is_retried_then_succeeds(monkeypatch):
    attempts = []

    def flaky(prompt, system, model):
        attempts.append(1)
        if len(attempts) < 3:
            raise llm.RateLimited("busy")
        return "finally"

    use_fake(monkeypatch, flaky)

    assert llm.generate("hi") == "finally"
    assert len(attempts) == 3


def test_rate_limit_gives_up_after_max_tries(monkeypatch):
    attempts = []

    def always_busy(prompt, system, model):
        attempts.append(1)
        raise llm.RateLimited("busy")

    use_fake(monkeypatch, always_busy)

    with pytest.raises(llm.RateLimited):
        llm.generate("hi")
    assert len(attempts) == llm.MAX_TRIES


def test_waits_longer_each_time(monkeypatch):
    waits = []
    monkeypatch.setattr(llm, "_sleep", waits.append)

    def always_busy(prompt, system, model):
        raise llm.RateLimited("busy")

    use_fake(monkeypatch, always_busy)

    with pytest.raises(llm.RateLimited):
        llm.generate("hi")
    assert waits == [llm.WAIT_SECONDS * 1, llm.WAIT_SECONDS * 2]


def test_other_errors_are_not_retried(monkeypatch):
    attempts = []

    def broken(prompt, system, model):
        attempts.append(1)
        raise llm.LLMError("bad key")

    use_fake(monkeypatch, broken)

    with pytest.raises(llm.LLMError, match="bad key"):
        llm.generate("hi")
    assert len(attempts) == 1


def test_unknown_provider_lists_the_choices(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mystery")

    with pytest.raises(llm.LLMError, match="gemini"):
        llm.generate("hi")


def test_missing_model_name_is_explained(monkeypatch):
    use_fake(monkeypatch, lambda prompt, system, model: "ok")
    monkeypatch.delenv("LLM_MODEL")

    with pytest.raises(llm.LLMError, match="LLM_MODEL"):
        llm.generate("hi")


def test_gemini_without_a_key_says_what_to_do(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(llm.LLMError, match="GEMINI_API_KEY"):
        llm.generate("hi")


def test_claude_is_not_set_up_yet(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "claude")

    with pytest.raises(llm.LLMError, match="not set up"):
        llm.generate("hi")


# --- The Gemini function, tested with a fake client (we cannot call the real API in tests) ---


class FakeClient:
    """Looks like genai.Client, but returns or raises whatever the test says."""

    def __init__(self, outcome):
        self.models = self
        self._outcome = outcome

    def generate_content(self, model, contents, config):
        if isinstance(self._outcome, Exception):
            raise self._outcome
        return self._outcome


class FakeResponse:
    def __init__(self, text):
        self.text = text


def use_gemini(monkeypatch, outcome):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "not-a-real-key")
    monkeypatch.setattr(llm.genai, "Client", lambda api_key: FakeClient(outcome))


def test_gemini_reply_text_is_returned(monkeypatch):
    use_gemini(monkeypatch, FakeResponse("hello from gemini"))

    assert llm.generate("hi") == "hello from gemini"


def test_gemini_429_becomes_rate_limited_and_is_retried(monkeypatch):
    use_gemini(monkeypatch, llm.genai.errors.APIError(429, {"error": {"message": "quota"}}))

    with pytest.raises(llm.RateLimited):
        llm.generate("hi")


def test_gemini_other_api_error_shows_only_the_code(monkeypatch):
    use_gemini(
        monkeypatch,
        llm.genai.errors.APIError(500, {"error": {"message": "secret internal detail"}}),
    )

    with pytest.raises(llm.LLMError) as problem:
        llm.generate("hi")
    assert "500" in str(problem.value)
    assert "secret internal detail" not in str(problem.value)


def test_gemini_network_failure_is_explained(monkeypatch):
    use_gemini(monkeypatch, ConnectionError("no internet"))

    with pytest.raises(llm.LLMError, match="Could not reach"):
        llm.generate("hi")


def test_gemini_reply_without_text_is_an_error(monkeypatch):
    use_gemini(monkeypatch, FakeResponse(None))

    with pytest.raises(llm.LLMError, match="empty reply"):
        llm.generate("hi")


def test_gemini_503_busy_is_retried_like_429(monkeypatch):
    # The free tier often answers "503 overloaded" (W-9, Render). That is worth a retry too.
    use_gemini(monkeypatch, llm.genai.errors.APIError(503, {"error": {"message": "overloaded"}}))

    with pytest.raises(llm.RateLimited):
        llm.generate("hi")


# --- The builder's model (W-9 fix): each busy reply is retried inside the build ---


def test_builder_model_retries_busy_replies():
    model = llm.builder_model("gemini-3.5-flash")

    assert model.model == "gemini-3.5-flash"
    assert model.retry_options.attempts == 5
    for code in (429, 503):
        assert code in model.retry_options.http_status_codes
    assert 400 not in model.retry_options.http_status_codes  # a bad request never gets better by waiting


class BusyThenOkServer(BaseHTTPRequestHandler):
    """A pretend Gemini server: says "503 busy" twice, then answers. Counts the calls it got."""

    calls = 0

    def do_POST(self):
        type(self).calls += 1
        self.rfile.read(int(self.headers.get("Content-Length", 0)))  # read the request so the line is clean
        if type(self).calls <= 2:
            body, status = {"error": {"code": 503, "message": "overloaded", "status": "UNAVAILABLE"}}, 503
        else:
            reply = {"content": {"role": "model", "parts": [{"text": "hello"}]}, "finishReason": "STOP"}
            body, status = {"candidates": [reply]}, 200
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):  # keep the test output quiet
        pass


def test_builder_model_really_resends_after_503(monkeypatch):
    # The real google-genai client against a pretend server on this computer: no key, no internet.
    monkeypatch.setenv("GEMINI_API_KEY", "not-a-real-key")
    monkeypatch.setattr(llm, "BUILDER_RETRY", llm.BUILDER_RETRY.model_copy(update={"initial_delay": 0.01, "max_delay": 0.02}))
    BusyThenOkServer.calls = 0
    server = HTTPServer(("127.0.0.1", 0), BusyThenOkServer)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        model = llm.builder_model("gemini-3.5-flash")
        model.base_url = f"http://127.0.0.1:{server.server_port}"
        reply = model.api_client.models.generate_content(model="gemini-3.5-flash", contents="hi")
    finally:
        server.shutdown()

    assert reply.text == "hello"
    assert BusyThenOkServer.calls == 3  # busy, busy, then the answer: the build would have carried on


class HangsThenOkServer(BaseHTTPRequestHandler):
    """A pretend Gemini server whose first answer never comes in time (seen live), then answers."""

    calls = 0

    def do_POST(self):
        type(self).calls += 1
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        if type(self).calls == 1:
            time.sleep(2)  # far longer than the test's time limit below: the client gives up first
        reply = {"content": {"role": "model", "parts": [{"text": "hello"}]}, "finishReason": "STOP"}
        data = json.dumps({"candidates": [reply]}).encode()
        try:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except OSError:  # the client already hung up on the slow first call
            pass

    def log_message(self, *args):
        pass


def test_builder_model_cuts_a_hanging_call_and_sends_it_again(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "not-a-real-key")
    monkeypatch.setattr(llm, "CALL_TIMEOUT_SECONDS", 0.5)
    monkeypatch.setattr(llm, "BUILDER_RETRY", llm.BUILDER_RETRY.model_copy(update={"initial_delay": 0.01, "max_delay": 0.02}))
    HangsThenOkServer.calls = 0
    server = ThreadingHTTPServer(("127.0.0.1", 0), HangsThenOkServer)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        model = llm.builder_model("gemini-3.5-flash")
        model.base_url = f"http://127.0.0.1:{server.server_port}"
        started = time.monotonic()
        reply = model.api_client.models.generate_content(model="gemini-3.5-flash", contents="hi")
        seconds = time.monotonic() - started
    finally:
        server.shutdown()

    assert reply.text == "hello"
    assert HangsThenOkServer.calls == 2  # the hanging call, then the one sent again
    assert seconds < 1.9  # we did not wait for the hanging call to finish
