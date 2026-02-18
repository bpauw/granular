# SPDX-License-Identifier: MIT

from granular.model.context import Context
from granular.time import now_utc


def get_context_template() -> Context:
    now = now_utc()
    return {
        "id": None,
        "name": None,
        "active": False,
        "auto_added_tags": None,
        "auto_added_projects": None,
        "filter": None,
        "default_note_folder": None,
        "created": now,
        "updated": now,
    }
