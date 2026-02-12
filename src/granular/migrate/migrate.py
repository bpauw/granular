# SPDX-License-Identifier: MIT

from granular.migrate import registry
from granular.repository.configuration import CONFIGURATION_REPO
from granular.repository.migrate import MIGRATE_REPO
from granular.version.version import Version


def run_required_migrations() -> None:
    config = CONFIGURATION_REPO.get_config()
    version = Version()

    registry.register_migrations()
    migrations = registry.get_migrations()
    latest_migration_id = MIGRATE_REPO.get_latest_migration_number()

    migrations_to_run = sorted(
        [
            (key, value)
            for key, value in migrations.items()
            if key > latest_migration_id
        ],
        key=lambda kvp: kvp[0],
    )

    for migration_tuple in migrations_to_run:
        migration_id = migration_tuple[0]
        migration_callable = migration_tuple[1]

        MIGRATE_REPO.set_new_migration_number(migration_id)
        migration_callable()

        if config["use_git_versioning"]:
            version.create_data_checkpoint(
                f"completed running migration: {migration_id}"
            )
