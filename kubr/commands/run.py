from typing import Optional

from kubr.backends.volcano import VolcanoBackend
from kubr.commands.base import BaseCommand
from kubr.config.runner import RunnerConfig
from pydantic_yaml import parse_yaml_raw_as

class RunCommand(BaseCommand):
    @staticmethod
    def add_parser(subparsers):
        run_parser = subparsers.add_parser('run', help='Submit a new job')
        run_parser.add_argument('config', help='Path to run config', type=str)
        run_parser.add_argument('-i', '--image', help='Image to run')
        run_parser.add_argument('-e', '--entrypoint', help='Entrypoint to run')
        run_parser.add_argument('-n', '--namespace', help='Namespace to submit job to')
        run_parser.add_argument('--name', help='Name of job')
        run_parser.add_argument('-it', '--interactive', help='Run job interactively', action='store_true',
                                default=False)

    def __call__(self, config: str, image: Optional[str] = None,
                 name: Optional[str] = None, entrypoint: Optional[str] = None,
                 namespace: Optional[str] = None):
        with open(config, 'r') as f:
            config = f.read()
        config = parse_yaml_raw_as(RunnerConfig, config)

        config.experiment.name = name or config.experiment.name
        config.container.image = image or config.container.image
        config.container.entrypoint = entrypoint or config.container.entrypoint
        config.experiment.namespace = namespace or config.experiment.namespace

        return self.backend.run_job(config)
