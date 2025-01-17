import jsonschema
import os
import datetime

from flask import Blueprint, url_for, jsonify, request

from service.errors import ApiError
from service.user.user_service import auth
from utils.job_db import JobDb
from utils import json_validation

from service.job.jobs import IngestRecordsJob, IngestJournalsJob

job_controller = Blueprint('job', __name__)


@job_controller.route('/jobs', methods=['GET'])
@auth.login_required
def job_list():
    """
    List jobs of the user.

    List jobs of the user updated less than a week ago and all jobs, which were
    not successful.
    If show_all_jobs is set True it returns all jobs.

    .. :quickref: Job Controller; List jobs of the user

    **Example request**:

    .. sourcecode:: http

        GET /jobs/ HTTP/1.1

    **Example response SUCCESS**:

    .. sourcecode:: http

        HTTP/1.1 200 OK

        [
            {
                "children": [
                    {
                        "job_id": "f602db90-f594-11e9-b848-0242ac130009",
                        "state": "success",
                        "type": "chain"
                    },
                    {
                        "job_id": "f6053df6-f594-11e9-b455-0242ac130009",
                        "state": "success",
                        "type": "chain"
                    }
                ],
                "created": "Wed, 23 Oct 2019 12:59:34 GMT",
                "errors": [],
                "job_id": "f5fe4d76-f594-11e9-8671-0242ac130009",
                "job_type": "ingest_journals",
                "name": "ingest_journals-f5fe4d76-f594-11e9-8671-0242ac130009",
                "parameters": {
                    ...
                },
                "started": "Wed, 23 Oct 2019 12:59:39 GMT",
                "state": "success",
                "updated": "Wed, 23 Oct 2019 12:59:39 GMT",
                "user": "test_user"
            },
            {
                "children": [
                    {
                        "job_id": "f803e5fa-f594-11e9-a9da-0242ac130009",
                        "state": "started",
                        "type": "chain"
                    },
                    {
                        "job_id": "f8119042-f594-11e9-8a4d-0242ac130009",
                        "state": "started",
                        "type": "chain"
                    }
                ],
                "created": "Wed, 23 Oct 2019 12:59:37 GMT",
                "errors": [],
                "job_id": "f7fdf50a-f594-11e9-8f9d-0242ac130009",
                "job_type": "ingest_records",
                "name": "ingest_records-f7fdf50a-f594-11e9-8f9d-0242ac130009",
                "parameters": {
                    ...
                },
                "started": "Wed, 23 Oct 2019 12:59:37 GMT",
                "state": "started",
                "updated": "Wed, 23 Oct 2019 12:59:37 GMT",
                "user": "test_user"
            }
        ]

    :query show_all_jobs: (optional) if 'True', all jobs are listed
    :return: A JSON object containing the list of job objects
    """
    user = auth.username()
    job_db = JobDb()
    jobs = job_db.get_jobs_for_user(user)
    job_db.close()
    show_all_jobs = request.args.get('show_all_jobs')
    response = []
    if not show_all_jobs or show_all_jobs == "false":
        threshold_days = int(os.environ['OLD_JOBS_THRESHOLD_DAYS'])
        threshold_date = (datetime.datetime.now() -
                          datetime.timedelta(days=threshold_days))
        for job in jobs:
            if job['updated'] > threshold_date:
                response.append(job)
    else:
        response = jobs
    return jsonify(response)


