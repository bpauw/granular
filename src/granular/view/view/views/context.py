# SPDX-License-Identifier: MIT

from rich import box
from rich.console import Console
from rich.table import Table

from granular.model.context import Context
from granular.time import datetime_to_display_local_datetime_str_optional
from granular.view.view.util import format_tags
from granular.view.view.views.header import header


def contexts_view(active_context: str, contexts: list[Context]) -> None:
    header(active_context, "contexts")

    contexts_table = Table(box=box.SIMPLE)
    contexts_table.add_column("id")
    contexts_table.add_column("active")
    contexts_table.add_column("name")
    contexts_table.add_column("auto_added_tags")
    contexts_table.add_column("auto_added_projects")
    contexts_table.add_column("has_filter")

    for context in contexts:
        id = str(context["id"]) if context["id"] is not None else ""
        active = "✓" if context["active"] else " "
        name = context["name"]
        auto_added_tags = format_tags(context["auto_added_tags"])
        auto_added_projects = format_tags(context["auto_added_projects"])
        has_filter = "✓" if context["filter"] is not None else " "

        contexts_table.add_row(
            id, active, name, auto_added_tags, auto_added_projects, has_filter
        )

    console = Console()
    console.print(contexts_table)


def single_context_view(active_context: str, context: Context) -> None:
    header(active_context, "context")

    context_table = Table(box=box.SIMPLE)
    context_table.add_column("property")
    context_table.add_column("value")

    context_table.add_row("id", str(context["id"]) if context["id"] is not None else "")
    context_table.add_row("name", context["name"])
    context_table.add_row("active", "✓" if context["active"] else "✗")
    context_table.add_row("auto_added_tags", format_tags(context["auto_added_tags"]))
    context_table.add_row(
        "auto_added_projects",
        format_tags(context["auto_added_projects"]),
    )
    context_table.add_row("filter", str(context["filter"]) if context["filter"] else "")
    context_table.add_row(
        "created",
        datetime_to_display_local_datetime_str_optional(context["created"]) or "",
    )
    context_table.add_row(
        "updated",
        datetime_to_display_local_datetime_str_optional(context["updated"]) or "",
    )

    console = Console()
    console.print(context_table)
