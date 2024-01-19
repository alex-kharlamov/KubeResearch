from datetime import datetime
from time import sleep
from typing import Optional

import humanize
from kubernetes import watch
from pydantic_yaml import parse_yaml_raw_as
from rich import print
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress

from kubr.backends.base import JobOperationStatus
from kubr.commands.base import BaseCommand
from kubr.commands.utils.drawing import generate_jobs_table, mascot_message
from kubr.config.job import Job, JobState
from kubr.config.runner import RunnerConfig


def visualize_job(job):
    job.age = humanize.naturaldelta(datetime.utcnow() - job.age)
    print(generate_jobs_table([job], state=str(JobState.Pending)))


class RunCommand(BaseCommand):
    @staticmethod
    def add_parser(subparsers):
        run_parser = subparsers.add_parser("run", help="Submit a new job")
        run_parser.add_argument("config", help="Path to run config", type=str)
        run_parser.add_argument("-i", "--image", help="Image to run")
        run_parser.add_argument("-e", "--entrypoint", help="Entrypoint to run")
        run_parser.add_argument("-n", "--namespace", help="Namespace to submit job to")
        run_parser.add_argument("--name", help="Name of job")
        run_parser.add_argument("-v", "--verbose", help="Verbose output", action="store_true", default=False)

    def show_job_run(self, job: Job):
        node_update_step = 100 / job.nodes
        console = Console()

        w = watch.Watch()
        stream = w.stream(
            self.backend.core_client.list_namespaced_event,
            namespace=job.namespace,
        )
        autoscaler = []

        progress = Progress()
        status = console.status("Running job...")

        live_panel = Live(Panel(Group(status, progress)))
        live_panel.start()

        scheduling_pb = progress.add_task("[red]Scheduling...", total=100)
        init_pb = progress.add_task("[green]Init...", total=100)
        container_pb = progress.add_task("[cyan]Container...", total=100)

        run_state = "Scheduling"

        # involvedObject.name={job.name}*,
        for line in stream:
            event_object = line["object"]
            if not event_object.metadata.name.startswith(job.name):
                continue
            if event_object.source.component == "cluster-autoscaler":
                autoscaler.append(event_object)
                continue

            if event_object.message.startswith("Successfully assigned"):
                progress.update(scheduling_pb, advance=node_update_step)
                if progress.tasks[scheduling_pb].completed:
                    run_state = "Init"

            if event_object.message == f"Started container {job.name}-init":
                progress.update(init_pb, advance=node_update_step)
                if progress.tasks[scheduling_pb].completed:
                    run_state = "Container"

            if event_object.message == f"Started container {job.name}":
                progress.update(container_pb, advance=75 / job.nodes)
                break

            status.update(f"{run_state}... {event_object.message}")

        while True:
            sleep(2)
            try:
                log_stream = self.backend.get_logs(job_name=job.name, namespace=job.namespace, tail=None, follow=True)
                for log in log_stream:
                    progress.update(container_pb, advance=25)
                    status.update("Job started!")
                    live_panel.stop()
                    print(log)
            except Exception:
                status.update("Container starting...")

    def __call__(
        self,
        config: str,
        image: Optional[str] = None,
        name: Optional[str] = None,
        entrypoint: Optional[str] = None,
        namespace: Optional[str] = None,
        verbose: bool = False,
    ):
        # TODO [run] check if config exists on cluster and ask to resubmit

        with open(config, "r") as f:
            config = f.read()
        config = parse_yaml_raw_as(RunnerConfig, config)

        config.experiment.name = name or config.experiment.name
        config.container.image = image or config.container.image
        config.container.entrypoint = entrypoint or config.container.entrypoint
        config.experiment.namespace = namespace or config.experiment.namespace

        job, status = self.backend.run_job(config)
        if status == JobOperationStatus.Failed:
            print(mascot_message(f"Job {config.experiment.name} running failed!"))

        elif status == JobOperationStatus.Success:
            if verbose:
                self.show_job_run(job)
            else:
                visualize_job(job)
        else:
            print(mascot_message(f"Job {config.experiment.name} is in unknown state!"))
