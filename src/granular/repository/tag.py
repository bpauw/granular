# SPDX-License-Identifier: MIT

from typing import Optional

from yaml import dump, load

try:
    from yaml import CDumper as Dumper
    from yaml import CLoader as Loader  # noqa: F401
except ImportError:
    from yaml import Dumper, Loader  # type: ignore[assignment]

from granular import configuration
from granular.model.tag import Tags


class TagRepository:
    def __init__(self) -> None:
        self._tags: Optional[set[str]] = None
        self.is_dirty = False

    @property
    def tags(self) -> set[str]:
        if self._tags is None:
            self.__load_data()
        if self._tags is None:
            raise ValueError()
        return self._tags

    def __load_data(self) -> None:
        tags_data = load(configuration.DATA_TAGS_PATH.read_text(), Loader=Loader)
        self._tags = set(tags_data["tags"])

    def __save_data(self, tags: set[str]) -> None:
        tags_data: Tags = {"tags": sorted(tags)}
        configuration.DATA_TAGS_PATH.write_text(dump(tags_data, Dumper=Dumper))

    def flush(self) -> None:
        if self._tags is not None and self.is_dirty:
            self.__save_data(self._tags)

    def add_tag(self, tag: str) -> None:
        if tag not in self.tags:
            self.is_dirty = True
            self.tags.add(tag)

    def add_tags(self, tags: list[str]) -> None:
        """Add multiple tags at once. Efficient for CRUD operations."""
        for tag in tags:
            if tag not in self.tags:
                self.is_dirty = True
                self.tags.add(tag)

    def remove_tag(self, tag: str) -> None:
        if tag in self.tags:
            self.is_dirty = True
            self.tags.discard(tag)

    def get_all_tags(self) -> list[str]:
        return sorted(self.tags)

    def tag_exists(self, tag: str) -> bool:
        return tag in self.tags

    def set_all_tags(self, tags: list[str]) -> None:
        self.is_dirty = True
        self._tags = set(tags)


TAG_REPO = TagRepository()
