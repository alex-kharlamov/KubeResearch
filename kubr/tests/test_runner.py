import pytest
from kubr.config.runner import RunnerConfig, ExperimentConfig, ResourceConfig
from pydantic_yaml import parse_yaml_raw_as
from kubr.backends.volcano import VolcanoBackend
from kubr.backends.base import BaseBackend

base_config = """
container:
    image: "jannnash/noop:latest"

resources:
    cpu: 1
    mem: 1Gi

experiment:
    name: "pytest-test"
    namespace: "default"
"""


class TestRunner:
    @pytest.fixture
    def runner(self):
        backend = VolcanoBackend()
        runner_cfg = parse_yaml_raw_as(RunnerConfig, base_config)
        return backend, runner_cfg

    def test_run(self, backend: BaseBackend, runner: RunnerConfig):
        backend.run_job(runner)

    @pytest.mark.parametrize("name, namespace, queue",
                             [("pytest-test", "default", "default"),
                              pytest.param("pytest-test", "default", "test", marks=pytest.mark.xfail),
                              pytest.param("pytest-test", "test", "default", marks=pytest.mark.xfail),
                              pytest.param("pytest-test", "test", "test", marks=pytest.mark.xfail)
                              ])
    def test_experiment_base(self, backend: BaseBackend, runner: RunnerConfig,
                             name: str, namespace: str, queue: str, env: dict):
        experiment_config = ExperimentConfig(name=name, namespace=namespace, queue=queue)
        runner.experiment = experiment_config

        backend.run_job(runner)


