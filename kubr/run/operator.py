from typing import Optional

from kubr.backends.volcano import VolcanoBackend
from kubr.config.runner import RunnerConfig
from pydantic_yaml import parse_yaml_raw_as

class RUNOperator:
    def __init__(self, backend=None):
        self.backend = backend or VolcanoBackend()

    def __call__(self, config: str, image: Optional[str] = None,
                 name: Optional[str] = None, entrypoint: Optional[str] = None, namespace: Optional[str] = None):
        with open(config, 'r') as f:
            config = f.read()
        config = parse_yaml_raw_as(RunnerConfig, config)

        config.exp_config.exp_name = name or config.exp_config.exp_name
        config.container_config.image = image or config.container_config.image
        config.container_config.entrypoint = entrypoint or config.container_config.entrypoint
        config.exp_config.namespace = namespace or config.exp_config.namespace

        return self.backend.run_job(config)
