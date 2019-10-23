import uuid
import logging

from abc import abstractmethod
from celery import chord, signature

from utils.celery_client import celery_app
from utils import job_db


class BaseJob:
    """Wraps multiple celery task chains as a celery chord and handles ID generation."""

    @abstractmethod
    def __init__(self, params, user_name):
        raise NotImplementedError("__init__ method not implemented")

    @abstractmethod
    def run(self):
        """
        Trigger asynchronous execution of the job chord.

        :return AsyncResult: Celery result
        """
        raise NotImplementedError("run method not implemented")

    @abstractmethod
    def _add_to_job_db(self, params, user_name):
        raise NotImplementedError("_add_to_job_db method not implemented")

    def _link(self, name, **params):
        return celery_app.signature(name, kwargs=params)

    def _generate_id(self):
        return str(uuid.uuid1())


class BatchJob(BaseJob):

    @abstractmethod
    def _create_chains(self, params, user_name):
        raise NotImplementedError("_create_chains method not implemented")

    def __init__(self, params, user_name):
        """
        Create a job chord and triggers ID generation.

        :param List[chain] chains: A list of celery task chains
        """

        self.logger = logging.getLogger(__name__)
        self.id = self._generate_id()

        chains = self._create_chains(params, user_name)

        # Once all job chains have finished within this chord, we have to trigger a
        # callback worker in order to update the database entry for the chord job itself.
        self.chord = chord(chains, signature(
            'finish_chord', kwargs={'job_id': self.id, 'work_path': self.id}))

        self.chain_ids = self._add_to_job_db(params, user_name)

        self.logger.info(f"created job chord with id: {self.id}: ")
        for (index, chain_id) in enumerate(self.chain_ids, 1):
            self.logger.info(
                f'  chain #{index}, job id: {chain_id}:')

    def run(self):
        job_db.update_job_state(self.id, 'started')
        for chain_id in self.chain_ids:
            job_db.update_job_state(chain_id, 'started')

        return self.chord.apply_async(task_id=self.id)


class IngestBooksJob(BatchJob):

    def _create_chains(self, params, user_name):
        chains = []

        for book_object in params['objects']:
            task_params = dict(**book_object, **{'user': user_name},
                               initial_representation='tif')

            current_chain = self._link('create_object', **task_params)

            current_chain |= self._link('list_files',
                                        representation='tif',
                                        target='jpg',
                                        task='convert.tif_to_jpg')

            current_chain |= self._link('list_files',
                                        representation='jpg',
                                        target='jpg_thumbnails',
                                        task='convert.tif_to_jpg',
                                        max_width=50,
                                        max_height=50)

            current_chain |= self._link('list_files',
                                        representation='tif',
                                        target='ptif',
                                        task='convert.tif_to_ptif')

            current_chain |= self._link('list_files',
                                        representation='tif',
                                        target='pdf',
                                        task='convert.tif_to_pdf')
            current_chain |= self._link('convert.merge_converted_pdf')

            if params['options']['do_ocr']:
                current_chain |= self._link('list_files',
                                            representation='tif',
                                            target='txt',
                                            task='convert.tif_to_txt',
                                            ocr_lang=params['options']['ocr_lang'])

            current_chain |= self._link('generate_xml',
                                        template_file='mets_template_no_articles.xml',
                                        target_filename='mets.xml',
                                        schema_file='mets.xsd')

            current_chain |= self._link('publish_to_repository')
            current_chain |= self._link('publish_to_archive')

            current_chain |= self._link('cleanup_workdir')
            current_chain |= self._link('finish_chain')

            chains.append(current_chain)

        return chains

    def _add_to_job_db(self, params, user_name):
        chain_ids = []

        for current_chain in self.chord.tasks:
            current_chain_links = []
            current_chain_id = self._generate_id()
            current_work_path = current_chain_id
            current_chain.kwargs['work_path'] = current_work_path

            for single_task in current_chain.tasks:
                job_id = self._generate_id()

                single_task.kwargs['job_id'] = job_id
                single_task.options['task_id'] = job_id
                single_task.kwargs['work_path'] = current_work_path
                single_task.kwargs['parent_job_id'] = current_chain_id

                job_db.add_job(job_id=job_id,
                               user=user_name,
                               job_type=single_task.name,
                               parent_job_id=current_chain_id,
                               child_job_ids=[],
                               parameters=single_task.kwargs)

                current_chain_links += [job_id]

            job_db.add_job(job_id=current_chain_id,
                           user=user_name,
                           job_type='chain',
                           parent_job_id=self.id,
                           child_job_ids=current_chain_links,
                           parameters={'work_path': current_chain.kwargs['work_path']})
            chain_ids += [current_chain_id]

        job_db.add_job(job_id=self.id,
                       user=user_name,
                       job_type='ingest_books',
                       parent_job_id=None,
                       child_job_ids=chain_ids,
                       parameters=params)

        return chain_ids


