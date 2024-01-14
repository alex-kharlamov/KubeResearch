from kubr.backends.volcano import VolcanoBackend
from typing import List

from kubr.commands.base import BaseCommand
from kubr.config.job import Job
from collections import defaultdict
import humanize
from tabulate import tabulate
from typing import Optional
from kubr.backends.utils import join_tables_horizontally
from datetime import datetime


def visualize_jobs(jobs: List[Job], head: Optional[int] = 10, show_all: bool = False):
    extracted_jobs = defaultdict(list)
    for job in jobs:
        if job.state in ['Pending', 'Running', 'Failed', 'Completed']:
            extracted_jobs[job.state].append(job)
        else:
            extracted_jobs['extra'].append(job)

    for state in ['Pending', 'Running', 'Completed', 'Failed', 'extra']:
        extracted_jobs[state].sort(key=lambda x: x.age, reverse=True)
        for job in extracted_jobs[state]:
            job.age = humanize.naturaldelta(datetime.utcnow() - job.age)
        if head:
            extracted_jobs[state] = extracted_jobs[state][:head]

        # TODO [ls] add pretty formatting that will show only first 10 jobs in completed and failed states are shown
        if not show_all and state in ['Completed', 'Failed']:
            extracted_jobs[state] = extracted_jobs[state][:5]

        dict_jobs = [job.dict() for job in extracted_jobs[state]]
        extracted_jobs[state] = tabulate(dict_jobs, headers='keys', tablefmt='grid')

    # TODO pretty handling of empty list in running jobs
    result = join_tables_horizontally(extracted_jobs['Running'], extracted_jobs['Pending'])
    result += '\n\n'
    result += join_tables_horizontally(extracted_jobs['Completed'], extracted_jobs['Failed'])

    if show_all:
        result += '\n\n'
        # TODO pretty handling of empty list in all jobs
        result += extracted_jobs['extra']

    return result


class LsCommand(BaseCommand):
    @staticmethod
    def add_parser(subparsers):
        ls_parser = subparsers.add_parser('ls', help='List all jobs')
        ls_parser.add_argument('-n', '--namespace', help='Namespace to list jobs from', default='All')
        ls_parser.add_argument('-a', '--all', help='Show all jobs', action='store_true', default=False)
        ls_parser.add_argument('-t', '--top', help='Show only first T jobs', default=None, type=int)
        return ls_parser

    def __call__(self, namespace: str = 'All', head: Optional[int] = None, show_all: bool = False):
        jobs = self.backend.list_jobs(namespace=namespace)
        print(visualize_jobs(jobs=jobs, head=head, show_all=show_all))
