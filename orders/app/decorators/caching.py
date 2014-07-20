import functools
import hashlib
from flask import request, make_response, jsonify


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
        rv = make_response(rv)

        # etags only make sense for request that are cacheable, so only
        # GET and HEAD requests are allowed
        if request.method not in ['GET', 'HEAD']:
            return rv

        # if the response is not a code 200 OK then we let it through
        # unchanged
        if rv.status_code != 200:
            return rv

        # compute the etag for this request as the MD5 hash of the response
        # text and set it in the response header
        etag = '"' + hashlib.md5(rv.get_data()).hexdigest() + '"'
        rv.headers['ETag'] = etag

        # handle If-Match and If-None-Match request headers if present
        if_match = request.headers.get('If-Match')
        if_none_match = request.headers.get('If-None-Match')
        if if_match:
            # only return the response if the etag for this request matches
            # any of the etags given in the If-Match header. If there is no
            # match, then return a 412 Precondition Failed status code
            etag_list = [tag.strip() for tag in if_match.split(',')]
            if etag not in etag_list and '*' not in etag_list:
                response = jsonify({'status': 412, 'error': 'precondition failed',
                                    'message': 'precondition failed'})
                response.status_code = 412
                return response
        elif if_none_match:
            # only return the response if the etag for this request does not
            # match any of the etags given in the If-None-Match header. If
            # one matches, then return a 304 Not Modified status code
            etag_list = [tag.strip() for tag in if_none_match.split(',')]
            if etag in etag_list or '*' in etag_list:
                response = jsonify({'status': 304, 'error': 'not modified',
                                    'message': 'resource not modified'})
                response.status_code = 304
                return response
        return rv
    return wrapped
