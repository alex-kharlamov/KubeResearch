from dataclasses import field
from typing import Dict, List, Literal, Union
from typing import Optional

from pydantic import BaseModel


class ContainerConfig(BaseModel):
    image: str
    entrypoint: str
    env: Dict[str, str] = field(default_factory=dict)
    port_map: Dict[str, int] = field(default_factory=dict)
    args: List[str] = field(default_factory=list)
    python_path: str = ""


class GitConfig(BaseModel):
    url: str
    branch: str
    commit: str
    secret: str


class VolumeMount(BaseModel):
    name: str
    type: Literal["pvc", "hostPath"]
    mount_path: str


class CodePersistenceConfig(BaseModel):
    git: Optional[GitConfig] = None
    pvc: Optional[str] = None
    volume: Optional[VolumeMount] = None


class DataConfig(BaseModel):
    pvcs: Optional[List[str]] = None
    volumes: Optional[List[VolumeMount]] = None


class ResourceConfig(BaseModel):
    num_replicas: int = 1
    cpu: int = 0
    memMB: int = 0
    gpu: int = 0
    devices: Dict[str, float] = field(default_factory=dict)
    capabilities: Dict[str, str] = field(default_factory=dict)
    ib: Union[int, Literal['auto']] = 0
    ib_device: str = "nvidia.com/hostdev"


class ExperimentConfig(BaseModel):
    exp_name: str
    namespace: str

    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)

    queue: Optional[str] = "default"
    priority_class: Optional[str] = None

    job_retries: int = 0
    min_replicas: int = 1
    task_name: str = "main-task"
    task_max_retries: int = 10


class RunnerConfig(BaseModel):
    container_config: ContainerConfig
    resource_config: ResourceConfig
    job_type: Literal["Volcano"] = "Volcano"
    code_persistence_config: Optional[CodePersistenceConfig] = None
    data_config: Optional[DataConfig] = None
    exp_config: Optional[ExperimentConfig] = None
