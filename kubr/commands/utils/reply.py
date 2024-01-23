from typing import List

import cowsay
from rich import print
from rich.table import Table

from kubr.config.job import Job, JobState

mascot = r"""
\
 \
  ╱|、
(˚ˎ 。7
 |、˜〵
じしˍ,)ノ
"""


def mascot_message(msg: str):
    return cowsay.draw(msg, mascot, to_console=False)


def generate_jobs_table(jobs: List[Job], state: str):
    total_gpus = sum([job.gpu for job in jobs])
    show_footer = state in [str(JobState.Running), str(JobState.Pending)]

    table = Table(title=str(state), width=100, show_footer=show_footer, footer_style="bold")
    table.add_column("Name", style="cyan", no_wrap=True, width=60)
    table.add_column("Namespace", style="magenta", justify="center")
    table.add_column("Age", "Total:", style="yellow", justify="center")
    table.add_column("GPU", f"{total_gpus}", style="red", justify="center")
    for job in jobs:
        table.add_row(job.name, job.namespace, job.age, str(job.gpu))
    return table


def confirmation_prompt(msg: str):
    print(mascot_message(msg + "\n |y/N| Default=No"))
    response = input().lower()
    return response in ["y", "yes"]
