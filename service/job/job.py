import uuid
import logging

from celery import chord, signature

from utils import job_db


class Job:
    """Wraps multiple celery task chains as a celery chord and handles ID generation."""

    def __init__(self, chains):
        """
        Create a job chord and triggers ID generation.

        :param List[chain] chains: A list of celery task chains
        """
        logger = logging.getLogger(__name__)

        self.id = str(uuid.uuid1())

        # Once all job chains have finished within this chord, we have to trigger a
        # callback worker in order to update the database entry for the chord job itself.
        self.chord = chord(chains, signature(
            'finish_chord', kwargs={'job_id': self.id, 'work_path': self.id}))

        self.chains = []

        for current_chain in self.chord.tasks:
            current_chain_links = []
            current_chain_work_path = str(uuid.uuid1())
            current_chain.kwargs['work_path'] = current_chain_work_path

            for single_task in current_chain.tasks:
                task_id = str(uuid.uuid1())

                single_task.kwargs['job_id'] = task_id
                single_task.kwargs['work_path'] = current_chain_work_path
                single_task.options['task_id'] = task_id

                current_chain_links += [{'name': single_task.name,
                                         'task_id': task_id}]

            self.chains += [{'work_path': current_chain_work_path,
                             'chain': current_chain_links}]

        logger.info(f"created job chord with id: {self.id}: ")
        for (index, chain) in enumerate(self.chains, 1):
            logger.info(
                f'  chain #{index}, work path: {chain["work_path"]}:')
            for sub_task in chain['sub_tasks']:
                logger.info(f'    {sub_task["name"]}: {sub_task["task_id"]}')

    def run(self):
        """
        Trigger asynchronous execution of the job chord.

        :return AsyncResult: Celery result
        """

        return self.chord.apply_async(task_id=self.id)
