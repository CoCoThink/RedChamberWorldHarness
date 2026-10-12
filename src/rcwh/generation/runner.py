"""Small offline-first provider boundary; importing this module never loads an SDK."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
import os
from typing import Iterable, Protocol

DEFAULT_MODEL = "claude-fable-5-1"
# Actual installed version is captured only when the optional runner executes.


@dataclass(frozen=True)
class Budget:
    max_tokens: int = 8192
    timeout_seconds: float = 120
    max_retries: int = 0
    max_requests: int = 1
    # Output ceiling reserves SDK retries. No provider fallback is enabled.
    # Input tokens are separately billed, not covered by this output ceiling.
    max_output_tokens: int = 8192
    max_input_bytes: int = 1000000

    def validate(self, requests: int = 1, *, fallback: bool = False) -> None:
        if (type(self.max_tokens) is not int or not 1 <= self.max_tokens <= 128000
                or not 0 < self.timeout_seconds <= 600
                or type(self.max_retries) is not int or not 0 <= self.max_retries <= 2
                or type(self.max_requests) is not int or self.max_requests < 1
                or type(self.max_output_tokens) is not int or self.max_output_tokens < 1
                or type(self.max_input_bytes) is not int or self.max_input_bytes < 1):
            raise ValueError("invalid generation budget")
        reserved = requests * self.max_tokens * (self.max_retries + 1) * (2 if fallback else 1)
        if requests > self.max_requests or reserved > self.max_output_tokens:
            raise ValueError("request/retry/fallback output reservation exceeds budget")

    def to_dict(self) -> dict:
        return asdict(self)


class ModelRunner(Protocol):
    provider: str
    sdk_version: str

    def run(self, request: dict, budget: Budget) -> dict: ...


class ReplayRunner:
    """Raw provider fixtures, or recorded runs whose requests must match exactly."""
    provider = "replay"
    sdk_version = "offline"

    def __init__(self, responses: Iterable[dict]):
        self.responses = iter(responses)

    def run(self, request: dict, budget: Budget) -> dict:
        try:
            response = deepcopy(next(self.responses))
        except StopIteration as exc:
            raise ValueError("replay responses exhausted") from exc
        if response.get("kind") == "MODEL_RUN":
            from .records import verify_record
            verify_record(response)
            if response["request"] != request:
                raise ValueError("replay request identity mismatch")
            return {"response": response["response"], "request_id": response["request_id"]}
        return {"response": response, "request_id": response.get("request_id")}


class AnthropicRunner:
    provider = "anthropic"
    sdk_version = "not-loaded"

    def __init__(self, *, execute: bool = False, network_consent: bool = False):
        self.execute = execute
        self.network_consent = network_consent

    def run(self, request: dict, budget: Budget) -> dict:
        if not self.execute or not self.network_consent:
            raise ValueError("live generation requires --execute and --network-consent (materials and budget)")
        # Explicit env-key only; do not inspect, print or persist credentials.
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise ValueError("ANTHROPIC_API_KEY is required for live generation")
        if os.environ.get("ANTHROPIC_LOG"):
            raise ValueError("disable ANTHROPIC_LOG before sending private generation inputs")
        from importlib.metadata import version
        try:
            import anthropic
        except ImportError as exc:
            raise ValueError("optional generate extra is not installed") from exc
        self.sdk_version = version("anthropic")
        budget.validate(fallback=bool(request.get("fallbacks")))
        # Explicit endpoint prevents unnoticed ANTHROPIC_BASE_URL redirection.
        try:
            with anthropic.Anthropic(api_key=key, base_url="https://api.anthropic.com",
                                     timeout=budget.timeout_seconds, max_retries=budget.max_retries) as client:
                with client.messages.stream(**request) as stream:
                    response = stream.get_final_message()
                return {"response": response.to_dict(), "request_id": response._request_id}
        except anthropic.AuthenticationError:
            raise ValueError("provider authentication failed") from None
        except anthropic.PermissionDeniedError:
            raise ValueError("provider permission denied") from None
        except anthropic.RateLimitError:
            raise ValueError("provider rate limit; configured retries exhausted") from None
        except anthropic.APIStatusError as exc:
            raise ValueError(f"provider HTTP failure ({exc.status_code})") from None
        except anthropic.APIConnectionError:
            raise ValueError("provider connection/timeout failure; configured retries exhausted") from None
