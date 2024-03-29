import re
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Iterable, Mapping, Optional

import humanize
from kubernetes import client, config, watch
from rich import print
from tabulate import tabulate

from kubr.backends.base import BaseBackend, JobOperationStatus
from kubr.backends.k8s_runner import create_pod_definition
from kubr.config.job import Job, JobBackend, JobState, JobType
from kubr.config.runner import EnvVar, RunnerConfig


def normalize_str(data: str) -> str:
    """
    Invokes ``lower`` on thes string and removes all
    characters that do not satisfy ``[a-z0-9\\-]`` pattern.
    This method is mostly used to make sure kubernetes and gcp_batch scheduler gets
    the job name that does not violate its restrictions.
    """
    if data.startswith("-"):
        data = data[1:]
    pattern = r"[a-z0-9\-]"
    return "".join(re.findall(pattern, data.lower()))


class RetryPolicy(str, Enum):
    REPLICA = "REPLICA"
    APPLICATION = "APPLICATION"


RETRY_POLICIES: Mapping[str, Iterable[Mapping[str, str]]] = {
    RetryPolicy.REPLICA: [],
    RetryPolicy.APPLICATION: [
        {"event": "PodEvicted", "action": "RestartJob"},
        {"event": "PodFailed", "action": "RestartJob"},
    ],
}


