import pytest
import sys
import os


EXPECTED_INPUTS_ENVS = ["INPUT_FOLDER", *("INPUT_{i}" for i in range(1, 6))]
EXPECTED_OUPUTS_ENVS = ["OUTPUT_FOLDER", *("OUTPUT_{i}" for i in range(1, 6))]


@pytest.mark.parametrize("env_var", EXPECTED_INPUTS_ENVS + EXPECTED_OUPUTS_ENVS)
def test_environment_variables(env_var: str):
    assert env_var in os.environ
    assert os.path.exists(os.environ[env_var])


def test_write_to_console():
    print("Hoi zaeme!")
    print("TEST stderr: 🧪", file=sys.stderr)
    print("TEST stdout: 🧪", file=sys.stdout)


def test_progress():
    pass


def test_outputs():
    pass


def test_inputs():
    pass


if __name__ == "__main__":
    sys.exit(
        pytest.main(
            [
                "--verbose",
                "--color=yes",
                "-s",
                "--log-cli-level=DEBUG",
                '--log-date-format="%Y-%m-%d %H:%M:%S"',
                '--log-format="%(asctime)s %(levelname)s %(message)s"',
                sys.argv[0],
            ]
        )
    )