@job_controller.route('/ingest_journals', methods=['POST'])
@auth.login_required
def journal_job_create():
    """
    Create a journal batch import job.

    Parameters can be provided as JSON as part of the request body
    and must match the job parameter schema.

    Valid user credential have to be given via HTTP basic authentication.

    Also adds the job to the job database.

    .. :quickref: Job Controller; Create a job of the specified job type

    **Example request**:

    .. sourcecode:: http

      POST /job/<job-type> HTTP/1.1

      {
            "objects": [{
                "id": "some_tiffs",
                "path": "some_tiffs",
                "metadata": {
                    "description": "Archäologischer Anzeiger",
                    "number": 1,
                    "ojs_journal_code": "test",
                    "volume": 1,
                    "publishing_year": 2015,
                    "reporting_year": 2011,
                    "zenon_id": 1449024
                }
            },{
                "id": "some_tiffs_2",
                "path": "some_tiffs_2",
                "metadata": {
                    "description": "Archäologischer Anzeiger",
                    "number": 1,
                    "ojs_journal_code": "test",
                    "volume": 1,
                    "publishing_year": 2015,
                    "reporting_year": 2011,
                    "zenon_id": 1449024
                }
            }],
            "options": {
                "ojs_metadata": {
                    "auto_publish_issue": true,
                    "default_create_frontpage": true,
                    "allow_upload_without_file": false
                }
            }
        }


    Each path ("some_tiffs" and "some_tiffs_2" in the example case, are
    expected to contain a directory "tif" that contains tif images.)

    **Example response SUCCESS**:

    .. sourcecode:: http

        HTTP/1.1 200 OK

        {
            "job_id": "399a5952-f594-11e9-ae9e-0242ac120007",
            "success": true
        }

    **Example response ERROR**:

    .. sourcecode:: http

        HTTP/1.1 400 BAD REQUEST

        {
            "error": {
                "code": "bad_request",
                "message": "400 Bad Request: The browser (or proxy)
                            sent a request that this server could
                            not understand."
            },
            "success": false
        }

    :reqheader Accept: application/json
    :param str job_type: name of the job type
    :<json dict objects: issue file path and metadata
    :<json dict options: job chain options

    :resheader Content-Type: application/json
    :>json dict: operation result
    :status 200: OK

    :return: A JSON object containing the status, the job id and the task
        ids of every subtask in every chain
    """
    if not request.data:
        raise ApiError("invalid_job_params", "No request payload found")
    params = request.get_json(force=True)
    user_name = auth.username()
    try:
        json_validation.validate_params(params, 'ingest_journals')
    except FileNotFoundError as e:
        raise ApiError("unknown_job_type", str(e), 404)
    except jsonschema.exceptions.ValidationError as e:
        raise ApiError("invalid_job_params", str(e), 400)

    job = IngestJournalsJob(params, user_name)
    job.run()

    body = jsonify({
        'success': True,
        'job_id': job.id})

    headers = {'Location': url_for(
        'job.job_status', job_id=job.id)}

    return body, 202, headers


