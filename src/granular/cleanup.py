# SPDX-License-Identifier: MIT

import atexit

from granular.repository.configuration import CONFIGURATION_REPO
from granular.repository.context import CONTEXT_REPO
from granular.repository.dispatch import DISPATCH_REPO
from granular.repository.entry import ENTRY_REPO
from granular.repository.event import EVENT_REPO
from granular.repository.id_map import ID_MAP_REPO
from granular.repository.log import LOG_REPO
from granular.repository.migrate import MIGRATE_REPO
from granular.repository.note import NOTE_REPO
from granular.repository.project import PROJECT_REPO
from granular.repository.tag import TAG_REPO
from granular.repository.task import TASK_REPO
from granular.repository.time_audit import TIME_AUDIT_REPO
from granular.repository.timespan import TIMESPAN_REPO
from granular.repository.tracker import TRACKER_REPO


def flush_and_sync() -> None:
    CONFIGURATION_REPO.flush()
    ID_MAP_REPO.flush()
    MIGRATE_REPO.flush()
    CONTEXT_REPO.flush()
    DISPATCH_REPO.flush()

    # Flush entity repositories
    ENTRY_REPO.flush()
    EVENT_REPO.flush()
    LOG_REPO.flush()
    NOTE_REPO.flush()
    TASK_REPO.flush()
    TIME_AUDIT_REPO.flush()
    TIMESPAN_REPO.flush()
    TRACKER_REPO.flush()

    # Flush tag and project caches
    # Tags/projects are now added incrementally during CRUD operations
    # rather than being resynced from all entities
    TAG_REPO.flush()
    PROJECT_REPO.flush()


def register_cleanup() -> None:
    atexit.register(flush_and_sync)
