import os
from collections.abc import Iterator
from unittest.mock import patch

import pytest

os.environ.setdefault('OPENAI_PERSONAL_MATH_ASSISTANT', 'test-key')

from pyderivehelper import wltools


@pytest.fixture(autouse=True)
def patch_kernel_start() -> Iterator[None]:
    with patch.object(wltools.ws, 'start'):
        yield
