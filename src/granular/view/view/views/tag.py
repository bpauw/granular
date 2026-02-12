# SPDX-License-Identifier: MIT

from rich import box
from rich.console import Console
from rich.table import Table

from granular.view.view.views.header import header


def tags_report(active_context: str, tags: list[str]) -> None:
    header(active_context, "tags")

    tags_table = Table(box=box.SIMPLE)
    tags_table.add_column("tag")

    for tag in tags:
        tags_table.add_row(tag)

    console = Console()
    console.print(tags_table)
