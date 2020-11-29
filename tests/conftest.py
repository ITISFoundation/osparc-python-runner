# pylint:disable=unused-variable
# pylint:disable=unused-argument
# pylint:disable=redefined-outer-name

import sys
from pathlib import Path

import pytest

pytest_plugins = [
    "service_integration.pytest_plugin.folder_structure",
    "service_integration.pytest_plugin.validation_data",
    "service_integration.pytest_plugin.docker_integration",
]


current_dir = Path(sys.argv[0] if __name__ ==
                   "__main__" else __file__).resolve().parent


@pytest.fixture(scope='session')
def project_slug_dir() -> Path:
    project_slug_dir = current_dir.parent
    assert project_slug_dir.exists()
    return project_slug_dir


@pytest.fixture(scope='session')
def git_root_dir() -> Path:
    # finds where is .git
    root_dir = current_dir
    while root_dir.as_posix() != "/" and not Path(root_dir / ".git").exists():
        root_dir = root_dir.parent
    if root_dir.as_posix() == "/":
        return None
    return root_dir
