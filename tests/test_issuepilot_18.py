"""Provider timeout validation stays consistent for finite positive values."""

import pytest

from kliz.providers import GoogleProvider, GoogleSearchConsoleProvider, IndexNowProvider
from kliz.providers.base import BaseProvider


def make_provider(name: str, timeout: float) -> BaseProvider:
    if name == "indexnow":
        return IndexNowProvider(api_key="abcdefgh", timeout=timeout)
    if name == "google":
        return GoogleProvider("account.json", timeout=timeout)
    return GoogleSearchConsoleProvider(
        "account.json", "https://example.com/", timeout=timeout
    )


@pytest.mark.parametrize("provider", ["indexnow", "google", "search-console"])
@pytest.mark.parametrize(
    "timeout", [float("nan"), float("inf"), -float("inf"), 0, -1, True, False]
)
def test_providers_reject_non_positive_non_finite_or_boolean_timeouts(
    provider: str, timeout: float
) -> None:
    with pytest.raises(ValueError, match="timeout"):
        make_provider(provider, timeout)


@pytest.mark.parametrize("provider", ["indexnow", "google", "search-console"])
@pytest.mark.parametrize("timeout", [0.1, 1, 10.0])
def test_providers_accept_finite_positive_timeouts(
    provider: str, timeout: float
) -> None:
    result = make_provider(provider, timeout)
    assert result.timeout == timeout
    result.close()
