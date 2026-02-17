# SPDX-License-Identifier: MIT

from typing import Annotated, Optional, cast

import typer

from granular.model.entity_id import EntityId
from granular.repository.configuration import (
    CONFIGURATION_REPO,
)
from granular.repository.context import CONTEXT_REPO
from granular.template.context import get_context_template
from granular.terminal.completion import complete_context
from granular.terminal.custom_typer import ContextAwareTyperGroup
from granular.terminal.validate import validate_unique_context_name
from granular.version.version import Version
from granular.view.view.views import context as context_report

app = typer.Typer(cls=ContextAwareTyperGroup, no_args_is_help=True)


@app.command("add, a", no_args_is_help=True)
def add(
    name: str,
    auto_added_tags: Annotated[
        Optional[list[str]],
        typer.Option("--auto-added-tag", "-a", help="accepts multiple tag options"),
    ] = None,
    auto_added_project: Annotated[
        Optional[str],
        typer.Option(
            "--auto-added-project", "-p", help="valid input: project.subproject"
        ),
    ] = None,
    default_note_folder: Annotated[
        Optional[str],
        typer.Option(
            "--default-note-folder",
            "-dnf",
            help="Default folder for external notes in this context",
        ),
    ] = None,
) -> None:
    # Validate that the context name is unique
    validate_unique_context_name(name)

    # Validate folder if provided
    if default_note_folder:
        config_temp = CONFIGURATION_REPO.get_config()
        note_folders = config_temp.get("note_folders", [])
        if note_folders is None:
            note_folders = []

        if not note_folders or default_note_folder not in [
            f["name"] for f in note_folders
        ]:
            typer.echo(
                f"Error: Folder '{default_note_folder}' not in configured note_folders",
                err=True,
            )
            raise typer.Exit(1)

    config = CONFIGURATION_REPO.get_config()
    version = Version()

    context = get_context_template()
    context["name"] = name
    context["auto_added_tags"] = auto_added_tags
    context["auto_added_project"] = auto_added_project
    context["default_note_folder"] = default_note_folder

    context_id = CONTEXT_REPO.save_new_context(context)
    new_context = CONTEXT_REPO.get_context(context_id)

    if config["use_git_versioning"]:
        version.create_data_checkpoint(f"add context: {new_context['name']}")

    context_report.single_context_view(name, new_context)


@app.command("activate, t", no_args_is_help=True)
def activate(
    name: Annotated[
        str,
        typer.Argument(autocompletion=complete_context),
    ],
) -> None:
    config = CONFIGURATION_REPO.get_config()
    version = Version()

    # Get the context by name to verify it exists
    context_to_activate = CONTEXT_REPO.get_context_by_name(name)
    context_id = cast(EntityId, context_to_activate["id"])

    # First, deactivate all contexts
    all_contexts = CONTEXT_REPO.get_all_contexts()
    for context in all_contexts:
        if context["active"]:
            CONTEXT_REPO.modify_context(
                id=cast(EntityId, context["id"]),
                new_name=None,
                active=False,
                auto_added_tags=None,
                auto_added_project=None,
                filter=None,
                default_note_folder=None,
                remove_auto_added_tags=False,
                remove_auto_added_project=False,
                remove_filter=False,
                remove_default_note_folder=False,
            )

    # Then activate the specified context
    CONTEXT_REPO.modify_context(
        id=context_id,
        new_name=None,
        active=True,
        auto_added_tags=None,
        auto_added_project=None,
        filter=None,
        default_note_folder=None,
        remove_auto_added_tags=False,
        remove_auto_added_project=False,
        remove_filter=False,
        remove_default_note_folder=False,
    )

    # Show the activated context
    activated_context = CONTEXT_REPO.get_context(context_id)
    activated_context_name = cast(str, activated_context["name"])

    if config["use_git_versioning"]:
        version.create_data_checkpoint(f"activate context: {activated_context_name}")

    context_report.single_context_view(activated_context_name, activated_context)
