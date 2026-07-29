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


