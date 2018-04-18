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
    print("created job: %s" % job)
    task = job.run()
    print("created job with id: %s" % task.id)
    return jsonify({'status': 'Accepted', 'job_id': task.id}), \
           202, {'Location': url_for('job.job_status', job_id=task.id)}


@job_controller.route('/<job_id>', methods=['GET'])
def job_status(job_id):
    task = celery.AsyncResult(job_id)
    response = {
        'status': task.state
    }
    if hasattr(task.info, 'result'):
        response['result'] = task.info['result']
    return jsonify(response)