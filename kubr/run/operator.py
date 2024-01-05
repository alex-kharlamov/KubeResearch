from kubr.backends.volcano import VolcanoBackend


class RUNOperator:
    def __init__(self, backend=None):
        self.backend = backend or VolcanoBackend()

    def __call__(self, job_name: str, namespace: str, image: str, entrypoint: str):
        return self.backend.run_job(job_name=job_name, namespace=namespace, image=image, entrypoint=entrypoint)
