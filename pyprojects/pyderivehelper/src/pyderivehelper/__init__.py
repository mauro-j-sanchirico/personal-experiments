"""Expose notebook calculations, plotting, logging, and the shared session.

The package exports wc, wnlc, wplot, set_log_level, and the Wolfram session ws.
Importing loads project configuration and .env values, creates the Wolfram
session and OpenAI client, and requires the configured API key environment
variable. It also configures warning-level root logging if no handlers exist.
"""

import logging

from pyderivehelper.wltools import (  # noqa: F401
    set_log_level,
    wc,
    wnlc,
    wplot,
    ws,
)

logging.basicConfig(
    level=logging.WARNING, format='%(levelname)s:%(name)s:%(message)s'
)
