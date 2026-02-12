# SPDX-License-Identifier: MIT

import typer
from rich.console import Console

from granular.terminal.custom_typer import ContextAwareTyperGroup

app = typer.Typer(cls=ContextAwareTyperGroup, no_args_is_help=True)


def print_doc(text: str) -> None:
    """Print documentation in Unix man-page style without markdown rendering."""
    console = Console()
    in_code_block = False

    # Process the text line by line
    for line in text.strip().split("\n"):
        # Handle code blocks
        if line.startswith("```"):
            in_code_block = not in_code_block
            continue

        # If in code block, handle specially
        if in_code_block:
            # Skip comment lines in code blocks
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            # Print actual code
            console.print(f"      {line}", style="dim")
            continue

        # Remove inline markdown formatting
        line = line.replace("**", "")  # Remove bold markers
        line = line.replace("`", "")  # Remove code markers

        # Skip markdown headers and convert them to plain text
        if line.startswith("# "):
            # Main header
            header = line[2:].strip()
            console.print(f"\n{header.upper()}", style="bold")
        elif line.startswith("## "):
            # Section header
            section = line[3:].strip()
            console.print(f"\n{section}", style="bold")
        elif line.startswith("### "):
            # Subsection header
            subsection = line[4:].strip()
            console.print(f"\n  {subsection}", style="bold")
        elif line.startswith("- "):
            # List item
            item = line[2:].strip()
            console.print(f"  • {item}")
        elif line.strip().startswith("- "):
            # Indented list item
            item = line.strip()[2:].strip()
            console.print(f"    • {item}")
        elif line.strip() == "":
            # Empty line
            console.print()
        else:
            # Regular text
            if line.strip():
                # Regular text
                console.print(f"  {line.strip()}")
            else:
                console.print()


OVERVIEW_DOC = ""


DATE_TIME_DOC = ""


TASKS_DOC = ""


TIME_AUDITS_DOC = ""


EVENTS_DOC = ""


TIMESPANS_DOC = ""


NOTES_DOC = ""


CONTEXTS_DOC = ""


VIEWS_DOC = ""


CONFIGURATION_DOC = ""


TAGS_PROJECTS_DOC = ""


CUSTOM_REPORTS_DOC = ""


@app.command("overview, o")
def overview() -> None:
    """Show an overview of Granular and its core concepts."""
    print_doc(OVERVIEW_DOC)


@app.command("tasks, t")
def tasks() -> None:
    """Learn about tasks: creating, managing, and tracking them."""
    print_doc(TASKS_DOC)


@app.command("time-audits, ta")
def time_audits() -> None:
    """Learn about time audits: tracking actual time spent on work."""
    print_doc(TIME_AUDITS_DOC)


@app.command("events, e")
def events() -> None:
    """Learn about events: calendar items and iCal sync."""
    print_doc(EVENTS_DOC)


@app.command("timespans, ts")
def timespans() -> None:
    """Learn about timespans: organizing work in time periods."""
    print_doc(TIMESPANS_DOC)


@app.command("notes, n")
def notes() -> None:
    """Learn about notes: capturing text notes and linking them to entities."""
    print_doc(NOTES_DOC)


@app.command("contexts, cx")
def contexts() -> None:
    """Learn about contexts: switching work environments."""
    print_doc(CONTEXTS_DOC)


@app.command("views, v")
def views() -> None:
    """Learn about views: viewing and filtering your data."""
    print_doc(VIEWS_DOC)


@app.command("configuration, config, c")
def configuration() -> None:
    """Learn about configuration options and settings."""
    print_doc(CONFIGURATION_DOC)


@app.command("dates-times, dt")
def dates_times() -> None:
    """Learn about date and time formats accepted by Granular."""
    print_doc(DATE_TIME_DOC)


@app.command("tags-projects, tp")
def tags_projects() -> None:
    """Learn about organizing work with tags and projects."""
    print_doc(TAGS_PROJECTS_DOC)


@app.command("custom-views, cv")
def custom_views() -> None:
    """Learn about creating custom YAML views with filters and sorting."""
    print_doc(CUSTOM_REPORTS_DOC)
