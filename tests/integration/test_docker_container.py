# pylint:disable=unused-variable
# pylint:disable=unused-argument
# pylint:disable=redefined-outer-name

import filecmp
import json
import os
import shutil
from pathlib import Path
from pprint import pformat
from typing import Dict, Iterator

import docker
import docker.errors
import docker.models.containers
import pytest

_FOLDER_NAMES = ["input", "output"]
_CONTAINER_FOLDER = Path("/home/scu/data")


@pytest.fixture
def host_folders(temporary_path: Path) -> Dict[str, Path]:
    tmp_dir = temporary_path

    host_folders = {}
    for folder in _FOLDER_NAMES:
        path = tmp_dir / folder
        if path.exists():
            shutil.rmtree(path)
        path.mkdir()
        # we need to ensure the path is writable for the docker container (Gitlab-CI case)
        os.chmod(str(path), 0o775)
        assert path.exists()
        host_folders[folder] = path

    return host_folders


@pytest.fixture
def container_variables() -> Dict:
    # of type INPUT_FOLDER=/home/scu/data/input
    env = {
        "{}_FOLDER".format(str(folder).upper()): (_CONTAINER_FOLDER / folder).as_posix()
        for folder in _FOLDER_NAMES
    }
    return env


@pytest.fixture
def validation_folders(validation_dir: Path) -> Dict[str, Path]:
    return {folder: (validation_dir / folder) for folder in _FOLDER_NAMES}


@pytest.fixture
def docker_container(
    validation_folders: Dict[str, Path],
    host_folders: Dict[str, Path],
    docker_client: docker.DockerClient,
    docker_image_key: str,
    container_variables: Dict,
) -> Iterator[docker.models.containers.Container]:
    # copy files to input folder, copytree needs to not have the input folder around.
    host_folders["input"].rmdir()
    shutil.copytree(validation_folders["input"], host_folders["input"])
    assert Path(host_folders["input"]).exists()
    # prepare output folders
    host_folders["output"].rmdir()
    for output_folder in validation_folders["output"].glob("*"):
        if not output_folder.is_dir():
            continue
        # create the same folder in the output
        host_output_folder = host_folders["output"] / output_folder.name
        host_output_folder.mkdir(parents=True)
        assert host_output_folder.exists()

    # run the container (this may take some time)
    container = None
    try:
        volumes = {
            host_folders[folder]: {
                "bind": container_variables["{}_FOLDER".format(str(folder).upper())]
            }
            for folder in _FOLDER_NAMES
        }
        container = docker_client.containers.run(
            docker_image_key,
            "run",
            detach=True,
            remove=False,
            volumes=volumes,
            environment=container_variables,
        )
        assert isinstance(container, docker.models.containers.Container)
        response = container.wait()
        if response["StatusCode"] > 0:
            logs = container.logs(timestamps=True)
            pytest.fail(
                "The container stopped with exit code {}\n\n\ncommand:\n {}, \n\n\nlog:\n{}".format(
                    response["StatusCode"],
                    "run",
                    pformat(
                        (container.logs(timestamps=True).decode("UTF-8")).split("\n"),
                        width=200,
                    ),
                )
            )
        else:
            yield container
    except docker.errors.ContainerError as exc:
        # the container did not run correctly
        assert isinstance(container, docker.models.containers.Container)
        pytest.fail(
            "The container stopped with exit code {}\n\n\ncommand:\n {}, \n\n\nlog:\n{}".format(
                exc.exit_status,
                exc.command,
                pformat(
                    (container.logs(timestamps=True).decode("UTF-8")).split("\n"),
                    width=200,
                ),
            )
        )
    finally:
        # cleanup
        if container:
            assert isinstance(container, docker.models.containers.Container)
            container.remove()


def _convert_to_simcore_labels(image_labels: Dict) -> Dict:
    io_simcore_labels = {}
    for key, value in image_labels.items():
        if str(key).startswith("io.simcore."):
            simcore_label = json.loads(value)
            simcore_keys = list(simcore_label.keys())
            assert len(simcore_keys) == 1
            simcore_key = simcore_keys[0]
            simcore_value = simcore_label[simcore_key]
            io_simcore_labels[simcore_key] = simcore_value
    assert len(io_simcore_labels) > 0
    return io_simcore_labels


def test_run_container(
    validation_folders: Dict[str, Path],
    host_folders: Dict[str, Path],
    docker_container: docker.models.containers.Container,
):
    for folder in _FOLDER_NAMES:
        # test if the files that should be there are actually there and correct
        list_of_files = [
            x.relative_to(validation_folders[folder])
            for x in validation_folders[folder].rglob("*")
            if x.is_file() and not ".gitkeep" in x.name
        ]
        for file_name in list_of_files:
            assert Path(
                host_folders[folder] / file_name
            ).exists(), f"missing {file_name=} in {host_folders[folder]=}"
        match, mismatch, errors = filecmp.cmpfiles(
            host_folders[folder],
            validation_folders[folder],
            list_of_files,
            shallow=False,
        )
        assert match
        assert not mismatch
        # assert not mismatch, "wrong/incorrect files in {}".format(host_folders[folder])
        assert not errors, "missing files in {}".format(host_folders[folder])

    # check the output is correct based on container labels
    output_cfg = {}
    output_cfg_file = Path(host_folders["output"] / "outputs.json")
    if output_cfg_file.exists():
        with output_cfg_file.open(encoding="utf-8") as fp:
            output_cfg = json.load(fp)

    container_labels = docker_container.labels
    io_simcore_labels = _convert_to_simcore_labels(container_labels)
    assert "outputs" in io_simcore_labels
    for key, value in io_simcore_labels["outputs"].items():
        assert "type" in value
        # rationale: files are on their own and other types are in inputs.json
        if not "data:" in value["type"]:
            # check that keys are available
            assert key in output_cfg
        else:
            # it's a file and it should be in the folder as well using key as the filename
            filename_to_look_for = key
            if "fileToKeyMap" in value:
                # ...or there is a mapping
                assert len(value["fileToKeyMap"]) > 0
                for filename, mapped_value in value["fileToKeyMap"].items():
                    assert mapped_value == key
                    filename_to_look_for = filename
            assert (host_folders["output"] / filename_to_look_for).exists()
