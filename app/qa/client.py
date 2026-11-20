"""One-attempt configurable Chat Completions client. The service owns retries."""
from dataclasses import dataclass
import json
import subprocess
import sys
from typing import Any

import httpx

from app.config import Settings
from .errors import QAError


@dataclass(frozen=True)
class GenerationResponse:
    content: str
    model: str
    finish_reason: str | None
    usage: dict | None
    response_id: str | None
    raw: dict


def redact(value: Any, secret: str):
    """Provider responses/errors may echo headers; sanitize before recording."""
    if isinstance(value, str):
        return value.replace(secret, "[REDACTED]") if secret else value
    if isinstance(value, dict):
        return {redact(k, secret): redact(v, secret) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v, secret) for v in value]
    return value


def _quote(value):
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\r", "\\r").replace("\n", "\\n")


class ChatCompletionsClient:
    """Explicit httpx/curl transports, no redirects or automatic fallback.

    mock HTTPX transports/curl runners are injected only by tests. Configuration
    and credentials never enter the model messages or exception messages.
    """
    def __init__(self, settings: Settings, *, http_transport=None, curl_runner=None):
        self.settings = settings
        self.http_transport = http_transport
        self.curl_runner = curl_runner or subprocess.run

    def generate(self, messages):
        if not self.settings.llm_configured:
            raise QAError("LLM_NOT_CONFIGURED", "Generation service is not configured", 503)
        cfg = self.settings.experiment.generation
        secret = self.settings.api_key()
        if secret in json.dumps(messages, ensure_ascii=False):
            raise QAError("CREDENTIAL_IN_PROMPT", "Credentials must not be included in model messages", 422)
        payload = {"model": cfg.model, "messages": messages, "temperature": cfg.temperature,
                   "max_tokens": cfg.max_tokens, "stream": False}
        if cfg.json_mode:
            payload["response_format"] = {"type": "json_object"}
        if cfg.seed is not None:
            payload["seed"] = cfg.seed
        url = cfg.base_url.rstrip("/") + "/chat/completions"
        if cfg.transport == "curl":
            status, raw = self._curl(url, payload, secret, cfg.timeout_seconds)
        else:
            status, raw = self._httpx(url, payload, secret, cfg.timeout_seconds)
        if status != 200:
            if status in (401, 403):
                raise QAError("LLM_AUTH_ERROR", "Generation service rejected authentication or model access", 503)
            if status == 429:
                raise QAError("LLM_RATE_LIMIT", "Generation service rate or quota limit reached", 503, retryable=True)
            if status == 408 or status >= 500:
                raise QAError("LLM_UNAVAILABLE", "Generation service is temporarily unavailable", 503, retryable=True)
            raise QAError("LLM_REQUEST_REJECTED", "Generation service rejected the configured request", 502)
        try:
            data = redact(json.loads(raw), secret)
            choice = data["choices"][0]
            content = choice["message"].get("content")
            model = data.get("model", cfg.model)
            finish = choice.get("finish_reason")
            usage = data.get("usage")
            response_id = data.get("id")
            if (not isinstance(content, str) or not content.strip() or not isinstance(model, str)
                    or not model.strip() or (usage is not None and not isinstance(usage, dict))
                    or (finish is not None and not isinstance(finish, str))
                    or (response_id is not None and not isinstance(response_id, str))):
                raise ValueError("invalid response fields")
        except (ValueError, KeyError, IndexError, TypeError, AttributeError):
            raise QAError("LLM_INVALID_RESPONSE", "Generation service returned an invalid or empty response", 502, retryable=True) from None
        return GenerationResponse(content, model, finish, usage, response_id, data)

    def _httpx(self, url, payload, secret, timeout):
        try:
            with httpx.Client(timeout=timeout, follow_redirects=False,
                              transport=self.http_transport) as client:
                response = client.post(url, headers={"Authorization": "Bearer " + secret}, json=payload)
            return response.status_code, response.text
        except httpx.TimeoutException:
            raise QAError("LLM_TIMEOUT", "Generation request timed out", 503, retryable=True) from None
        except httpx.HTTPError:
            raise QAError("LLM_CONNECTION_ERROR", "Could not connect to generation service", 503, retryable=True) from None

    def _curl(self, url, payload, secret, timeout):
        config = ('url = "' + _quote(url) + '"\n'
                  'header = "Authorization: Bearer ' + _quote(secret) + '"\n'
                  'header = "Content-Type: application/json"\n'
                  'data-binary = "' + _quote(json.dumps(payload, ensure_ascii=False)) + '"\n')
        executable = "curl.exe" if sys.platform == "win32" else "curl"
        args = [executable, "-q", "--config", "-", "--silent", "--show-error",
                "--connect-timeout", "10", "--max-time", str(timeout), "--max-redirs", "0",
                "--proto", "=https,http" if url.startswith("http://") else "=https",
                "--write-out", "\n%{http_code}"]
        try:
            response = self.curl_runner(args, input=config.encode("utf-8"), capture_output=True,
                                        timeout=timeout + 5)
        except subprocess.TimeoutExpired:
            raise QAError("LLM_TIMEOUT", "Generation request timed out", 503, retryable=True) from None
        except OSError:
            raise QAError("LLM_TRANSPORT_UNAVAILABLE", "Configured curl transport is unavailable", 503) from None
        if response.returncode:
            transient = response.returncode in {5, 6, 7, 18, 28, 52, 55, 56}
            code = "LLM_TIMEOUT" if response.returncode == 28 else "LLM_CONNECTION_ERROR"
            raise QAError(code, "Generation transport could not complete the request", 503, retryable=transient)
        try:
            raw, code = response.stdout.decode("utf-8").rsplit("\n", 1)
            status = int(code)
            if not 100 <= status <= 599:
                raise ValueError("invalid status")
            return status, raw
        except (ValueError, UnicodeError):
            raise QAError("LLM_INVALID_RESPONSE", "Generation transport returned an invalid response", 502, retryable=True) from None
