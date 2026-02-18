# SPDX-License-Identifier: MIT

from granular.model.note import Note
from granular.time import now_utc


def get_note_template() -> Note:
    return {
        "id": None,
        "reference_id": None,
        "reference_type": None,
        "timestamp": None,
        "created": now_utc(),
        "updated": now_utc(),
        "deleted": None,
        "tags": None,
        "projects": None,
        "text": None,
        "color": None,
        "external_file_path": None,
        "note_folder_name": None,
        "sync_frontmatter": None,
    }
