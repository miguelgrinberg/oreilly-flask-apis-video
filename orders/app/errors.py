from flask import jsonify
from .exceptions import ValidationError
from .api_v1 import api


@api.errorhandler(ValidationError)
def bad_request(e):
    response = jsonify({'status': 400, 'error': 'bad request',
                        'message': e.args[0]})
    response.status_code = 400
    return response


@api.errorhandler(304)
def not_modified(e):
    response = jsonify({'status': 304, 'error': 'not modified',
                        'message': ''})
    response.status_code = 304
    return response


@api.app_errorhandler(404)  # this has to be an app-wide handler
def not_found(e):
    response = jsonify({'status': 404, 'error': 'not found',
                        'message': 'invalid resource URI'})
    response.status_code = 404
    return response


@api.errorhandler(405)
def method_not_supported(e):
    response = jsonify({'status': 405, 'error': 'method not supported',
                        'message': 'the method is not supported'})
    response.status_code = 405
    return response


@api.errorhandler(412)
def precondition_failed(e):
    response = jsonify({'status': 412, 'error': 'precondition failed',
                        'message': ''})
    response.status_code = 412
    return response


@api.app_errorhandler(500)  # this has to be an app-wide handler
def internal_server_error(e):
    response = jsonify({'status': 500, 'error': 'internal server error',
                        'message': e.args[0]})
    response.status_code = 500
    return response
