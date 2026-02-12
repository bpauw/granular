# SPDX-License-Identifier: MIT

from typing import Optional

from yaml import dump, load

try:
    from yaml import CDumper as Dumper
    from yaml import CLoader as Loader  # noqa: F401
except ImportError:
    from yaml import Dumper, Loader  # type: ignore[assignment]

from granular import configuration
from granular.model.project import Projects


class ProjectRepository:
    def __init__(self) -> None:
        self._projects: Optional[set[str]] = None
        self.is_dirty = False

    @property
    def projects(self) -> set[str]:
        if self._projects is None:
            self.__load_data()
        if self._projects is None:
            raise ValueError()
        return self._projects

    def __load_data(self) -> None:
        projects_data = load(
            configuration.DATA_PROJECTS_PATH.read_text(), Loader=Loader
        )
        self._projects = set(projects_data["projects"])

    def __save_data(self, projects: set[str]) -> None:
        projects_data: Projects = {"projects": sorted(projects)}
        configuration.DATA_PROJECTS_PATH.write_text(dump(projects_data, Dumper=Dumper))

    def flush(self) -> None:
        if self._projects is not None and self.is_dirty:
            self.__save_data(self._projects)

    def add_project(self, project: str) -> None:
        if project not in self.projects:
            self.is_dirty = True
            self.projects.add(project)

    def remove_project(self, project: str) -> None:
        if project in self.projects:
            self.is_dirty = True
            self.projects.discard(project)

    def get_all_projects(self) -> list[str]:
        return sorted(self.projects)

    def project_exists(self, project: str) -> bool:
        return project in self.projects

    def set_all_projects(self, projects: list[str]) -> None:
        self.is_dirty = True
        self._projects = set(projects)


PROJECT_REPO = ProjectRepository()
