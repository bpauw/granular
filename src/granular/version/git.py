# SPDX-License-Identifier: MIT

import shutil
import subprocess
from enum import Enum
from pathlib import Path
from typing import Optional


class GitCommand(Enum):
    STATUS = 0
    INIT = 1
    UPDATE = 2


class Git:
    def is_git_repo(self, folder: Path) -> bool:
        self.__fail_if_git_not_available()
        results = self.__execute_git_command(GitCommand.STATUS, folder)
        final_result = results[-1]
        if "not a git repository" in final_result:
            return False
        return True

    def init(self, folder: Path) -> None:
        self.__fail_if_git_not_available()
        self.__execute_git_command(GitCommand.INIT, folder)

    def update(self, folder: Path, message: str) -> None:
        self.__fail_if_git_not_available()
        self.__execute_git_command(GitCommand.UPDATE, folder, message=message)

    def __fail_if_git_not_available(self) -> None:
        git_available = shutil.which("git")
        if git_available is None:
            raise Exception("Git is not available on the system")

    def __execute_git_command(
        self, command: GitCommand, folder: Path, message: Optional[str] = None
    ) -> list[str]:
        git_commands: list[list[str]] = [
            ["git", "-C", str(folder.resolve())],
        ]

        match command:
            case GitCommand.STATUS:
                git_commands[0].append("status")
            case GitCommand.INIT:
                git_commands[0].append("init")
            case GitCommand.UPDATE:
                commit_message = message or ""
                git_commands[0] += ["add", "-vA"]
                git_commands.append(
                    ["git", "-C", str(folder.resolve()), "commit", "-m", commit_message]
                )

        results = []

        for git_command in git_commands:
            result = subprocess.run(git_command, text=True, capture_output=True)
            result_str = result.stdout + result.stderr
            results.append(result_str)

        return results
