"""LLM 契约的单测：JSON 模式、校验失败重试 ≤2、用尽降级（ARCHITECTURE §5）。"""

import httpx
import pytest

from src.intelligence.llm import LLMClient, LLMError, LLMOutputError


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr("src.intelligence.llm.time.sleep", lambda *_: None)


def _client(handler):
    return LLMClient(
        api_key="sk-test",
        base_url="https://example.invalid",
        model="m",
        http=httpx.Client(transport=httpx.MockTransport(handler)),
    )


def _reply(content):
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


def test_happy_path_passes_payload_to_parse():
    client = _client(lambda request: _reply('{"ok": true}'))
    assert client.chat_json("s", "u", lambda payload: payload["ok"]) is True


def test_invalid_json_is_retried_then_succeeds():
    calls = []

    def handler(request):
        calls.append(request)
        return _reply("not json") if len(calls) == 1 else _reply('{"ok": 1}')

    assert _client(handler).chat_json("s", "u", lambda payload: payload["ok"]) == 1
    assert len(calls) == 2


def test_validation_failure_feeds_reason_back_to_model():
    seen = []

    def handler(request):
        seen.append(request)
        if len(seen) == 2:
            import json

            body = json.loads(request.content)
            assert "quote 不是原文" in body["messages"][-1]["content"]
        return _reply('{"bad": 1}') if len(seen) == 1 else _reply('{"ok": 2}')

    def parse(payload):
        if "bad" in payload:
            raise LLMOutputError("quote 不是原文")
        return payload["ok"]

    assert _client(handler).chat_json("s", "u", parse) == 2


def test_retries_are_capped_then_degrade_without_guessing():
    calls = []

    def handler(request):
        calls.append(request)
        return _reply("still not json")

    with pytest.raises(LLMError) as exc:
        _client(handler).chat_json("s", "u", lambda payload: payload)
    assert len(calls) == 3                     # 初次 + 2 次重试
    assert "3 次" in str(exc.value)


def test_http_error_raises_llm_error():
    client = _client(lambda request: httpx.Response(500, text="boom"))
    with pytest.raises(LLMError) as exc:
        client.chat_json("s", "u", lambda payload: payload)
    assert "500" in str(exc.value)


def test_transport_error_raises_llm_error():
    def handler(request):
        raise httpx.ConnectError("no network")

    with pytest.raises(LLMError):
        _client(handler).chat_json("s", "u", lambda payload: payload)


def test_repr_never_leaks_api_key():
    client = LLMClient(api_key="sk-supersecret", base_url="https://x", model="m")
    assert "supersecret" not in repr(client)


def test_request_uses_json_object_mode():
    import json

    seen = {}

    def handler(request):
        seen.update(json.loads(request.content))
        return _reply('{"ok": 1}')

    _client(handler).chat_json("s", "u", lambda payload: payload)
    assert seen["response_format"] == {"type": "json_object"}


# ---------- 真机诊断（2026-09-17）：失败原因必须留在 stderr ----------


def test_failure_log_carries_attempt_reason_and_raw_output(capsys):
    """群里只回一句人话，但 stderr 要能看到：第几次 / 为什么 / 模型原样返回。"""

    def handler(request):
        return _reply("still not json")

    with pytest.raises(LLMError):
        _client(handler).chat_json("s", "u", lambda payload: payload)

    err = capsys.readouterr().err
    assert "第 3/3 次未通过" in err        # 重试次数
    assert "不是合法 JSON" in err          # 校验失败原因
    assert "still not json" in err        # 模型返回原文


def test_schema_reason_is_logged_on_every_attempt(capsys):
    def parse(payload):
        raise LLMOutputError("rubric[0](R1) 的 quote 不是作业书原文")

    with pytest.raises(LLMError):
        _client(lambda request: _reply('{"ok": 1}')).chat_json("s", "u", parse)

    err = capsys.readouterr().err
    assert "第 1/3 次未通过" in err
    assert "quote 不是作业书原文" in err
