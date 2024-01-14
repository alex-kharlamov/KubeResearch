from kubr.backends.volcano import VolcanoBackend
from typing import List
from kubr.config.job import Job


class LSOperator:
    def __init__(self, backend=None):
        self.backend = backend or VolcanoBackend()


    def visualize_jobs(self, jobs: List[Job]):
        for job in jobs:
            if job_state['State'] in ['Pending', 'Running', 'Failed', 'Completed']:
                extracted_jobs[job_state['State']].append(job_state)
            else:
                extracted_jobs['extra'].append(job_state)

        for state in ['Pending', 'Running', 'Completed', 'Failed', 'extra']:
            extracted_jobs[state].sort(key=lambda x: x['Age'], reverse=True)
            for job in extracted_jobs[state]:
                job['Age'] = humanize.naturaldelta(datetime.utcnow() - job['Age'])
            if head:
                extracted_jobs[state] = extracted_jobs[state][:head]

            # TODO [ls] add pretty formatting that will show only first 10 jobs in completed and failed states are shown
            if not show_all and state in ['Completed', 'Failed']:
                extracted_jobs[state] = extracted_jobs[state][:5]

            extracted_jobs[state] = tabulate(extracted_jobs[state], headers='keys', tablefmt='grid')

        # TODO pretty handling of empty list in running jobs
        result = join_tables_horizontally(extracted_jobs['Running'], extracted_jobs['Pending'])
        result += '\n\n'
        result += join_tables_horizontally(extracted_jobs['Completed'], extracted_jobs['Failed'])

        if show_all:
            result += '\n\n'
            # TODO pretty handling of empty list in all jobs
            result += extracted_jobs['extra']

        return result

    def __call__(self, *args, **kwargs):
        return self.backend.list_jobs(*args, **kwargs)