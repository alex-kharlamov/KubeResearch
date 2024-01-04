from dataclasses import field, dataclass
from enum import Enum
from typing import Literal, Dict, Any, Mapping, Iterable, List, Optional

from kubr.backends.base import BaseBackend
from kubernetes import client, config
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
from tabulate import tabulate

RESERVED_MILLICPU = 100
RESERVED_MEMMB = 1024


@dataclass
class PodResource:
    cpu: float = 0
    memMB: float = 0
    gpu: float = 0
    devices: Dict[str, float] = field(default_factory=dict)
    capabilities: Dict[str, str] = field(default_factory=dict)


@dataclass
class PodConfig:
    resource: PodResource
    image: str
    entrypoint: str
    args: List[str]
    env: Dict[str, str] = field(default_factory=dict)
    port_map: Dict[str, int] = field(default_factory=dict)


def create_pod_definition(pod_name: str, pod_config: PodConfig, service_account: Optional[str]) -> "V1Pod":
    limits = {}
    requests = {}

    resource = pod_config.resource
    if resource.cpu > 0:
        mcpu = int(resource.cpu * 1000)
        limits["cpu"] = f"{mcpu}m"
        request_mcpu = max(mcpu - RESERVED_MILLICPU, 0)
        requests["cpu"] = f"{request_mcpu}m"
    if resource.memMB > 0:
        limits["memory"] = f"{int(resource.memMB)}M"
        request_memMB = max(int(resource.memMB) - RESERVED_MEMMB, 0)
        requests["memory"] = f"{request_memMB}M"
    if resource.gpu > 0:
        requests["nvidia.com/gpu"] = limits["nvidia.com/gpu"] = str(resource.gpu)

    for device_name, device_limit in resource.devices.items():
        limits[device_name] = str(device_limit)

    resources = V1ResourceRequirements(
        limits=limits,
        requests=requests,
    )

    node_selector: Dict[str, str] = {}
    if LABEL_INSTANCE_TYPE in resource.capabilities:
        node_selector[LABEL_INSTANCE_TYPE] = resource.capabilities[LABEL_INSTANCE_TYPE]

    # To support PyTorch dataloaders we need to set /dev/shm to larger than the
    # 64M default so we mount an unlimited sized tmpfs directory on it.
    SHM_VOL = "dshm"
    volumes = [
        V1Volume(
            name=SHM_VOL,
            empty_dir=V1EmptyDirVolumeSource(
                medium="Memory",
            ),
        ),
    ]
    volume_mounts = [
        V1VolumeMount(name=SHM_VOL, mount_path="/dev/shm"),
    ]
    security_context = V1SecurityContext()

    container = V1Container(
        command=[pod_config.entrypoint] + pod_config.args,
        image=pod_config.image,
        name=pod_name,
        env=[
            V1EnvVar(
                name=name,
                value=value,
            )
            for name, value in pod_config.env.items()
        ],
        resources=resources,
        ports=[
            V1ContainerPort(
                name=name,
                container_port=port,
            )
            for name, port in pod_config.port_map.items()
        ],
        volume_mounts=volume_mounts,
        security_context=security_context,
    )

    return V1Pod(
        spec=V1PodSpec(
            containers=[container],
            restart_policy="Never",
            service_account_name=service_account,
            volumes=volumes,
            node_selector=node_selector,
        ),
        metadata=V1ObjectMeta(
            annotations={
                # Disable the istio sidecar as it prevents the containers from
                # exiting once finished.
                ANNOTATION_ISTIO_SIDECAR: "false",
            },
            labels={},
        ),
    )


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

    def run_job(self, job_name: str, namespace: str, image: str, command: str):
        unique_app_id = job_name
        queue = "default"
        job_retries = 0
        priority_class = None
        task_name = "main_task"
        task_max_retries = 0
        replica_id = 0
        min_replicas = 1

        pod = create_pod_definition(
            pod_name=task_name,
            pod_config=PodConfig(
                resource=PodResource(
                    cpu=1,
                    memMB=1024,
                ),
                image=image,
                entrypoint=command,
                args=[],
            ),
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
            "name": task_name,
            "template": pod,
        }
        if task_max_retries > 0:
            task["maxRetry"] = task_max_retries
            task["policies"] = RETRY_POLICIES[RetryPolicy.APPLICATION]

        if min_replicas is not None:
            # first min_replicas tasks are required, afterward optional
            task["minAvailable"] = 1 if replica_id < min_replicas else 0

        tasks = [task]

        job_spec = {
            "schedulerName": "volcano",
            "queue": queue,
            "tasks": tasks,
            "maxRetry": job_retries,
            "plugins": {
                # https://github.com/volcano-sh/volcano/issues/533
                "svc": ["--publish-not-ready-addresses"],
                "env": [],
            },
        }
        if priority_class is not None:
            job_spec["priorityClassName"] = priority_class

        resource: Dict[str, object] = {
            "apiVersion": "batch.volcano.sh/v1alpha1",
            "kind": "Job",
            "metadata": {"name": f"{unique_app_id}"},
            "spec": job_spec,
        }

        resp = self.crd_client.create_namespaced_custom_object(
            group="batch.volcano.sh",
            version="v1alpha1",
            namespace=namespace,
            plural="jobs",
            body=resource,
        )
        print(resp)

    def list_jobs(self, namespace: str = 'All', show_all: bool = False, head: int = None):
        jobs_stat = self.crd_client.list_cluster_custom_object(group='batch.volcano.sh',
                                                               version='v1alpha1',
                                                               plural='jobs')
        jobs = jobs_stat['items']
        result_running_data = []
        result_all_data = []
        for job in jobs:
            job_state = {'Name': job['metadata']['name'],
                         'Namespace': job['metadata']['namespace'],
                         'State': job['status']['state']['phase'],
                         'State Time': job['status']['state']['lastTransitionTime']
                         }
            if namespace != 'All' and job_state['Namespace'] != namespace:
                continue

            if job_state['State'] == 'Running':
                result_running_data.append(job_state)
            else:
                result_all_data.append(job_state)

        result_running_data.sort(key=lambda x: x['State Time'], reverse=True)
        if head:
            result_running_data = result_running_data[:head]
        # TODO pretty handling of empty list in running jobs
        result = tabulate(result_running_data, headers='keys', tablefmt='grid')
        if show_all:
            result_all_data.sort(key=lambda x: x['State Time'], reverse=True)
            if head:
                result_all_data = result_all_data[:head]
            result += '\n\n'
            # TODO pretty handling of empty list in all jobs
            result += tabulate(result_all_data, headers='keys', tablefmt='grid')

        return result

    def delete_job(self, job_name: str, namespace: str):
        resp = self.crd_client.delete_namespaced_custom_object(group='batch.volcano.sh',
                                                               version='v1alpha1',
                                                               namespace=namespace,
                                                               plural='jobs',
                                                               name=job_name)
        print(resp)
