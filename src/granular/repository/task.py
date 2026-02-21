# SPDX-License-Identifier: MIT

from copy import deepcopy
from typing import Any, Optional, cast

import pendulum
from yaml import dump, load

try:
    from yaml import CDumper as Dumper
    from yaml import CLoader as Loader  # noqa: F401
except ImportError:
    from yaml import Dumper, Loader  # type: ignore[assignment]

from granular import configuration, time
from granular.model.task import Task
from granular.repository.project import PROJECT_REPO
from granular.repository.tag import TAG_REPO
from granular.model.entity_id import EntityId, generate_entity_id


class TaskRepository:
    def __init__(self) -> None:
        self._tasks: Optional[list[Task]] = None
        self.is_dirty = False
        self._dirty_ids: set[str] = set()
        self._deleted_ids: set[str] = set()

    @property
    def tasks(self) -> list[Task]:
        if self._tasks is None:
            self.__load_data()
        if self._tasks is None:
            raise ValueError()
        return self._tasks

    def __load_data(self) -> None:
        self._tasks = []
        for file_path in configuration.DATA_TASKS_DIR.iterdir():
            if file_path.suffix != ".yaml" or file_path.name == ".gitkeep":
                continue
            raw_task = load(file_path.read_text(), Loader=Loader)
            if raw_task is not None:
                self._tasks.append(self.__convert_task_for_deserialization(raw_task))

    def __save_data(self) -> None:
        # Write dirty entities
        for task in self.tasks:
            if task["id"] in self._dirty_ids:
                serializable_task = self.__convert_task_for_serialization(
                    deepcopy(task)
                )
                file_path = configuration.DATA_TASKS_DIR / f"{task['id']}.yaml"
                file_path.write_text(dump(serializable_task, Dumper=Dumper))

        # Remove hard-deleted entity files
        for entity_id in self._deleted_ids:
            file_path = configuration.DATA_TASKS_DIR / f"{entity_id}.yaml"
            if file_path.exists():
                file_path.unlink()

        # Clear tracking sets
        self._dirty_ids.clear()
        self._deleted_ids.clear()

    def flush(self) -> bool:
        if self._tasks is not None and self.is_dirty:
            self.__save_data()
            self.is_dirty = False
            return True
        return False

    def __convert_task_for_serialization(self, task: Task) -> dict[str, Any]:
        serializable_task = cast(dict[str, Any], task)
        serializable_task["estimate"] = time.duration_to_str_optional(
            serializable_task["estimate"]
        )
        serializable_task["created"] = time.datetime_to_iso_str(
            serializable_task["created"]
        )
        serializable_task["updated"] = time.datetime_to_iso_str(
            serializable_task["updated"]
        )
        serializable_task["scheduled"] = time.datetime_to_iso_str_optional(
            serializable_task["scheduled"]
        )
        serializable_task["due"] = time.datetime_to_iso_str_optional(
            serializable_task["due"]
        )
        serializable_task["started"] = time.datetime_to_iso_str_optional(
            serializable_task["started"]
        )
        serializable_task["completed"] = time.datetime_to_iso_str_optional(
            serializable_task["completed"]
        )
        serializable_task["not_completed"] = time.datetime_to_iso_str_optional(
            serializable_task["not_completed"]
        )
        serializable_task["cancelled"] = time.datetime_to_iso_str_optional(
            serializable_task["cancelled"]
        )
        serializable_task["deleted"] = time.datetime_to_iso_str_optional(
            serializable_task["deleted"]
        )
        return serializable_task

    def __convert_task_for_deserialization(self, task: dict[str, Any]) -> Task:
        deserializable_task = task
        deserializable_task["estimate"] = time.duration_from_str_optional(
            deserializable_task["estimate"]
        )
        deserializable_task["created"] = time.datetime_from_str(
            deserializable_task["created"]
        )
        deserializable_task["updated"] = time.datetime_from_str(
            deserializable_task["updated"]
        )
        deserializable_task["scheduled"] = time.datetime_from_str_optional(
            deserializable_task["scheduled"]
        )
        deserializable_task["due"] = time.datetime_from_str_optional(
            deserializable_task["due"]
        )
        deserializable_task["started"] = time.datetime_from_str_optional(
            deserializable_task["started"]
        )
        deserializable_task["completed"] = time.datetime_from_str_optional(
            deserializable_task["completed"]
        )
        deserializable_task["not_completed"] = time.datetime_from_str_optional(
            deserializable_task["not_completed"]
        )
        deserializable_task["cancelled"] = time.datetime_from_str_optional(
            deserializable_task["cancelled"]
        )
        deserializable_task["deleted"] = time.datetime_from_str_optional(
            deserializable_task["deleted"]
        )
        return cast(Task, deserializable_task)

    def save_new_task(self, task: Task) -> EntityId:
        self.is_dirty = True

        task["id"] = generate_entity_id()

        # Deduplicate tags
        if task["tags"] is not None:
            task["tags"] = list(dict.fromkeys(task["tags"]))

        self.tasks.append(task)
        self._dirty_ids.add(task["id"])

        # Update tag and project caches
        if task["tags"] is not None:
            TAG_REPO.add_tags(task["tags"])
        if task["projects"] is not None:
            PROJECT_REPO.add_projects(task["projects"])

        return task["id"]

    def modify_task(
        self,
        id: EntityId,
        cloned_from_id: Optional[EntityId],
        timespan_id: Optional[EntityId],
        description: Optional[str],
        projects: Optional[list[str]],
        tags: Optional[list[str]],
        priority: Optional[int],
        color: Optional[str],
        estimate: Optional[pendulum.Duration],
        scheduled: Optional[pendulum.DateTime],
        due: Optional[pendulum.DateTime],
        started: Optional[pendulum.DateTime],
        completed: Optional[pendulum.DateTime],
        not_completed: Optional[pendulum.DateTime],
        cancelled: Optional[pendulum.DateTime],
        deleted: Optional[pendulum.DateTime],
        remove_cloned_from_id: bool,
        remove_timespan_id: bool,
        remove_description: bool,
        remove_projects: bool,
        remove_tags: bool,
        remove_priority: bool,
        remove_color: bool,
        remove_estimate: bool,
        remove_scheduled: bool,
        remove_due: bool,
        remove_started: bool,
        remove_completed: bool,
        remove_not_completed: bool,
        remove_cancelled: bool,
        remove_deleted: bool,
    ) -> None:
        self.is_dirty = True
        self._dirty_ids.add(id)

        task = [task for task in self.tasks if task["id"] == id][0]
        # Set updated timestamp to current moment
        task["updated"] = time.now_utc()
        if cloned_from_id is not None:
            task["cloned_from_id"] = cloned_from_id
        if timespan_id is not None:
            task["timespan_id"] = timespan_id
        if description is not None:
            task["description"] = description
        if projects is not None:
            deduplicated_projects = list(dict.fromkeys(projects))
            task["projects"] = deduplicated_projects
            PROJECT_REPO.add_projects(deduplicated_projects)
        if tags is not None:
            # Deduplicate tags
            deduplicated_tags = list(dict.fromkeys(tags))
            task["tags"] = deduplicated_tags
            TAG_REPO.add_tags(deduplicated_tags)
        if priority is not None:
            task["priority"] = priority
        if color is not None:
            task["color"] = color
        if estimate is not None:
            task["estimate"] = estimate
        if scheduled is not None:
            task["scheduled"] = scheduled
        if due is not None:
            task["due"] = due
        if started is not None:
            task["started"] = started
        if completed is not None:
            task["completed"] = completed
        if not_completed is not None:
            task["not_completed"] = not_completed
        if cancelled is not None:
            task["cancelled"] = cancelled
        if deleted is not None:
            task["deleted"] = deleted

        if remove_cloned_from_id:
            task["cloned_from_id"] = None
        if remove_timespan_id:
            task["timespan_id"] = None
        if remove_description:
            task["description"] = None
        if remove_projects:
            task["projects"] = None
        if remove_tags:
            task["tags"] = None
        if remove_priority:
            task["priority"] = None
        if remove_color:
            task["color"] = None
        if remove_estimate:
            task["estimate"] = None
        if remove_scheduled:
            task["scheduled"] = None
        if remove_due:
            task["due"] = None
        if remove_started:
            task["started"] = None
        if remove_completed:
            task["completed"] = None
        if remove_not_completed:
            task["not_completed"] = None
        if remove_cancelled:
            task["cancelled"] = None
        if remove_deleted:
            task["deleted"] = None

    def get_all_tasks(self) -> list[Task]:
        return deepcopy(self.tasks)

    def get_task(self, id: EntityId) -> Task:
        return deepcopy([task for task in self.tasks if task["id"] == id][0])


TASK_REPO = TaskRepository()
