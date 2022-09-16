import json
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("osparc-python-main")


ENVIRONS = ["INPUT_FOLDER", "OUTPUT_FOLDER"]
try:
    INPUT_FOLDER, OUTPUT_FOLDER = [Path(os.environ[v]) for v in ENVIRONS]
except KeyError:
    raise ValueError("Required env vars {ENVIRONS} were not set")

# NOTE: sync with schema in metadata!!
NUM_OUTPUTS = 4
OUTPUT_FILE_TEMPLATE = "output_{}.zip"


def _find_user_code_entrypoint(code_dir: Path) -> Path:
    logger.info("Searching for script main entrypoint ...")
    code_files = list(code_dir.rglob("*.py"))

    if not code_files:
        raise ValueError("No python code found")

    if len(code_files) > 1:
        code_files = list(code_dir.rglob("main.py"))
        if not code_files:
            raise ValueError("No entrypoint found (e.g. main.py)")
        if len(code_files) > 1:
            raise ValueError(f"Many entrypoints found: {code_files}")

    main_py = code_files[0]
    logger.info("Found %s as main entrypoint", main_py)
    return main_py


def _ensure_pip_requirements(code_dir: Path) -> Path:
    logger.info("Searching for requirements file ...")
    requirements = list(code_dir.rglob("requirements.txt"))
    if len(requirements) > 1:
        raise ValueError(f"Many requirements found: {requirements}")

    elif not requirements:
        # deduce requirements using pipreqs
        logger.info("Not found. Recreating requirements ...")
        requirements = code_dir / "requirements.txt"
        subprocess.run(
            f"pipreqs --savepath={requirements} --force {code_dir}".split(),
            shell=False,
            check=True,
            cwd=INPUT_FOLDER,
        )

        # TODO log subprocess.run

    else:
        requirements = requirements[0]
        logger.info(f"Found: {requirements}")
    return requirements


def _show_io_environments() -> None:
    for io_type in ["input", "output"]:
        logger.info(
            "%s ENVs available: %s",
            io_type.capitalize(),
            json.dumps(
                list(filter(lambda x: f"{io_type.upper()}_" in x, os.environ)), indent=2
            ),
        )


def setup():
    _show_io_environments()
    logger.info("Available data:")
    os.system("ls -tlah")

    user_code_entrypoint = _find_user_code_entrypoint(INPUT_FOLDER)
    requirements_txt = _ensure_pip_requirements(INPUT_FOLDER)

    logger.info("Preparing launch script ...")
    venv_dir = Path.home() / ".venv"
    script = [
        "#!/bin/sh",
        "set -o errexit",
        "set -o nounset",
        "IFS=$(printf '\\n\\t')",
        'echo "Creating virtual environment ..."',
        f'python3 -m venv --system-site-packages --symlinks --upgrade "{venv_dir}"',
        f'"{venv_dir}/bin/pip" install -U pip wheel setuptools',
        f'"{venv_dir}/bin/pip" install -r "{requirements_txt}"',
        f'echo "Executing code {user_code_entrypoint.name}..."',
        f'"{venv_dir}/bin/python3" "{user_code_entrypoint}"',
        'echo "DONE ..."',
    ]
    main_script_path = Path("main.sh")
    main_script_path.write_text("\n".join(script))


def teardown():
    logger.info("Zipping output...")
    for n in range(1, NUM_OUTPUTS + 1):
        output_path = OUTPUT_FOLDER / f"output_{n}"
        archive_file_path = OUTPUT_FOLDER / OUTPUT_FILE_TEMPLATE.format(n)
        logger.info("Zipping %s into %s...", output_path, archive_file_path)
        shutil.make_archive(
            f"{(archive_file_path.parent / archive_file_path.stem)}",
            format="zip",
            root_dir=output_path,
            logger=logger,
        )
        logger.info("Zipping %s into %s done", output_path, archive_file_path)
    logger.info("Zipping done.")


if __name__ == "__main__":
    action = "setup" if len(sys.argv) == 1 else sys.argv[1]
    try:
        if action == "setup":
            setup()
        else:
            teardown()
    except Exception as err:  # pylint: disable=broad-except
        logger.error("%s . Stopping %s", err, action)
