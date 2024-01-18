from kubr.backends.volcano import VolcanoBackend
from typing import List

from kubr.commands.base import BaseCommand
from kubr.config.job import Job, JobState
from collections import defaultdict
import humanize
from tabulate import tabulate
from typing import Optional
from kubr.backends.utils import join_tables_horizontally
from datetime import datetime
from kubr.commands.utils.drawing import mascot_message, generate_jobs_table
from rich import print
from rich.columns import Columns
from rich.table import Table


def visualize_jobs(jobs: List[Job], head: Optional[int] = 10, show_all: bool = False):
    extracted_jobs = defaultdict(list)
    for job in jobs:
        if job.state in [JobState.Pending, JobState.Running, JobState.Completed, JobState.Failed]:
            extracted_jobs[str(job.state)].append(job)
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

        if len(extracted_jobs[state]):
            extracted_jobs[state] = generate_jobs_table(jobs=extracted_jobs[state], state=state)
        else:
            extracted_jobs[state] = mascot_message(f"No {state} jobs found!")

    result = [extracted_jobs['Running'], extracted_jobs['Pending'], extracted_jobs['Completed'], extracted_jobs['Failed']]

    if show_all:
        result.append(extracted_jobs['extra'])

    return Columns(result, equal=True,)


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
