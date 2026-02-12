# SPDX-License-Identifier: MIT

from granular.model.id_map import IdMap


def get_id_map_template() -> IdMap:
    return {
        "tasks": {"synthetic_to_real": {}, "real_to_synthetic": {}},
        "time_audits": {"synthetic_to_real": {}, "real_to_synthetic": {}},
        "events": {"synthetic_to_real": {}, "real_to_synthetic": {}},
        "timespans": {"synthetic_to_real": {}, "real_to_synthetic": {}},
        "notes": {"synthetic_to_real": {}, "real_to_synthetic": {}},
        "logs": {"synthetic_to_real": {}, "real_to_synthetic": {}},
        "trackers": {"synthetic_to_real": {}, "real_to_synthetic": {}},
        "entries": {"synthetic_to_real": {}, "real_to_synthetic": {}},
    }