class IngestJournalsJob(BatchJob):
    def _create_chains(self, params, user_name):
        chains = []

        for issue_object in params['objects']:
            task_params = dict(**issue_object, **{'user': user_name},
                               initial_representation='tif')

            current_chain = self._link('create_object', **task_params)

            current_chain |= self._link('list_files',
                                        representation='tif',
                                        target='pdf',
                                        task='convert.tif_to_pdf')

            current_chain |= self._link('convert.merge_converted_pdf')

            current_chain |= self._link('list_files',
                                        representation='tif',
                                        target='jpg',
                                        task='convert.tif_to_jpg')

            current_chain |= self._link('list_files',
                                        representation='tif',
                                        target='jpg_thumbnails',
                                        task='convert.scale_image',
                                        max_width=50,
                                        max_height=50)

            current_chain |= self._link('generate_xml',
                                        template_file='ojs3_template_issue.xml',
                                        target_filename='ojs_import.xml',
                                        ojs_metadata=params['options']['ojs_metadata'])

            current_chain |= self._link('generate_xml',
                                        template_file='mets_template_no_articles.xml',
                                        target_filename='mets.xml',
                                        schema_file='mets.xsd')

            if params['options']['ojs_metadata']['auto_publish_issue']:
                current_chain |= self._link('publish_to_ojs',
                                            ojs_metadata=params['options']['ojs_metadata'],
                                            ojs_journal_code=issue_object['metadata']['ojs_journal_code'])
            current_chain |= self._link('publish_to_repository')
            current_chain |= self._link('publish_to_archive')
            current_chain |= self._link('cleanup_workdir')
            current_chain |= self._link('finish_chain')
            chains.append(current_chain)

        return chains

    def _add_to_job_db(self, params, user_name):
        chain_ids = []

        for current_chain in self.chord.tasks:
            current_chain_links = []
            current_chain_id = self._generate_id()
            current_work_path = current_chain_id
            current_chain.kwargs['work_path'] = current_work_path

            for single_task in current_chain.tasks:
                job_id = self._generate_id()

                single_task.kwargs['job_id'] = job_id
                single_task.options['task_id'] = job_id
                single_task.kwargs['work_path'] = current_work_path
                single_task.kwargs['parent_job_id'] = current_chain_id

                job_db.add_job(job_id=job_id,
                               user=user_name,
                               job_type=single_task.name,
                               parent_job_id=current_chain_id,
                               child_job_ids=[],
                               parameters=single_task.kwargs)

                current_chain_links += [job_id]

            job_db.add_job(job_id=current_chain_id,
                           user=user_name,
                           job_type='chain',
                           parent_job_id=self.id,
                           child_job_ids=current_chain_links,
                           parameters={'work_path': current_chain.kwargs['work_path']})
            chain_ids += [current_chain_id]

        job_db.add_job(job_id=self.id,
                       user=user_name,
                       job_type='ingest_journals',
                       parent_job_id=None,
                       child_job_ids=chain_ids,
                       parameters=params)

        return chain_ids