from typing import Dict, Optional

from kubernetes.client import V1EnvVarSource, V1HostPathVolumeSource, V1SecretKeySelector
from kubernetes.client.models import (  # noqa: F811 redefinition of unused
    V1Container,
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

from kubr.config.runner import ContainerConfig, DataConfig, ResourceConfig

RESERVED_MILLICPU = 100
RESERVED_MEMMB = 1024

ANNOTATION_ISTIO_SIDECAR = "sidecar.istio.io/inject"


def create_pod_definition(
    pod_name: str,
    resource_config: ResourceConfig,
    container_config: ContainerConfig,
    service_account: Optional[str],
    data_config: DataConfig,
    init_container_config: ContainerConfig,
) -> "V1Pod":
    limits = {}
    requests = {}

    if resource_config.cpu > 0:
        mcpu = int(resource_config.cpu * 1000)
        limits["cpu"] = f"{mcpu}m"
        request_mcpu = max(mcpu - RESERVED_MILLICPU, 0)
        requests["cpu"] = f"{request_mcpu}m"
    if resource_config.memory > 0:
        limits["memory"] = f"{int(resource_config.memory * 2 ** 10)}M"
        request_memMB = max(int(resource_config.memory) - RESERVED_MEMMB, 0)
        requests["memory"] = f"{request_memMB}M"
    if resource_config.gpu > 0:
        requests["nvidia.com/gpu"] = limits["nvidia.com/gpu"] = str(resource_config.gpu)
    if resource_config.ib > 0:
        requests[resource_config.ib_device] = limits[resource_config.ib_device] = str(resource_config.ib)

    # for device_name, device_limit in resource_config.devices.items():
    #     limits[device_name] = str(device_limit)

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
    if data_config is not None:
        for volume in data_config.volumes:
            if volume.type == "hostPath":
                host_path, mount_path = volume.mount_path.split(":")
                volumes.append(
                    V1Volume(
                        name=volume.name,
                        host_path=V1HostPathVolumeSource(
                            path=host_path,
                        ),
                    )
                )
                volume_mounts.append(
                    V1VolumeMount(
                        name=volume.name,
                        mount_path=mount_path,
                    )
                )
            else:
                raise ValueError(f"Unknown volume type {volume.type}")
    security_context = V1SecurityContext()

    container_envs = []
    for env in container_config.env:
        container_envs.append(
            V1EnvVar(
                name=env.name,
                value=env.value,
            )
        )
    for secret in container_config.secrets:
        container_envs.append(
            V1EnvVar(
                name=secret.env,
                value_from=V1EnvVarSource(
                    secret_key_ref=V1SecretKeySelector(
                        name=secret.secret_name,
                        key=secret.secret_key,
                    ),
                ),
            )
        )

    # port_maps = [
    #     V1ContainerPort(
    #         name=name,
    #         container_port=port,
    #     )
    #     for name, port in container_config.port_map.items()
    # ]
    port_maps = []
    init_containers = []
    if init_container_config is not None:
        # TODO [run] support env handling for init_container
        init_containers.append(
            V1Container(
                command=init_container_config.entrypoint.split()
                if init_container_config.entrypoint is not None
                else None,
                image=init_container_config.image,
                image_pull_policy="Always",
                name=f"{pod_name}-init",
            )
        )

    container = V1Container(
        command=container_config.entrypoint.split() if container_config.entrypoint is not None else None,
        image=container_config.image,
        image_pull_policy="Always",
        name=pod_name,
        env=container_envs,
        resources=resources,
        ports=port_maps,
        volume_mounts=volume_mounts,
        security_context=security_context,
    )

    return V1Pod(
        spec=V1PodSpec(
            init_containers=init_containers,
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