@job_controller.route('/ingest_records', methods=['POST'])
@auth.login_required
def record_job_create():
    """
    Create a record batch import job.

    Parameters can be provided as JSON as part of the request body
    and must match the job parameter schema.

    Valid user credential have to be given via HTTP basic authentication.

    Also adds the job to the job database.

    .. :quickref: Job Controller; Create a job of the specified job type

    **Example request**:

    .. sourcecode:: http

      POST /job/<job-type> HTTP/1.1

      {
        "objects": [{
            "id": "some_tiffs",
            "path": "some_tiffs",
            "metadata": {
                "title": "54A, Attische Vasen ausser schwarzfigurige",
                "abstract": "12 drawings arranged by technique.",
                "created": "1836-1879",
                "author": [{
                    "firstname": "Peter",
                    "lastname": "Baumeister"
                    }],
                "zenon_id": 1449024,
                "atom_id": 1449025
            }
        },{
            "id": "some_tiffs_2",
            "path": "some_tiffs_2",
            "metadata": {
                "title": "54A, Attische Vasen ausser schwarzfigurige.",
                "abstract": "12 drawings arranged by technique.",
                "created": "1836-1879",
                "author": [{
                    "firstname": "Peter",
                    "lastname": "Baumeister"
                    }],
                "zenon_id": 1449024,
                "atom_id": 1449025
            }
        }],
        "options": {
            "do_ocr": true,
            "ocr_lang": "eng"
        }
    }

    Each path ("some_tiffs" and "some_tiffs_2" in the example case, are
    expected to contain a directory "tif" that contains tif images.)

    **Example response SUCCESS**:

    .. sourcecode:: http

        HTTP/1.1 200 OK

        {
            "job_id": "399a5952-f594-11e9-ae9e-0242ac120007",
            "success": true
        }

    **Example response ERROR**:

    .. sourcecode:: http

        HTTP/1.1 400 BAD REQUEST

        {
            "error": {
                "code": "bad_request",
                "message": "400 Bad Request: The browser (or proxy)
                            sent a request that this server could
                            not understand."
            },
            "success": false
        }

    :reqheader Accept: application/json
    :param str job_type: name of the job type
    :<json dict objects: records with file path and metadata
    :<json dict options: job chain options

    :resheader Content-Type: application/json
    :>json dict: operation result
    :status 200: OK

    :return: A JSON object containing the status, the job id and the task
        ids of every subtask in every chain
    """
    if not request.data:
        raise ApiError("invalid_job_params", "No request payload found")
    params = request.get_json(force=True)
    user_name = auth.username()
    try:
        json_validation.validate_params(params, 'ingest_records')
    except FileNotFoundError as e:
        raise ApiError("unknown_job_type", str(e), 404)
    except jsonschema.exceptions.ValidationError as e:
        raise ApiError("invalid_job_params", str(e), 400)

    job = IngestRecordsJob(params, user_name)
    job.run()

    body = jsonify({
        'success': True,
        'job_id': job.id})

    headers = {'Location': url_for(
        'job.job_status', job_id=job.id)}
    return body, 202, headers


@job_controller.route('/param_schema/<job_type>', methods=['GET'])
def get_job_param_schema(job_type):
    """
    Serve the contents of the JSON parameter schema for the given job type.

    .. :quickref: Job Controller; Contents of the job param schema file

    **Example request**:

    .. sourcecode:: http

      GET /job/<job_type> HTTP/1.1

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK

        {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "additionalProperties": false,
            "description": "Used to validate ingest-journal job parameters",
            "properties": {
                "objects": {
                    "items": {
                        "properties": {
                            "path": {
                                "type": "string"
                            }
                        },
                        "required": [
                            "path"
                        ],
                        "type": "object"
                    },
                    "type": "array"
                },
                "options": {
                    "additionalProperties": false,
                    "properties": {
                        "do_nlp": {
                            "type": "boolean"
                        },
                        "do_ocr": {
                            "type": "boolean"
                        },
                        "nlp_params": {
                            "additionalProperties": false,
                            "properties": {
                                "lang": {
                                    "type": "string"
                                }
                            },
                            "required": [
                                "lang"
                            ],
                            "type": "object"
                        },
                        "ocr_lang": {
                            "type": "string"
                        },
                        "ojs_metadata": {
                            "additionalProperties": false,
                            "properties": {
                                "allow_upload_without_file": {
                                    "type": "boolean"
                                },
                                "auto_publish_issue": {
                                    "type": "boolean"
                                },
                                "default_create_frontpage": {
                                    "type": "boolean"
                                },
                                "ojs_journal_code": {
                                    "type": "string"
                                },
                                "ojs_user": {
                                    "type": "string"
                                }
                            },
                            "required": [
                                "ojs_journal_code",
                                "ojs_user",
                                "auto_publish_issue",
                                "default_create_frontpage",
                                "allow_upload_without_file"
                            ],
                            "type": "object"
                        }
                    },
                    "required": [
                        "ojs_metadata",
                        "do_ocr",
                        "nlp_params"
                    ],
                    "type": "object"
                }
            },
            "required": [
                "objects",
                "options"
            ],
            "title": "Ingest Journal schema",
            "type": "object"
        }

    :reqheader Accept: application/json
    :param str job_type: Name of the job type

    :resheader Content-Type: application/json
    :>json dict: operation result
    :status 200: OK

    :return: JSON file content of the job parameter schema
    """
    try:
        schema = json_validation.get_schema(job_type)
        return jsonify(schema)
    except FileNotFoundError:
        raise ApiError(
            "job_type_not_found",
            f"No definition for given job type '{job_type}' found",
            404)


