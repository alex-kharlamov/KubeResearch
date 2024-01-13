from kubr.backends.volcano import VolcanoBackend
from kubr.config.runner import RunnerConfig
from pydantic_yaml import parse_yaml_raw_as

class RUNOperator:
    def __init__(self, backend=None):
        self.backend = backend or VolcanoBackend()

    def __call__(self, config: str):
        with open(config, 'r') as f:
            config = f.read()

        config = parse_yaml_raw_as(RunnerConfig, config)
        return self.backend.run_job(config)
