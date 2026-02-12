# SPDX-License-Identifier: MIT

from textwrap import dedent

from granular import configuration
from granular.version.git import Git


class Version:
    def __init__(self) -> None:
        self.git = Git()

    def initialize_data_versioning(self) -> None:
        if not self.git.is_git_repo(configuration.DATA_PATH):
            self.git.init(configuration.DATA_PATH)
            gitignore_path = configuration.DATA_PATH / ".gitignore"
            gitignore_path.touch()
            gitignore_path.write_text(
                dedent("""
                    id_map.yaml
                """)
            )

    def create_data_checkpoint(self, message: str) -> None:
        if self.git.is_git_repo(configuration.DATA_PATH):
            self.git.update(configuration.DATA_PATH, message)
