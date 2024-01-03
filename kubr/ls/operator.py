from kubr.backends.volcano import VolcanoBackend


class LSOperator:
    def __init__(self, backend=None):
        self.backend = backend or VolcanoBackend()

    def create(self, name, image, command=None, args=None, env=None, labels=None):
        return self.backend.create(name, image, command, args, env, labels)

    def delete(self, name):
        return self.backend.delete(name)

    def get(self, name):
        return self.backend.get(name)

    def __call__(self, *args, **kwargs):
        return self.backend.list_jobs(*args, **kwargs)