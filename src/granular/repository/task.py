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


class TaskRepository:
    def __init__(self) -> None:
        self._tasks: Optional[list[Task]] = None
        self._next_id: Optional[int] = None
        self.is_dirty = False

    @property
    def tasks(self) -> list[Task]:
        if self._tasks is None:
            self.__load_data()
        if self._tasks is None:
            raise ValueError()
        return self._tasks

    @property
    def next_id(self) -> int:
        if self._next_id is None:
            self.__load_data()
        if self._next_id is None:
            raise ValueError()
        return self._next_id

    @next_id.setter
    def next_id(self, value: int) -> None:
        self._next_id = value

    def __load_data(self) -> None:
        tasks_data = load(configuration.DATA_TASKS_PATH.read_text(), Loader=Loader)
        self._next_id = int(tasks_data["next_id"])
        raw_tasks = tasks_data["tasks"]
        self._tasks = [
            self.__convert_task_for_deserialization(task) for task in raw_tasks
        ]

    def __save_data(self, tasks: list[Task], next_id: int) -> None:
        serializable_tasks = [
            self.__convert_task_for_serialization(task) for task in deepcopy(tasks)
        ]
        tasks_data = {"next_id": next_id, "tasks": serializable_tasks}
        configuration.DATA_TASKS_PATH.write_text(dump(tasks_data, Dumper=Dumper))

    def flush(self) -> bool:
        if self._tasks is not None and self._next_id is not None and self.is_dirty:
            self.__save_data(self._tasks, self._next_id)
            return True
        return False

    def __get_next_id(self) -> int:
        return_id = self.next_id
        self.next_id += 1
        return return_id

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

    def save_new_task(self, task: Task) -> int:
        self.is_dirty = True

        task["id"] = self.__get_next_id()

        # Deduplicate tags
        if task["tags"] is not None:
            task["tags"] = list(dict.fromkeys(task["tags"]))

        self.tasks.append(task)

        # Update tag and project caches
        if task["tags"] is not None:
            TAG_REPO.add_tags(task["tags"])
        if task["project"] is not None:
            PROJECT_REPO.add_project(task["project"])

        return task["id"]

    def modify_task(
        self,
        id: int,
        cloned_from_id: Optional[int],
        timespan_id: Optional[int],
        description: Optional[str],
        project: Optional[str],
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
        remove_project: bool,
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

        task = [task for task in self.tasks if task["id"] == id][0]
        # Set updated timestamp to current moment
        task["updated"] = time.now_utc()
        if cloned_from_id is not None:
            task["cloned_from_id"] = cloned_from_id
        if timespan_id is not None:
            task["timespan_id"] = timespan_id
        if description is not None:
            task["description"] = description
        if project is not None:
            task["project"] = project
            PROJECT_REPO.add_project(project)
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
        if remove_project:
            task["project"] = None
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

    def get_task(self, id: int) -> Task:
        return deepcopy([task for task in self.tasks if task["id"] == id][0])


TASK_REPO = TaskRepository()
