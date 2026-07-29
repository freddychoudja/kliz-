"""IndexNow provider implementation."""

import re
from collections.abc import Sequence
from pathlib import PurePosixPath
from typing import Optional, Union
from urllib.parse import SplitResult

import requests

from kliz._validation import parse_http_url
from kliz.exceptions import ProviderError
from kliz.providers.base import BaseProvider

PayloadValue = Union[str, list[str]]


