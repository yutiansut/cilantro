import os
import logging
import shutil

from flask import Blueprint, jsonify, request, send_file
from werkzeug.utils import secure_filename

from service.errors import ApiError
from service.user.user_service import auth

staging_controller = Blueprint('staging', __name__)

staging_dir = os.environ['STAGING_DIR']

allowed_extensions = ['xml', 'pdf', 'tif', 'tiff', 'json', 'csv']

log = logging.getLogger(__name__)


def _list_dir(dir_path):
    tree = []
    for entry in os.scandir(dir_path):
        if entry.is_file():
            tree.append({
                "type": "file",
                "name": entry.name})
        else:
            tree.append({
                "type": "directory",
                "name": entry.name,
                "contents": _list_dir(os.path.join(dir_path, entry.name))})
    return tree


@staging_controller.route('/<path:path>', methods=['DELETE'],
                          strict_slashes=False)
@auth.login_required
def delete_from_staging(path):
    r"""
    Delete file or directory from the staging area.

    .. :quickref: Staging Controller; \
        Delete file or directory from the staging area.

    **Example request**:

    .. sourcecode:: http

      DELETE /staging/<path> HTTP/1.1

    **Example response**:

    .. sourcecode:: http

      HTTP/1.1 200 OK

      TODO

    :reqheader Accept: application/json
    :resheader Content-Type: application/json
    :param str path: path to file or directory to be deleted
    """
    try:
        os.remove(os.path.join(staging_dir, auth.username(), path))
    except (FileNotFoundError, IsADirectoryError):
        try:
            shutil.rmtree(os.path.join(staging_dir, auth.username(), path))
        except FileNotFoundError:
            raise ApiError("file_not_found",
                           f"No resource was found under the path {path}", 404)

    return jsonify({"success": True}), 200


@staging_controller.route('', methods=['GET'], strict_slashes=False)
@auth.login_required
def list_staging():
    r"""
    List files and directories in the staging area.

    Returns a complete recursive folder hierarchy.

    .. :quickref: Staging Controller; \
        List files and directories in the staging area.

    **Example request**:

    .. sourcecode:: http

      GET /staging/ HTTP/1.1

    **Example response**:

    .. sourcecode:: http

      HTTP/1.1 200 OK

      TODO

    :reqheader Accept: application/json

    :resheader Content-Type: application/json
    :status 200: OK

    :return: JSON array containing objects for files and folders
    """
    try:
        tree = _list_dir(os.path.join(staging_dir, auth.username()))
    except FileNotFoundError:
        log.warn(f"List staging called on not-existing folder: "
                 f"{os.path.join(staging_dir, auth.username())}")
        tree = []
    return jsonify(tree)


@staging_controller.route('/<path:path>', methods=['GET'],
                          strict_slashes=False)
@auth.login_required
def get_path(path):
    r"""
    Retrieve a file or folder content from the staging folder.

    Returns A JSON array containing all file names, if it's a directory or
    the file's content if it's a file.

    .. :quickref: Staging Controller; \
        Retrieve a file or folder content from the staging folder.

    **Example request**:

    .. sourcecode:: http

      GET /staging/<path> HTTP/1.1

    **Example response**:

    .. sourcecode:: http

      HTTP/1.1 200 OK

      TODO

    :reqheader Accept: application/json
    :param str path: path to file

    :resheader Content-Type: application/json
    :status 200: array containing all file names, if it's a directory or the \
                 file's content if it's a file
    :status 404: file was not found
    """
    abs_path = os.path.join(staging_dir, auth.username(), path)
    if os.path.isdir(abs_path):
        return jsonify(os.listdir(abs_path))
    elif os.path.isfile(abs_path):
        return send_file(abs_path)
    else:
        raise ApiError("file_not_found",
                       f"No resource was found under the path {path}", 404)


@staging_controller.route('', methods=['POST'], strict_slashes=False)
@auth.login_required
def upload_to_staging():
    r"""
    Upload files to the staging area.

    If the names of the given files contain folders, these are created in the
    staging area if not already present.

    The upload endpoint is able to handle single and multiple files provided
    under any key.

    .. :quickref: Staging Controller; \
        Upload files to the staging area.

    **Example request**:

    .. sourcecode:: http

      POST /staging/ HTTP/1.1

    **Example response**:

    .. sourcecode:: http

      HTTP/1.1 200 OK

      {
          "result": {
              <uploaded_file_name>: {
                  "success": <boolean>,
                  "error": {
                      "code": <string>,
                      "message": <string>
                  }
              }
          }
      }

    :reqheader Accept: multipart/form-data
    :formparam file: file to be uploaded

    :resheader Content-Type: application/json
    :>json dict: operation result
    :status 200: OK
    :status 400: no files were provided
    :status 415: one of the files' extension is not allowed

    :return: a JSON object
    """
    log.debug(f"Uploading {len(request.files)} files")
    results = {}

    if request.files:
        for key in request.files:
            for file in request.files.getlist(key):
                results[file.filename] = _process_file(file, auth.username())
        return jsonify({"result": results}), 200
    raise ApiError("no_files_provided",
                   f"The request did not contain any files")


def _process_file(file, username):
    if _is_allowed_file(file.filename):
        try:
            _upload_file(file, username)
            return {"success": True}
        except Exception as e:
            return _generate_error_result(
                file,
                "upload_failed",
                "An unknown error occurred.",
                e)
    else:
        return _generate_error_result(
            file,
            "extension_not_allowed",
            f"File extension .{_get_file_extension(file.filename)}"
            f" is not allowed.")


def _generate_error_result(file, code, message, e=None):
    log.error(f"Error during upload of {file.filename}. {message}.")
    if e:
        log.error(f" Cause: {str(e)}")
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message}
        }


def _upload_file(file, username):
    path, filename = os.path.split(file.filename)
    folders = list(map(secure_filename, path.split("/")))
    full_path = os.path.join(staging_dir, username, *folders)
    os.makedirs(full_path, exist_ok=True)
    file.save(os.path.join(full_path, secure_filename(filename)))


def _is_allowed_file(filename):
    return '.' in filename and \
           _get_file_extension(filename) in allowed_extensions


def _get_file_extension(filename):
    return filename.rsplit('.', 1)[1].lower()
