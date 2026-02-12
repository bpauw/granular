from granular.repository.context import CONTEXT_REPO
from granular.repository.project import PROJECT_REPO
from granular.repository.tag import TAG_REPO


def complete_tag(incomplete: str) -> list[str]:
    """Return list of available tags for shell completion."""

    all_tags = TAG_REPO.get_all_tags()
    return [tag for tag in all_tags if tag.startswith(incomplete)]


def complete_project(incomplete: str) -> list[str]:
    """Return list of available projects for shell completion."""

    all_projects = PROJECT_REPO.get_all_projects()
    return [project for project in all_projects if project.startswith(incomplete)]


def complete_context(incomplete: str) -> list[str]:
    """Return list of available context names for shell completion."""
    all_contexts = CONTEXT_REPO.get_all_contexts()
    return [
        context["name"]
        for context in all_contexts
        if context["name"] and context["name"].startswith(incomplete)
    ]
