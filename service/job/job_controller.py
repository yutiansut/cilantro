from flask import Blueprint, url_for, jsonify, request
from utils.celery_client import celery
from service.job.job_config import JobConfig

job_controller = Blueprint('job', __name__)

job_config = JobConfig()
print("job types: %s" % job_config.job_types)


@job_controller.route('/<job_type>/<object_id>', methods=['POST'])
def job_create(job_type, object_id):
    params = request.get_json(force=True, silent=True)
    job = job_config.generate_job(job_type, object_id, params)
    task = job.run()
    print("created job with id: %s" % task.id)

    job_id = task.id
    task_ids = _get_task_ids(task)

    body = jsonify({
        'status': 'Accepted',
        'job_id': job_id,
        'task_ids': task_ids
    })
    headers = {'Location': url_for('job.job_status', job_id=task.id)}
    return body, 202, headers


@job_controller.route('/<job_id>', methods=['GET'])
def job_status(job_id):
    task = celery.AsyncResult(job_id)
    response = {
        'status': task.state
    }
    if hasattr(task.info, 'result'):
        response['result'] = task.info['result']
    return jsonify(response)


def _get_task_ids(task):
    task_ids = []
    while task.parent is not None:
        task_ids.insert(0, task.id)
        task = task.parent
    return task_ids
