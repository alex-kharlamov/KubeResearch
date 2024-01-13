from dataclasses import dataclass, field
from typing import Dict, List, Literal
from typing import Optional
from kubr.config.runner import ContainerConfig, ResourceConfig


from kubernetes.client.models import (  # noqa: F811 redefinition of unused
    V1Container,
    V1ContainerPort,
    V1EmptyDirVolumeSource,
    V1EnvVar,
    V1ObjectMeta,
    V1Pod,
    V1PodSpec,
    V1ResourceRequirements,
    V1SecurityContext,
    V1Volume,
    V1VolumeMount,
)

RESERVED_MILLICPU = 100
RESERVED_MEMMB = 1024

ANNOTATION_ISTIO_SIDECAR = "sidecar.istio.io/inject"


def create_pod_definition(pod_name: str, resource_config: ResourceConfig, container_config: ContainerConfig,
                          service_account: Optional[str]) -> "V1Pod":
    limits = {}
    requests = {}

    if resource_config.cpu > 0:
        mcpu = int(resource_config.cpu * 1000)
        limits["cpu"] = f"{mcpu}m"
        request_mcpu = max(mcpu - RESERVED_MILLICPU, 0)
        requests["cpu"] = f"{request_mcpu}m"
    if resource_config.memMB > 0:
        limits["memory"] = f"{int(resource_config.memMB)}M"
        request_memMB = max(int(resource_config.memMB) - RESERVED_MEMMB, 0)
        requests["memory"] = f"{request_memMB}M"
    if resource_config.gpu > 0:
        requests["nvidia.com/gpu"] = limits["nvidia.com/gpu"] = str(resource_config.gpu)
    if resource_config.ib > 0:
        requests[resource_config.ib_device] = limits[resource_config.ib_device] = str(resource_config.ib)

    for device_name, device_limit in resource_config.devices.items():
        limits[device_name] = str(device_limit)

    resources = V1ResourceRequirements(
        limits=limits,
        requests=requests,
    )

    node_selector: Dict[str, str] = {}
    # if LABEL_INSTANCE_TYPE in resource.capabilities:
    #     node_selector[LABEL_INSTANCE_TYPE] = resource.capabilities[LABEL_INSTANCE_TYPE]

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
        command=[container_config.entrypoint] + container_config.args,
        image=container_config.image,
        name=pod_name,
        env=[
            V1EnvVar(
                name=name,
                value=value,
            )
            for name, value in container_config.env.items()
        ],
        resources=resources,
        ports=[
            V1ContainerPort(
                name=name,
                container_port=port,
            )
            for name, port in container_config.port_map.items()
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