class VolcanoBackend(BaseBackend):
    DEFAULT_TASK_NAME = "worker"

    def __init__(self):
        self.kubernetes_config = config.load_config()
        self.crd_client = client.CustomObjectsApi()
        self.core_client = client.CoreV1Api()

    def run_job(self, run_config: RunnerConfig) -> [Job, JobOperationStatus]:
        tasks = []

        for replica_id in range(run_config.resources.nodes):
            rank0_env = f"VC_{normalize_str(self.DEFAULT_TASK_NAME)}_0_HOSTS".upper()
            if replica_id == 0:
                rank0_env = "KUBR_RANK0_HOST"
                run_config.container.env.append(EnvVar(name="KUBR_RANK0_HOST", value="localhost"))

            pod = create_pod_definition(
                pod_name=run_config.experiment.name,
                runner_config=run_config,
                service_account=None,
                rank0_env=rank0_env,
            )

            # pod.metadata.labels.update(
            #     pod_labels(
            #         app=app,
            #         role_idx=role_idx,
            #         role=role,
            #         replica_id=replica_id,
            #         app_id=unique_app_id,
            #     )
            # )

            task: Dict[str, Any] = {
                "replicas": 1,
                "name": f"{self.DEFAULT_TASK_NAME}-{replica_id}",
                "template": pod,
            }
            if run_config.experiment.worker_max_retries > 0:
                task["maxRetry"] = run_config.experiment.worker_max_retries
                task["policies"] = RETRY_POLICIES[RetryPolicy.APPLICATION]

            task["minAvailable"] = 1

            tasks.append(task)

        job_spec = {
            "schedulerName": "volcano",
            "queue": run_config.experiment.queue,
            "tasks": tasks,
            "maxRetry": run_config.experiment.job_retries,
            "plugins": {
                # https://github.com/volcano-sh/volcano/issues/533
                "svc": ["--publish-not-ready-addresses"],
                "env": [],
            },
        }
        # if run_config.experiment.priority_class is not None:
        #     job_spec["priorityClassName"] = run_config.experiment.priority_class

        resource: Dict[str, object] = {
            "apiVersion": "batch.volcano.sh/v1alpha1",
            "kind": "Job",
            "metadata": {"name": f"{run_config.experiment.name}"},
            "spec": job_spec,
        }

        try:
            self.crd_client.create_namespaced_custom_object(
                group="batch.volcano.sh",
                version="v1alpha1",
                namespace=run_config.experiment.namespace,
                plural="jobs",
                body=resource,
            )

        except Exception as e:
            # TODO [run] add exception printing
            print(e)
            return None, JobOperationStatus.Failed

        job = Job(
            type=JobType.torchrun,
            backend=JobBackend.Volcano,
            name=run_config.experiment.name,
            namespace=run_config.experiment.namespace,
            state=JobState.Pending,
            age=datetime.now(),
            gpu=run_config.resources.gpu * run_config.resources.nodes,
            nodes=run_config.resources.nodes,
        )
        return job, JobOperationStatus.Success

    def _completion_list_running_jobs(self, **kwargs):
        print("Using completion list for running jobs")
        jobs_stat = self.crd_client.list_cluster_custom_object(
            group="batch.volcano.sh", version="v1alpha1", plural="jobs"
        )
        jobs = jobs_stat["items"]
        running_jobs = []
        for job in jobs:
            if job["status"]["state"]["phase"] == "Running":
                running_jobs.append(job["metadata"]["name"])
        return running_jobs

    @staticmethod
    def _extract_gpu_count(k8s_job) -> int:
        gpu_count = 0

        for task in k8s_job["spec"]["tasks"]:
            for container in task["template"]["spec"]["containers"]:
                if "nvidia.com/gpu" in container["resources"]["limits"]:
                    gpu_count += int(container["resources"]["limits"]["nvidia.com/gpu"])
        return gpu_count

    def list_jobs(self, namespace: str = "All"):
        # TODO [ls] speedup for selected namespace(filter on server side)
        jobs_stat = self.crd_client.list_cluster_custom_object(
            group="batch.volcano.sh", version="v1alpha1", plural="jobs"
        )
        k8s_jobs = jobs_stat["items"]

        extracted_jobs = []
        for k8s_job in k8s_jobs:
            if namespace != "All" and k8s_job["metadata"]["namespace"] != namespace:
                continue

            job = Job(
                type=JobType.torchrun,
                backend=JobBackend.Volcano,
                name=k8s_job["metadata"]["name"],
                namespace=k8s_job["metadata"]["namespace"],
                state=k8s_job["status"]["state"]["phase"],
                age=datetime.strptime(k8s_job["status"]["state"]["lastTransitionTime"], "%Y-%m-%dT%H:%M:%SZ"),
                gpu=self._extract_gpu_count(k8s_job),
            )
            extracted_jobs.append(job)

        return extracted_jobs

    def delete_job(self, job_name: str, namespace: str) -> JobOperationStatus:
        # TODO add cli response formatting for deletion confirmation
        self.crd_client.delete_namespaced_custom_object(
            group="batch.volcano.sh", version="v1alpha1", namespace=namespace, plural="jobs", name=job_name
        )
        events = self.core_client.list_namespaced_event(namespace=namespace)
        for event in events.items:
            if event.metadata.name.startswith(f"{job_name}"):
                self.core_client.delete_namespaced_event(name=event.metadata.name, namespace=namespace)

        return JobOperationStatus.Success

    def get_job_main_pod(self, job_name: str, namespace: str):
        pods = self.core_client.list_namespaced_pod(
            namespace=namespace, label_selector=f"volcano.sh/job-name={job_name}"
        )
        # TODO add logic for multi pod master-worker selection for logging extraction
        if len(pods.items) == 0:
            raise Exception(f"No pods found for job {job_name} in namespace {namespace}")
        pod = pods.items[0]
        pod_name = pod.metadata.name
        return pod_name, pod

    def get_job_events(self, pod_name: str, namespace: str):
        events = self.core_client.list_namespaced_event(
            namespace=namespace, field_selector=f"involvedObject.name={pod_name}"
        )
        return events

    def get_logs(self, job_name: str, namespace: str, tail: Optional[int] = None, follow: bool = False):
        pod_name, pod = self.get_job_main_pod(job_name, namespace)
        containers = pod.spec.containers
        if len(containers) == 0:
            return f"No containers found for pod {pod_name} in namespace {namespace}"
        # TODO add logic for multi container selection for logging extraction
        container = containers[0]
        container_name = container.name
        if tail:
            return self.core_client.read_namespaced_pod_log(
                name=pod_name, namespace=namespace, container=container_name, tail_lines=tail
            )
        if follow:
            w = watch.Watch()
            return w.stream(
                self.core_client.read_namespaced_pod_log, name=pod_name, namespace=namespace, container=container_name
            )

        api_response = self.core_client.read_namespaced_pod_log(name=pod_name, namespace=namespace)
        return api_response

    def describe_job(self, job_name: str, namespace: str):
        pod_name, pod = self.get_job_main_pod(job_name, namespace)
        raw_events = self.get_job_events(pod_name, namespace)

        events = []
        for event in raw_events.items:
            events.append(
                {
                    "Last Seen": event.last_timestamp,
                    "From": event.source.component,
                    "Type": event.type,
                    "Reason": event.reason,
                    "Message": event.message,
                }
            )
        events.sort(key=lambda x: x["Last Seen"], reverse=True)
        for event in events:
            event["Last Seen"] = humanize.naturaldelta(datetime.now() - event["Last Seen"].replace(tzinfo=None))

        # TODO add handling events longer than 10
        events = events[:10]

        events = tabulate(events, headers="keys", tablefmt="grid", maxcolwidths=80)

        return events
