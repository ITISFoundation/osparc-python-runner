import pytest
import sys
import os
from pathlib import Path
import time


EXPECTED_INPUTS_ENVS = ["INPUT_FOLDER", *(f"INPUT_{i}" for i in range(1, 6))]
EXPECTED_OUPUTS_ENVS = ["OUTPUT_FOLDER", *(f"OUTPUT_{i}" for i in range(1, 5))]


@pytest.mark.parametrize("env_var", EXPECTED_INPUTS_ENVS + EXPECTED_OUPUTS_ENVS)
def test_environment_variable(env_var: str):
    assert env_var in os.environ
    # assert os.path.exists(os.environ[env_var])


def test_write_to_console():
    print("Hoi zaeme!")
    print("TEST stderr: 🧪", file=sys.stderr)
    print("TEST stdout: 🧪", file=sys.stdout)


def test_progress():
    """Should be parsed by osparc progress bar"""
    total = 100
    for part in range(0, total + 1):
        print(f"[PROGRESS] {part}/{total}")
        time.sleep(0.001)


def test_inputs():
    assert (Path(os.environ["INPUT_1"]) / "input_script_1.py").exists()
    assert (Path(os.environ["INPUT_1"]) / "requirements.txt").exists()


def test_outputs():
    """write a file in each output"""
    for output_folder_env in [*(f"OUTPUT_{i}" for i in range(1, 5))]:
        folder = Path(os.environ[output_folder_env])
        assert folder.exists()
        for number in range(1, 3):
            file = Path(folder) / f"some_output_{number}_file"
            file.write_text(f"Hello this is file {number}")
            assert file.exists()


if __name__ == "__main__":
    sys.exit(
        pytest.main(
            [
                "--verbose",
                "--color=no",
                "--capture=no",
                "--log-cli-level=DEBUG",
                '--log-date-format="%Y-%m-%d %H:%M:%S"',
                '--log-format="%(asctime)s %(levelname)s %(message)s"',
                sys.argv[0],
            ]
        )
    )
