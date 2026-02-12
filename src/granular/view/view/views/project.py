# SPDX-License-Identifier: MIT

from rich import box
from rich.console import Console
from rich.table import Table

from granular.view.view.views.header import header


def projects_view(active_context: str, projects: list[str]) -> None:
    header(active_context, "projects")

    projects_table = Table(box=box.SIMPLE)
    projects_table.add_column("project")

    for project in projects:
        projects_table.add_row(project)

    console = Console()
    console.print(projects_table)
