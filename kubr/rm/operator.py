from kubr.backends.volcano import VolcanoBackend


class RMOperator:
    def __init__(self, backend=None):
        self.backend = backend or VolcanoBackend()

    def __call__(self, job_name: str, namespace: str = 'default'):
        return self.backend.delete_job(job_name=job_name, namespace=namespace)
