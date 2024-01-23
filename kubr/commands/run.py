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
from kubr.commands.utils.reply import confirmation_prompt, generate_jobs_table, mascot_message
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

        pod_events = []
        started_containers = 0

        # involvedObject.name={job.name}*,
        for line in stream:
            event_object = line["object"]
            if not event_object.metadata.name.startswith(job.name):
                continue
            if event_object.source.component == "cluster-autoscaler":
                autoscaler.append(event_object)
                continue

            if event_object.reason == "FailedScheduling":
                pod_events.append(event_object)

            if event_object.message.startswith("Successfully assigned"):
                progress.update(scheduling_pb, advance=node_update_step)
                if progress.tasks[scheduling_pb].completed:
                    run_state = "Init"

            if event_object.message == f"Started container {job.name}-init":
                progress.update(init_pb, advance=node_update_step)
                if progress.tasks[scheduling_pb].completed:
                    run_state = "Container"

            if event_object.message == f"Started container {job.name}":
                progress.update(container_pb, advance=node_update_step)
                started_containers += 1
                if started_containers == job.nodes:
                    status.update("Waiting for logs...")
                    break

            if "pod group is not ready" in event_object.message and len(pod_events):
                status.update(f"{run_state}... {event_object.message}\n \t Pod issue: {pod_events[-1].message}")
            else:
                status.update(f"{run_state}... {event_object.message}")

        log_found = 0
        while True:
            sleep(2)
            try:
                log_stream = self.backend.get_logs(job_name=job.name, namespace=job.namespace, tail=None, follow=True)
                for log in log_stream:
                    # TODO [run] stop if log stopped
                    if not log_found:
                        status.update("Job started!")
                        live_panel.stop()
                    print(log)
                    log_found += 1

                break
            except Exception:
                status.update("Waiting for logs...")

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

        if "-" in config.experiment.name:
            print(mascot_message(f"Job name {config.experiment.name} is invalid!"))
            return

        pods = self.backend.core_client.list_namespaced_pod(
            namespace=config.experiment.namespace, label_selector=f"volcano.sh/job-name={config.experiment.name}"
        )
        if len(pods.items) > 0:
            if confirmation_prompt(
                f"Job {config.experiment.name} already exists in namespace {config.experiment.namespace}. \n"
                f"Do you want to resubmit it?"
            ):
                self.backend.delete_job(job_name=config.experiment.name, namespace=config.experiment.namespace)

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
