"""DeepSeek rejects OpenAI-style JSON mode — the router must degrade, not die.

docs/known_issues.md §1: `enhance_insights` asked LiteLLM for
`response_format={"type":"json_object"}`; DeepSeek leads every tier group and
answers `"This response_format type is unavailable now"`, so the call raised,
fell through to a quota-exhausted OpenAI, and every insight-enhancement call in
the Phase A baseline recorded success=0.

The router picks its provider at call time, so JSON mode cannot be decided up
front. These pin the agreed behaviour: ask for it, and on a rejection retry once
without it — `_extract_json` already recovers JSON from free text.
"""
import pytest

from src.ai import llm_layer


DEEPSEEK_REJECTION = (
    "litellm.BadRequestError: DeepseekException - "
    '{"error":{"message":"This response_format type is unavailable now",'
    '"type":"invalid_request_error"}}'
)

JSON_MODE = {"type": "json_object"}


# ── the detector ────────────────────────────────────────────────────────

def test_deepseeks_real_rejection_is_recognised():
    assert llm_layer._rejects_json_mode(Exception(DEEPSEEK_REJECTION))


@pytest.mark.parametrize("message", [
    "RateLimitError: OpenAIException - You exceeded your current quota",
    "AuthenticationError: invalid api key",
    "Timeout: request timed out after 90s",
    "APIConnectionError: connection reset by peer",
])
def test_unrelated_failures_do_not_trigger_a_retry(message):
    """A quota or auth error must not burn a second call — it cannot succeed."""
    assert not llm_layer._rejects_json_mode(Exception(message))


def test_an_unrelated_error_merely_naming_response_format_is_ignored():
    """Naming the field is not enough; it must say the field is unsupported."""
    assert not llm_layer._rejects_json_mode(
        Exception("response_format was accepted but the upstream socket closed")
    )


# ── the retry path ──────────────────────────────────────────────────────

class _Resp:
    def __init__(self, content):
        self.choices = [type("C", (), {"message": type("M", (), {"content": content})()})()]
        self._hidden_params = {}


class _Router:
    """Records each attempt; rejects JSON mode exactly as DeepSeek does."""

    def __init__(self, *, reject_json_mode=True, content='{"insights": ["ok"]}'):
        self.reject_json_mode = reject_json_mode
        self.content = content
        self.attempts = []

    async def acompletion(self, **kwargs):
        self.attempts.append(kwargs)
        if self.reject_json_mode and "response_format" in kwargs:
            raise Exception(DEEPSEEK_REJECTION)
        return _Resp(self.content)


@pytest.fixture
def router(monkeypatch):
    """Installs a fake router AND severs the direct-API fallback.

    `_call_api` falls through to `litellm.acompletion` when the router yields
    nothing. Left alone that reaches the real OpenAI endpoint, which makes this
    suite slow, networked and billable — so stub it to fail closed.
    """
    import litellm

    async def _no_network(**kwargs):
        raise AssertionError(
            "direct-API fallback must not be reached in these tests "
            f"(model={kwargs.get('model')!r})"
        )

    monkeypatch.setattr(litellm, "acompletion", _no_network)

    def _install(**kw):
        r = _Router(**kw)
        monkeypatch.setattr(llm_layer, "_get_router", lambda: r)
        return r
    return _install


async def test_a_rejecting_provider_still_returns_a_result(router):
    r = router(reject_json_mode=True)
    result = await llm_layer._call_api(
        [{"role": "user", "content": "hi"}], response_format=JSON_MODE
    )
    assert result == {"insights": ["ok"]}, "the retry must salvage the call"
    assert len(r.attempts) == 2
    assert "response_format" in r.attempts[0], "JSON mode is tried first"
    assert "response_format" not in r.attempts[1], "the retry drops it"


async def test_a_provider_that_accepts_json_mode_is_called_once(router):
    """No wasted second call where JSON mode works — SambaNova, OpenAI."""
    r = router(reject_json_mode=False)
    result = await llm_layer._call_api(
        [{"role": "user", "content": "hi"}], response_format=JSON_MODE
    )
    assert result == {"insights": ["ok"]}
    assert len(r.attempts) == 1
    assert "response_format" in r.attempts[0]


async def test_no_response_format_requested_means_no_retry_loop(router):
    r = router(reject_json_mode=True)
    await llm_layer._call_api([{"role": "user", "content": "hi"}])
    assert len(r.attempts) == 1


async def test_a_non_json_body_is_not_retried(router):
    """Unparseable output is a parsing problem — dropping JSON mode worsens it."""
    r = router(reject_json_mode=False, content="I'm afraid I can't do that.")
    await llm_layer._call_api(
        [{"role": "user", "content": "hi"}], response_format=JSON_MODE
    )
    assert len(r.attempts) == 1, "must fall through, not retry"


async def test_json_is_recovered_from_prose_after_the_retry(router):
    """The retry relies on _extract_json, so a fenced body must still parse."""
    r = router(
        reject_json_mode=True,
        content='Sure!\n```json\n{"insights": ["from prose"]}\n```\n',
    )
    result = await llm_layer._call_api(
        [{"role": "user", "content": "hi"}], response_format=JSON_MODE
    )
    assert result == {"insights": ["from prose"]}
    assert len(r.attempts) == 2
