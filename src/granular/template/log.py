# SPDX-License-Identifier: MIT

from granular.model.log import Log
from granular.time import now_utc


def get_log_template() -> Log:
    now = now_utc()
    return {
        "id": None,
        "reference_id": None,
        "reference_type": None,
        "timestamp": None,
        "created": now,
        "updated": now,
        "deleted": None,
        "tags": None,
        "project": None,
        "text": None,
        "color": None,
    }
