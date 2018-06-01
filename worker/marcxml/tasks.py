import os
import json
import shutil

from worker.marcxml.marcxml_generator import generate_marcxml
from utils.celery_client import celery_app


@celery_app.task(name="generate_marcxml")
def task_generate_marcxml(object_id, job_id, prev_task):
    source = os.path.join(os.environ['WORKING_DIR'], job_id, object_id, prev_task)
    target = os.path.join(os.environ['WORKING_DIR'], job_id, object_id, 'generate_marcxml')

    shutil.copytree(source, target)

    json_path = os.path.join(target, 'data_json/data.json')
    with open(json_path) as data_object:
        data = json.load(data_object)

    generate_marcxml(data, target)