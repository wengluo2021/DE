import json
import subprocess

import httpx
import pytest

from app.config import load_settings
from app.qa.client import ChatCompletionsClient
from app.qa.errors import QAError


def settings(**generation):
    return load_settings(environ={}, api_key="fixture-key", overrides={"generation": generation})


def body(content='{"status":"insufficient","claims":[]}'):
    return {"model": "server-model", "id": "response-1", "choices": [
        {"message": {"content": content}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 2}}


def test_httpx_payload_and_response_are_explicit_and_secret_is_not_in_messages():
    captured = []
    def handle(request):
        captured.append(request)
        return httpx.Response(200, json=body())
    client = ChatCompletionsClient(settings(), http_transport=httpx.MockTransport(handle))
    response = client.generate([{"role": "user", "content": "question"}])
    request = captured[0]; payload = json.loads(request.content)
    assert request.headers["Authorization"] == "Bearer fixture-key"
    assert str(request.url) == "https://llm.cs.cityu.edu.hk/v1/chat/completions"
    assert payload["max_tokens"] == 1024 and "max_completion_tokens" not in payload
    assert payload["response_format"] == {"type": "json_object"}
    assert payload["stream"] is False and payload["temperature"] == 0
    assert "fixture-key" not in json.dumps(payload)
    assert response.model == "server-model" and response.usage["prompt_tokens"] == 1


@pytest.mark.parametrize("status,code,retry", [(401,"LLM_AUTH_ERROR",False),(403,"LLM_AUTH_ERROR",False),
    (429,"LLM_RATE_LIMIT",True),(503,"LLM_UNAVAILABLE",True),(400,"LLM_REQUEST_REJECTED",False),
    (302,"LLM_REQUEST_REJECTED",False)])
def test_http_status_is_not_a_refusal_or_unlimited_retry(status, code, retry):
    captured = []
    def handle(request):
        captured.append(request)
        return httpx.Response(status, headers={"Location":"https://other.example"}, text="fixture-key")
    client = ChatCompletionsClient(settings(), http_transport=httpx.MockTransport(handle))
    with pytest.raises(QAError) as error:
        client.generate([])
    assert error.value.code == code and error.value.retryable is retry
    assert len(captured) == 1 and "fixture-key" not in str(error.value)


def test_timeout_has_one_transport_attempt():
    def handle(request):
        raise httpx.ReadTimeout("contains fixture-key", request=request)
    client = ChatCompletionsClient(settings(), http_transport=httpx.MockTransport(handle))
    with pytest.raises(QAError) as error:
        client.generate([])
    assert error.value.status == 503 and error.value.retryable
    assert "fixture-key" not in str(error.value)


@pytest.mark.parametrize("invalid", [{}, {"choices":[]}, {"choices":[{"message":"wrong"}]}, body("")])
def test_bad_provider_shape_is_a_bounded_retryable_error(invalid):
    client = ChatCompletionsClient(settings(), http_transport=httpx.MockTransport(lambda req: httpx.Response(200,json=invalid)))
    with pytest.raises(QAError) as error:
        client.generate([])
    assert error.value.code == "LLM_INVALID_RESPONSE"


def test_missing_configuration_never_calls_transport():
    client = ChatCompletionsClient(load_settings(environ={}), http_transport=httpx.MockTransport(
        lambda req: pytest.fail("No request should be made")))
    with pytest.raises(QAError) as error:
        client.generate([])
    assert error.value.code == "LLM_NOT_CONFIGURED"


def test_secret_accidentally_in_prompt_is_not_transmitted():
    client = ChatCompletionsClient(settings(), http_transport=httpx.MockTransport(
        lambda req: pytest.fail("Credential must not be sent in messages")))
    with pytest.raises(QAError) as error:
        client.generate([{"role": "user", "content": "fixture-key"}])
    assert error.value.code == "CREDENTIAL_IN_PROMPT" and error.value.status == 422


def test_curl_configuration_is_stdin_only_and_default_curlrc_is_disabled():
    calls = []
    def runner(args, **kwargs):
        calls.append((args,kwargs))
        return subprocess.CompletedProcess(args,0,(json.dumps(body())+"\n200").encode(),b"")
    client = ChatCompletionsClient(settings(transport="curl"), curl_runner=runner)
    assert client.generate([{"role":"user","content":"hello"}]).model == "server-model"
    args, kwargs = calls[0]
    assert args[1] == "-q" and "fixture-key" not in " ".join(args)
    assert b"fixture-key" in kwargs["input"]
    assert "--insecure" not in args and "--location" not in args
    assert args[args.index("--max-redirs")+1] == "0"


@pytest.mark.parametrize("returncode,retry", [(28,True),(35,False),(60,False)])
def test_curl_failures_do_not_expose_stderr_or_change_transport(returncode,retry):
    calls=[]
    def runner(args,**kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args,returncode,b"",b"fixture-key")
    client=ChatCompletionsClient(settings(transport="curl"),curl_runner=runner)
    with pytest.raises(QAError) as error:
        client.generate([])
    assert len(calls)==1 and error.value.retryable is retry
    assert "fixture-key" not in str(error.value)


def test_provider_echoed_credential_is_redacted_before_recording():
    client=ChatCompletionsClient(settings(),http_transport=httpx.MockTransport(
        lambda req:httpx.Response(200,json=body("fixture-key"))))
    response=client.generate([])
    assert response.content == "[REDACTED]"
    assert "fixture-key" not in json.dumps(response.raw)
