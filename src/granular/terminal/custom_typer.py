# SPDX-License-Identifier: MIT

import re
from typing import Any, Optional

import click
import typer
import typer.core
from rich.console import Console
from rich.padding import Padding

from granular.repository.context import ContextRepository

console = Console()


def _show_active_context(ctx: click.Context) -> None:
    """Show the active context header if not already shown in this context chain"""
    # Check if we've already shown the context in this invocation by looking at the context
    if hasattr(ctx, "_context_shown") and ctx._context_shown:
        return

    # Mark all contexts in the chain as having shown the context
    current: Optional[click.Context] = ctx
    while current is not None:
        current._context_shown = True  # type: ignore[attr-defined]
        current = current.parent

    try:
        repository = ContextRepository()
        active_context = repository.get_active_context()
        context_name = active_context["name"]

        # Print header with active context
        console.print()
        console.print(
            Padding(
                f"[bold plum1]Active Context: {context_name}[/bold plum1]",
                (0, 0, 0, 1),
            )
        )
    except Exception:
        # Silently handle errors (e.g., if data file doesn't exist yet)
        pass


class ContextAwareCommand(typer.core.TyperCommand):
    """Custom command class that displays active context in help text"""

    def format_help(
        self, ctx: click.Context, formatter: click.formatting.HelpFormatter
    ) -> None:
        _show_active_context(ctx)

        # Call original format_help to generate standard help
        super().format_help(ctx, formatter)


class AliasedTyperGroup(typer.core.TyperGroup):
    """Custom TyperGroup that supports comma-separated command aliases"""

    _CMD_SPLIT_P = re.compile(r" ?, ?")

    def get_command(self, ctx: click.Context, cmd_name: str) -> Optional[click.Command]:
        """Override to resolve aliases to the full command name"""
        cmd_name = self._group_cmd_name(cmd_name)
        return super().get_command(ctx, cmd_name)

    def _group_cmd_name(self, default_name: str) -> str:
        """Find the full command name if default_name is an alias"""
        for cmd in self.commands.values():
            name = cmd.name
            if name and default_name in self._CMD_SPLIT_P.split(name):
                return name
        return default_name

    def add_command(self, cmd: click.Command, name: Optional[str] = None) -> None:
        """Override to prevent duplicate commands from being added"""
        if name is None:
            name = cmd.name

        # Check if this command is already registered (as an alias)
        existing_name = self._group_cmd_name(name or "")
        if existing_name in self.commands and existing_name != name:
            # This is an alias, don't add it again
            return

        super().add_command(cmd, name)


class ContextAwareTyperGroup(AliasedTyperGroup):
    """Custom TyperGroup that displays active context in help text and supports aliases"""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # Set the command class for all commands added to this group
        self.command_class = ContextAwareCommand

    def list_commands(self, ctx: click.Context) -> list[str]:
        """Return commands in desired order (not insertion order due to Typer internals)"""
        # Define the desired order
        desired_order = [
            "config, c",
            "context, cx",
            "task, t",
            "audit, a",
            "event, e",
            "timespan, ts",
            "tracker, tr",
            "note, n",
            "log, l",
            "view, v",
            "custom-view, cv",
            "search, s",
            "doc, d",
            "version, ve",
        ]

        # Return commands in desired order, then any extras not in the list
        result = []
        for cmd_name in desired_order:
            if cmd_name in self.commands:
                result.append(cmd_name)

        # Add any commands not in the desired order list
        for cmd_name in self.commands.keys():
            if cmd_name not in result:
                result.append(cmd_name)

        return result

    def get_command(self, ctx: click.Context, cmd_name: str) -> Optional[click.Command]:
        """Override to wrap commands with context-aware formatting"""
        cmd = super().get_command(ctx, cmd_name)

        if cmd is not None and not isinstance(cmd, ContextAwareCommand):
            # Replace the format_help method of the command
            original_format_help = cmd.format_help

            def context_aware_format_help(
                help_ctx: click.Context, formatter: click.formatting.HelpFormatter
            ) -> None:
                _show_active_context(help_ctx)

                # Call original format_help to generate standard help
                original_format_help(help_ctx, formatter)

            cmd.format_help = context_aware_format_help  # type: ignore

        return cmd

    def format_help(
        self, ctx: click.Context, formatter: click.formatting.HelpFormatter
    ) -> None:
        _show_active_context(ctx)

        # Call original format_help to generate standard help
        super().format_help(ctx, formatter)


class AlphabeticalContextAwareGroup(ContextAwareTyperGroup):
    """Combines alphabetical ordering with context awareness and alias support"""

    def list_commands(self, ctx: click.Context) -> list[str]:
        return sorted(super().list_commands(ctx))
