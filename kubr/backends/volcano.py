import time
from collections import defaultdict
from dataclasses import field, dataclass
from enum import Enum
from typing import Literal, Dict, Any, Mapping, Iterable, List, Optional
from datetime import datetime

from kubr.backends.base import BaseBackend
from kubernetes import client, config, watch
from kubernetes.client.models import (  # noqa: F811 redefinition of unused
    V1Container,
    V1ContainerPort,
    V1EmptyDirVolumeSource,
    V1EnvVar,
    V1HostPathVolumeSource,
    V1ObjectMeta,
    V1PersistentVolumeClaimVolumeSource,
    V1Pod,
    V1PodSpec,
    V1ResourceRequirements,
    V1SecurityContext,
    V1Volume,
    V1VolumeMount,
)

from kubr.backends.k8s_runner import (
    create_pod_definition,
)
from kubr.config.runner import RunnerConfig
from kubr.backends.utils import join_tables_horizontally
from kubr.config.job import Job


class RetryPolicy(str, Enum):
    """
    Defines the retry policy for the ``Roles`` in the ``AppDef``.
    The policy defines the behavior when the role replica encounters a failure:

    1. unsuccessful (non zero) exit code
    2. hardware/host crashes
    3. preemption
    4. eviction

    .. note:: Not all retry policies are supported by all schedulers.
              However all schedulers must support ``RetryPolicy.APPLICATION``.
              Please refer to the scheduler's documentation for more information
              on the retry policies they support and behavior caveats (if any).

    1. REPLICA: Replaces the replica instance. Surviving replicas are untouched.
                Use with ``dist.ddp`` component to have torchelastic coordinate
                restarts and membership changes. Otherwise, it is up to the
                application to deal with failed replica departures and
                replacement replica admittance.
    2. APPLICATION: Restarts the entire application.

    """

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
    def __init__(self):
        self.kubernetes_config = config.load_config()
        self.crd_client = client.CustomObjectsApi()
        self.core_client = client.CoreV1Api()

    def run_job(self, run_config: RunnerConfig):
        tasks = []

        for replica_id in range(run_config.resource_config.num_replicas):
            pod = create_pod_definition(
                pod_name=run_config.exp_config.exp_name,
                resource_config=run_config.resource_config,
                container_config=run_config.container_config,
                data_config=run_config.data_config,
                service_account=None,
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
                "name": run_config.exp_config.task_name,
                "template": pod,
            }
            if run_config.exp_config.task_max_retries > 0:
                task["maxRetry"] = run_config.exp_config.task_max_retries
                task["policies"] = RETRY_POLICIES[RetryPolicy.APPLICATION]

            if run_config.exp_config.min_replicas is not None:
                # first min_replicas tasks are required, afterward optional
                task["minAvailable"] = 1 if replica_id < run_config.exp_config.min_replicas else 0

            tasks.append(task)

        job_spec = {
            "schedulerName": "volcano",
            "queue": run_config.exp_config.queue,
            "tasks": tasks,
            "maxRetry": run_config.exp_config.job_retries,
            "plugins": {
                # https://github.com/volcano-sh/volcano/issues/533
                "svc": ["--publish-not-ready-addresses"],
                "env": [],
            },
        }
        if run_config.exp_config.priority_class is not None:
            job_spec["priorityClassName"] = run_config.exp_config.priority_class

        resource: Dict[str, object] = {
            "apiVersion": "batch.volcano.sh/v1alpha1",
            "kind": "Job",
            "metadata": {"name": f"{run_config.exp_config.exp_name}"},
            "spec": job_spec,
        }

        resp = self.crd_client.create_namespaced_custom_object(
            group="batch.volcano.sh",
            version="v1alpha1",
            namespace=run_config.exp_config.namespace,
            plural="jobs",
            body=resource,
        )
        print(resp)

    def _completion_list_running_jobs(self, **kwargs):
        print("Using completion list for running jobs")
        jobs_stat = self.crd_client.list_cluster_custom_object(group='batch.volcano.sh',
                                                               version='v1alpha1',
                                                               plural='jobs')
        jobs = jobs_stat['items']
        running_jobs = []
        for job in jobs:
            if job['status']['state']['phase'] == 'Running':
                running_jobs.append(job['metadata']['name'])
        return running_jobs

    def list_jobs(self, namespace: str = 'All'):
        # TODO [ls] show used resources
        # TODO [ls] speedup for selected namespace(filter on server side)
        # TODO [ls] show events for pending jobs
        jobs_stat = self.crd_client.list_cluster_custom_object(group='batch.volcano.sh',
                                                               version='v1alpha1',
                                                               plural='jobs')
        k8s_jobs = jobs_stat['items']

        extracted_jobs = []
        for k8s_job in k8s_jobs:
            if namespace != 'All' and k8s_job['metadata']['namespace'] != namespace:
                continue
            job = Job(type='Volcano',
                      name=k8s_job['metadata']['name'],
                      namespace=k8s_job['metadata']['namespace'],
                      state=k8s_job['status']['state']['phase'],
                      age=datetime.strptime(k8s_job['status']['state']['lastTransitionTime'],
                                            '%Y-%m-%dT%H:%M:%SZ')
                      )
            extracted_jobs.append(job)

        return extracted_jobs

    def delete_job(self, job_name: str, namespace: str):
        # TODO add cli response formatting for deletion confirmation
        resp = self.crd_client.delete_namespaced_custom_object(group='batch.volcano.sh',
                                                               version='v1alpha1',
                                                               namespace=namespace,
                                                               plural='jobs',
                                                               name=job_name)
        events = self.core_client.list_namespaced_event(namespace=namespace,
                                                        field_selector=f"involvedObject.name={job_name}")
        for event in events.items:
            self.core_client.delete_namespaced_event(name=event.metadata.name, namespace=namespace)

        print(resp)

    def get_job_main_pod(self, job_name: str, namespace: str):
        pods = self.core_client.list_namespaced_pod(namespace=namespace,
                                                    label_selector=f"volcano.sh/job-name={job_name}")
        # TODO add logic for multi pod master-worker selection for logging extraction
        if len(pods.items) == 0:
            raise Exception(f'No pods found for job {job_name} in namespace {namespace}')
        pod = pods.items[0]
        pod_name = pod.metadata.name
        return pod_name, pod

    def get_job_events(self, pod_name: str, namespace: str):
        events = self.core_client.list_namespaced_event(namespace=namespace,
                                                        field_selector=f"involvedObject.name={pod_name}")
        return events

    def get_logs(self, job_name: str, namespace: str, tail: Optional[int] = None):
        pod_name, pod = self.get_job_main_pod(job_name, namespace)
        containers = pod.spec.containers
        if len(containers) == 0:
            return f'No containers found for pod {pod_name} in namespace {namespace}'
        # TODO add logic for multi container selection for logging extraction
        container = containers[0]
        container_name = container.name
        if tail:
            api_response = self.core_client.read_namespaced_pod_log(name=pod_name, namespace=namespace,
                                                                    container=container_name, tail_lines=tail)
            return api_response
        else:
            w = watch.Watch()
            # TODO fix log streaming utf-8 decoding
            for line in w.stream(self.core_client.read_namespaced_pod_log, name=pod_name,
                                 namespace=namespace, container=container_name):
                print(line)

        api_response = self.core_client.read_namespaced_pod_log(name=pod_name, namespace=namespace)
        return api_response

    def describe_job(self, job_name: str, namespace: str):

        pod_name, pod = self.get_job_main_pod(job_name, namespace)
        raw_events = self.get_job_events(pod_name, namespace)

        events = []
        for event in raw_events.items:
            events.append({
                'Last Seen': event.last_timestamp,
                'From': event.source.component,
                'Type': event.type,
                'Reason': event.reason,
                'Message': event.message
            })
        events.sort(key=lambda x: x['Last Seen'], reverse=True)
        for event in events:
            event['Last Seen'] = humanize.naturaldelta(datetime.now() - event['Last Seen'].replace(tzinfo=None))

        # TODO add handling events longer than 10
        events = events[:10]

        events = tabulate(events, headers='keys', tablefmt='grid', maxcolwidths=80)

        return events
