# SPDX-License-Identifier: MIT

from granular.migrate.registry import migration


@migration(1)
def migrate() -> None:
    """
    Placeholder so that there's a first version to kickoff the migrations system
    """
    print("running migration 1...")
    print("migration 1 complete!")
