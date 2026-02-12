# SPDX-License-Identifier: MIT

from typing import Annotated

import typer

from granular import state as app_state
from granular.terminal import (
    configuration,
    context,
    event,
    log,
    note,
    task,
    time_audit,
    timespan,
    tracker,
    view,
)
from granular.terminal.custom_typer import ContextAwareTyperGroup
from granular.terminal.search import search
from granular.terminal.version import version
from granular.view import state as view_state

app = typer.Typer(
    cls=ContextAwareTyperGroup,
    help="Granular - Organizational management in the CLI",
    no_args_is_help=True,
)
app.add_typer(configuration.app, name="config, c")
app.add_typer(context.app, name="context, cx")
app.add_typer(task.app, name="task, t")
app.add_typer(time_audit.app, name="audit, a")
app.add_typer(event.app, name="event, e")
app.add_typer(timespan.app, name="timespan, ts")
app.add_typer(note.app, name="note, n")
app.add_typer(log.app, name="log, l")
app.add_typer(tracker.app, name="tracker, tr")
app.add_typer(view.app, name="view, v")
# app.add_typer(doc.app, name="doc, d")
app.command(name="search, s")(search)
app.command(name="version, ve")(version)


@app.callback()
def main_callback(
    no_header: Annotated[
        bool,
        typer.Option(
            "--no-header",
            "-nh",
            help="Suppress header output in reports",
        ),
    ] = False,
    clear_ids: Annotated[
        bool,
        typer.Option(
            "--clear-ids/--no-clear-ids",
            help="Clear ID map",
        ),
    ] = False,
) -> None:
    """
    Granular - Organizational management in the CLI

    Global options that apply to all commands.
    """
    if no_header:
        view_state.set_show_header(False)
    if clear_ids:
        app_state.set_clear_ids(True)


def run() -> None:
    app()