@job_controller.route('/<job_id>', methods=['GET'])
def job_status(job_id):
    """
    Return the status information for a job.

    Also looks up the job  in the job database to get the name.

    This function is also used to get task status. Those cannot be found in the
    job database (as it only holds job info) and no further info will be
    returned.

    .. :quickref: Job Controller; Status information for a job

    **Example request**:

    .. sourcecode:: http

      GET /job/<job-id> HTTP/1.1

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK

        {
            "children": [
                {
                    "job_id": "f602de62-f594-11e9-9ab2-0242ac130009",
                    "state": "success",
                    "type": "create_object"
                },
                {
                    "job_id": "f6036210-f594-11e9-b1cf-0242ac130009",
                    "state": "success",
                    "type": "list_files"
                },
                {
                    "job_id": "f6038f76-f594-11e9-9977-0242ac130009",
                    "state": "success",
                    "type": "convert.merge_converted_pdf"
                },
                {
                    "job_id": "f603bac2-f594-11e9-a1c9-0242ac130009",
                    "state": "success",
                    "type": "list_files"
                },
                {
                    "job_id": "f603e442-f594-11e9-9b1f-0242ac130009",
                    "state": "success",
                    "type": "list_files"
                },
                {
                    "job_id": "f6040a82-f594-11e9-a658-0242ac130009",
                    "state": "success",
                    "type": "generate_xml"
                },
                {
                    "job_id": "f60433de-f594-11e9-9545-0242ac130009",
                    "state": "success",
                    "type": "generate_xml"
                },
                {
                    "job_id": "f604609a-f594-11e9-84db-0242ac130009",
                    "state": "success",
                    "type": "publish_to_ojs"
                },
                {
                    "job_id": "f6048698-f594-11e9-be6b-0242ac130009",
                    "state": "success",
                    "type": "publish_to_repository"
                },
                {
                    "job_id": "f604aa4a-f594-11e9-873c-0242ac130009",
                    "state": "success",
                    "type": "publish_to_archive"
                },
                {
                    "job_id": "f604d1f8-f594-11e9-bf3a-0242ac130009",
                    "state": "success",
                    "type": "cleanup_workdir"
                },
                {
                    "job_id": "f604f78a-f594-11e9-836a-0242ac130009",
                    "state": "success",
                    "type": "finish_chain"
                }
            ],
            "created": "Wed, 23 Oct 2019 12:59:34 GMT",
            "duration": "0:00:05",
            "errors": [],
            "job_id": "f602db90-f594-11e9-b848-0242ac130009",
            "job_type": "chain",
            "name": "chain-f602db90-f594-11e9-b848-0242ac130009",
            "parameters": {
                "work_path": "f602db90-f594-11e9-b848-0242ac130009"
            },
            "parent_job_id": "f5fe4d76-f594-11e9-8671-0242ac130009",
            "started": "Wed, 23 Oct 2019 12:59:34 GMT",
            "state": "success",
            "updated": "Wed, 23 Oct 2019 12:59:39 GMT",
            "user": "test_user"
        }

    :reqheader Accept: application/json
    :param str job_id: Job ID

    :resheader Content-Type: application/json
    :>json dict: operation result
    :status 200: OK

    :return: A JSON object containing the status info
    """
    job_db = JobDb()
    job = job_db.get_job_by_id(job_id)
    job_db.close()

    job['duration'] = str(datetime.timedelta(
        seconds=int((job['updated'] - job['created']).total_seconds())))
    return jsonify(job)
