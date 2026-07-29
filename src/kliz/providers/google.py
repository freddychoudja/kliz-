"""Google Indexing API provider implementation."""

from pathlib import Path
from typing import Any, Union

import google_auth_httplib2
import httplib2
from google.auth.exceptions import TransportError
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from kliz._validation import parse_http_url
from kliz.exceptions import ProviderError
from kliz.providers.base import BaseProvider


class GoogleProvider(BaseProvider):
    """Notify Google for eligible JobPosting or BroadcastEvent pages only."""

    scope = "https://www.googleapis.com/auth/indexing"

    def __init__(
        self,
        service_account_file: Union[str, Path],
        *,
        timeout: float = 60.0,
        num_retries: int = 2,
    ) -> None:
        if not str(service_account_file):
            raise ValueError("service_account_file must not be empty")
        if timeout <= 0:
            raise ValueError("timeout must be greater than zero")
        if num_retries < 0:
