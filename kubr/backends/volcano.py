from typing import Literal

from kubr.backends.base import BaseBackend
from kubernetes import client, config
from tabulate import tabulate


class VolcanoBackend(BaseBackend):
    def __init__(self):
        self.kubernetes_config = config.load_config()
        self.crd_client = client.CustomObjectsApi()

    def list_jobs(self, namespace: Literal['All'] = 'All', show_all: bool = False, head: int = None):
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
