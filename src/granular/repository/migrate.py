# SPDX-License-Identifier: MIT

from typing import Optional

from yaml import dump, load

try:
    from yaml import CDumper as Dumper
    from yaml import CLoader as Loader  # noqa: F401
except ImportError:
    from yaml import Dumper, Loader  # type: ignore[assignment]

from granular import configuration
from granular.model.migrate import Migrate


class MigrateRepository:
    def __init__(self) -> None:
        self._migrate_data: Optional[Migrate] = None
        self.is_dirty = False

    @property
    def migrate_data(self) -> Migrate:
        if self._migrate_data is None:
            self.__load_data()
        if self._migrate_data is None:
            raise ValueError()
        return self._migrate_data

    def __load_data(self) -> None:
        self._migrate_data = load(
            configuration.DATA_MIGRATE_PATH.read_text(), Loader=Loader
        )

    def __save_data(self, migrate_data: Migrate) -> None:
        configuration.DATA_MIGRATE_PATH.write_text(dump(migrate_data, Dumper=Dumper))

    def flush(self) -> None:
        if self._migrate_data is not None and self.is_dirty:
            self.__save_data(self._migrate_data)

    def get_latest_migration_number(self) -> int:
        return self.migrate_data["version"]

    def set_new_migration_number(self, migration_number: int) -> None:
        self.is_dirty = True

        if migration_number <= self.migrate_data["version"]:
            raise ValueError(
                f"{MigrateRepository.__name__}.{MigrateRepository.set_new_migration_number.__name__}: error, new migration number {migration_number} is not greater than existing migration number {self.migrate_data['version']}"
            )
        self.migrate_data["version"] = migration_number


MIGRATE_REPO = MigrateRepository()
