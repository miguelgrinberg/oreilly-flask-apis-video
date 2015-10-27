import functools
import hashlib
from flask import request, make_response, jsonify
from werkzeug.http import generate_etag, HTTP_STATUS_CODES
from werkzeug.datastructures import ETag


def cache_control(*directives):
    """Insert a Cache-Control header with the given directives."""
    def decorator(f):
        @functools.wraps(f)
        def wrapped(*args, **kwargs):
            # invoke the wrapped function
            rv = f(*args, **kwargs)

            # convert the returned value to a response object
            rv = make_response(rv)

            # insert the Cache-Control header and return response
            rv.headers['Cache-Control'] = ', '.join(directives)
            return rv
        return wrapped
    return decorator


def no_cache(f):
    """Insert a no-cache directive in the response. This decorator just
    invokes the cache-control decorator with the specific directives."""
    return cache_control('private', 'no-cache', 'no-store', 'max-age=0')(f)


def etag(f):
    """Add entity tag (etag) handling to the decorated route."""
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        # invoke the wrapped function and generate a response object from
        # its result
        rv = f(*args, **kwargs)
        response = make_response(rv)

        # etags only make sense for request that are cacheable, so only
        # GET and HEAD requests are processed
        if request.method not in ['GET', 'HEAD']:
            return response

        # if the response is not a code 200 OK then we let it through
        # unchanged
        if response.status_code != 200:
            return response

        # compute the etag for this request as the MD5 hash of the response
        # text and set it in the response header
        etag = generate_etag(response.get_data())
        response.set_etag(etag)

        status = 200
        # Handle If-Match and If-None-Match request headers if present
        if request.if_match:
            # Only return the response if the etag for this request matches
            # any of the etags given in the If-Match header. If there is no
            # match, then return a 412 Precondition Failed status code
            if not etag in request.if_match:
                status = 412
        elif request.if_none_match:
            # Only return the response if the etag for this request does not
            # match any of the etags given in the If-None-Match header. If
            # one matches, then return a 304 Not Modified status code
            if etag in request.if_none_match:
                status = 304

        # check if response needs to be modified due to ETags
        if status != 200:
            message = HTTP_STATUS_CODES[status]
            response = jsonify({'status': status, 'error': message,
                                'message': message})
            response.status_code = status

        return response
    return wrapped
