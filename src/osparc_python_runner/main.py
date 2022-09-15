import logging
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("osparc-python-main")


ENVIRONS = ["INPUT_FOLDER", "OUTPUT_FOLDER"]
try:
    INPUT_FOLDER, OUTPUT_FOLDER = [Path(os.environ[v]) for v in ENVIRONS]
except KeyError:
    raise ValueError("Required env vars {ENVIRONS} were not set")

# NOTE: sync with schema in metadata!!
NUM_OUTPUTS = 4
OUTPUT_FILE_TEMPLATE = "output_{output_number}.zip"


def run_cmd(cmd: str):
    subprocess.run(cmd.split(), shell=False, check=True, cwd=INPUT_FOLDER)
    # TODO: deal with stdout, log? and error??


def unzip_dir(parent: Path):
    for filepath in list(parent.rglob("*.zip")):
        logger.info("Unzipping '%s'...", filepath.name)
        if zipfile.is_zipfile(filepath):
            with zipfile.ZipFile(filepath) as zf:
                zf.extractall(filepath.parent)
        logger.info("Unzipping '%s' done", filepath.name)



def ensure_main_entrypoint(code_dir: Path) -> Path:
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
    return main_py


def ensure_requirements(code_dir: Path) -> Path:
    requirements = list(code_dir.rglob("requirements.txt"))
    if len(requirements) > 1:
        raise ValueError(f"Many requirements found: {requirements}")

    elif not requirements:
        # deduce requirements using pipreqs
        logger.info("Not found. Recreating requirements ...")
        requirements = code_dir / "requirements.txt"
        run_cmd(f"pipreqs --savepath={requirements} --force {code_dir}")

        # TODO log subprocess.run

    else:
        requirements = requirements[0]
    return requirements


def setup():
    for n in range(NUM_OUTPUTS):
        output_sub_folder = OUTPUT_FOLDER / f"output_{n+1}"
        logger.info("Creating %s", f"{output_sub_folder=}")
        output_sub_folder.mkdir(parents=True)
        
    # NOTE The inputs defined in ${INPUT_FOLDER}/inputs.json are available as env variables by their key in capital letters
    # For example: input_1 -> $INPUT_1
    #

    logger.info("Processing input from %s ...", INPUT_FOLDER)
    unzip_dir(INPUT_FOLDER)

    logger.info("Searching main entrypoint ...")
    user_main_py = ensure_main_entrypoint(INPUT_FOLDER)
    logger.info("Found %s as main entrypoint", user_main_py)

    logger.info("Searching requirements ...")
    requirements_txt = ensure_requirements(INPUT_FOLDER)

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
        f'echo "Executing code {user_main_py.name}..."',
        f'"{venv_dir}/bin/python3" "{user_main_py}"',
        'echo "DONE ..."',
    ]
    main_script_path = Path("main.sh")
    main_script_path.write_text("\n".join(script))



def teardown():
    logger.info("Zipping output...")
    for n in range(NUM_OUTPUTS):
        output_path = OUTPUT_FOLDER / f"output_{n+1}"
        archive_file_path = OUTPUT_FOLDER / OUTPUT_FILE_TEMPLATE.format(output_number=(n+1))
        logger.info("Zipping %s into %s...", output_path, archive_file_path)
        shutil.make_archive(f"{(archive_file_path.parent / archive_file_path.stem)}", format="zip", root_dir=OUTPUT_FOLDER, base_dir=f"output_{n+1}", logger=logger)
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
