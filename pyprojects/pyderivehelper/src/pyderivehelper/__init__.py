import logging

from pyderivehelper.wltools import (  # noqa: F401
    set_log_level,
    wc,
    wnlc,
    wplot,
)

logging.basicConfig(
    level=logging.WARNING, format='%(levelname)s:%(name)s:%(message)s'
)
