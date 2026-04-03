import logging

from pyderivehelper.wltools import (  # noqa: F401
    set_log_level,
    wc,
    wnlc,
    wplot,
)

logging.basicConfig(
    level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s'
)
