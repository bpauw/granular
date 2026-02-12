# SPDX-License-Identifier: MIT

from rich import box
from rich.console import Console
from rich.table import Table

from granular.service.search import SearchResult
from granular.view.view.util import format_tags
from granular.view.view.views.header import header


def search_results_view(
    active_context: str,
    report_name: str,
    results: list[SearchResult],
    no_wrap: bool = False,
) -> None:
    """
    Display search results in a table format.

    Args:
        active_context: The name of the active context
        report_name: The name of the report
        results: List of SearchResult objects to display
        no_wrap: Whether to disable text wrapping in columns
    """
    header(active_context, report_name)

    if not results:
        console = Console()
        console.print("No results found.")
        return

    search_table = Table(box=box.SIMPLE)

    # Add columns
    search_table.add_column("id")
    search_table.add_column("entity type")
    search_table.add_column("project")
    if no_wrap:
        search_table.add_column("description", no_wrap=True, overflow="ellipsis")
    else:
        search_table.add_column("description")
    search_table.add_column("tags")

    # Add rows
    for result in results:
        search_table.add_row(
            str(result["id"]) if result["id"] is not None else "",
            result["entity_type"],
            result["project"] or "",
            result["description"] or "",
            format_tags(result["tags"]),
        )

    console = Console()
    console.print(search_table)
