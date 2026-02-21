# SPDX-License-Identifier: MIT

from copy import deepcopy
from typing import Any, Optional, cast

from yaml import dump, load

try:
    from yaml import CDumper as Dumper
    from yaml import CLoader as Loader  # noqa: F401
except ImportError:
    from yaml import Dumper, Loader  # type: ignore[assignment]

from granular import configuration, time
from granular.model.context import Context
from granular.repository.configuration import CONFIGURATION_REPO
from granular.model.entity_id import EntityId, generate_entity_id


class ContextRepository:
    def __init__(self) -> None:
        self._contexts: Optional[list[Context]] = None
        self.is_dirty = False
        self._dirty_ids: set[str] = set()
        self._deleted_ids: set[str] = set()

    @property
    def contexts(self) -> list[Context]:
        if self._contexts is None:
            self.__load_data()
        if self._contexts is None:
            raise ValueError()
        return self._contexts

    def __load_data(self) -> None:
        self._contexts = []
        for file_path in configuration.DATA_CONTEXT_DIR.iterdir():
            if file_path.suffix != ".yaml" or file_path.name == ".gitkeep":
                continue
            raw_context = load(file_path.read_text(), Loader=Loader)
            if raw_context is not None:
                self._contexts.append(
                    self.__convert_context_for_deserialization(raw_context)
                )

    def __save_data(self) -> None:
        # Write dirty entities
        for context in self.contexts:
            if context["id"] in self._dirty_ids:
                serializable_context = self.__convert_context_for_serialization(
                    deepcopy(context)
                )
                file_path = configuration.DATA_CONTEXT_DIR / f"{context['id']}.yaml"
                file_path.write_text(dump(serializable_context, Dumper=Dumper))

        # Remove hard-deleted entity files
        for entity_id in self._deleted_ids:
            file_path = configuration.DATA_CONTEXT_DIR / f"{entity_id}.yaml"
            if file_path.exists():
                file_path.unlink()

        # Clear tracking sets
        self._dirty_ids.clear()
        self._deleted_ids.clear()

    def flush(self) -> None:
        if self._contexts is not None and self.is_dirty:
            self.__save_data()
            self.is_dirty = False

    def __convert_context_for_serialization(self, context: Context) -> dict[str, Any]:
        serializable_context = cast(dict[str, Any], context)
        serializable_context["created"] = time.datetime_to_iso_str(
            serializable_context["created"]
        )
        serializable_context["updated"] = time.datetime_to_iso_str(
            serializable_context["updated"]
        )
        return serializable_context

    def __convert_context_for_deserialization(self, context: dict[str, Any]) -> Context:
        deserializable_context = context
        deserializable_context["created"] = time.datetime_from_str(
            deserializable_context["created"]
        )
        deserializable_context["updated"] = time.datetime_from_str(
            deserializable_context["updated"]
        )
        return cast(Context, deserializable_context)

    def get_all_contexts(self) -> list[Context]:
        return deepcopy(self.contexts)

    def get_active_context(self) -> Context:
        return deepcopy([context for context in self.contexts if context["active"]][0])

    def save_new_context(self, context: Context) -> EntityId:
        self.is_dirty = True

        # Check for duplicate names
        for existing_context in self.contexts:
            if existing_context["name"] == context["name"]:
                raise ValueError(
                    f"A context with the name '{context['name']}' already exists"
                )

        context["id"] = generate_entity_id()
        self.contexts.append(context)
        self._dirty_ids.add(context["id"])
        return context["id"]

    def modify_context(
        self,
        id: EntityId,
        new_name: Optional[str],
        active: Optional[bool],
        auto_added_tags: Optional[list[str]],
        auto_added_projects: Optional[list[str]],
        filter: Optional[Any],
        default_note_folder: Optional[str],
        remove_auto_added_tags: bool,
        remove_auto_added_projects: bool,
        remove_filter: bool,
        remove_default_note_folder: bool,
    ) -> None:
        self.is_dirty = True
        self._dirty_ids.add(id)

        context = [context for context in self.contexts if context["id"] == id][0]
        # Set updated timestamp to current moment
        context["updated"] = time.now_utc()
        if new_name is not None:
            # Check for duplicate names (excluding the current context)
            for ctx in self.contexts:
                if ctx["name"] == new_name and ctx["id"] != id:
                    raise ValueError(
                        f"A context with the name '{new_name}' already exists"
                    )
            context["name"] = new_name
        if active is not None:
            context["active"] = active
        if auto_added_tags is not None:
            context["auto_added_tags"] = auto_added_tags
        if auto_added_projects is not None:
            context["auto_added_projects"] = auto_added_projects
        if filter is not None:
            context["filter"] = filter
        if default_note_folder is not None:
            config = CONFIGURATION_REPO.get_config()
            note_folders = config.get("note_folders", [])
            if note_folders is None:
                note_folders = []

            if note_folders and default_note_folder not in [
                f["name"] for f in note_folders
            ]:
                raise ValueError(
                    f"Note folder '{default_note_folder}' not found in config"
                )

            context["default_note_folder"] = default_note_folder

        if remove_auto_added_tags:
            context["auto_added_tags"] = None
        if remove_auto_added_projects:
            context["auto_added_projects"] = None
        if remove_filter:
            context["filter"] = None
        if remove_default_note_folder:
            context["default_note_folder"] = None

    def delete_context(self, id: EntityId) -> None:
        self.is_dirty = True
        self._deleted_ids.add(id)
        self._contexts = [context for context in self.contexts if context["id"] != id]

    def get_context(self, id: EntityId) -> Context:
        return deepcopy(
            [context for context in self.contexts if context["id"] == id][0]
        )

    def get_context_by_name(self, name: str) -> Context:
        return deepcopy(
            [context for context in self.contexts if context["name"] == name][0]
        )


CONTEXT_REPO = ContextRepository()
