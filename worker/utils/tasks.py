import glob
import os
import shutil
import time

from celery import signature, group

from utils.celery_client import celery

repository_dir = os.environ['REPOSITORY_DIR']
working_dir = os.environ['WORKING_DIR']


@celery.task(bind=True, name="match")
def match(self, object_id, job_id, prev_task, run, pattern='*.tif'):
    source = os.path.join(working_dir, job_id, object_id, prev_task)
    subtasks = []
    for file in glob.iglob(os.path.join(source, pattern)):
        subtasks.append(signature(
            run, [object_id, job_id, prev_task, self.name, file]
        ))
    raise self.replace(group(subtasks))


@celery.task(name="rename")
def rename(object_id, job_id, prev_task, parent_task, file):
    source = os.path.join(working_dir, job_id, object_id, prev_task)
    target = os.path.join(working_dir, job_id, object_id, parent_task)
    if not os.path.exists(target):
        try:
            os.makedirs(target)
        except OSError:
            print("could not create dir, eating exception")
    time.sleep(10)
    new_file = file.replace('.tif', '.jpg').replace(source, target)
    shutil.copyfile(file, new_file)


@celery.task(name="cleanup_workdir")
def cleanup_workdir(object_id, job_id, prev_task):
    folder = os.path.join(working_dir, job_id)
    shutil.rmtree(folder)