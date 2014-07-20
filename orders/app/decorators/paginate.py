import functools
from flask import url_for, request


def paginate(collection, max_per_page=25):
    """Generate a paginated response for a resource collection.

    Routes that use this decorator must return a SQLAlchemy query as a
    response.

    The output of this decorator is a Python dictionary with the paginated
    results. The application must ensure that this result is converted to a
    response object, either by chaining another decorator or by using a
    custom response object that accepts dictionaries."""
    def decorator(f):
        @functools.wraps(f)
        def wrapped(*args, **kwargs):
            # invoke the wrapped function
            query = f(*args, **kwargs)

            # obtain pagination arguments from the URL's query string
            page = request.args.get('page', 1, type=int)
            per_page = min(request.args.get('per_page', max_per_page,
                                            type=int), max_per_page)
            expanded = None
            if request.args.get('expanded', 0, type=int) != 0:
                expanded = 1

            # run the query with Flask-SQLAlchemy's pagination
            p = query.paginate(page, per_page)

            # build the pagination metadata to include in the response
            pages = {'page': page, 'per_page': per_page,
                     'total': p.total, 'pages': p.pages}
            if p.has_prev:
                pages['prev_url'] = url_for(request.endpoint, page=p.prev_num,
                                            per_page=per_page,
                                            expanded=expanded, _external=True,
                                            **kwargs)
            else:
                pages['prev_url'] = None
            if p.has_next:
                pages['next_url'] = url_for(request.endpoint, page=p.next_num,
                                            per_page=per_page,
                                            expanded=expanded, _external=True,
                                            **kwargs)
            else:
                pages['next_url'] = None
            pages['first_url'] = url_for(request.endpoint, page=1,
                                         per_page=per_page, expanded=expanded,
                                         _external=True, **kwargs)
            pages['last_url'] = url_for(request.endpoint, page=p.pages,
                                        per_page=per_page, expanded=expanded,
                                        _external=True, **kwargs)

            # generate the paginated collection as a dictionary
            if expanded:
                results = [item.export_data() for item in p.items]
            else:
                results = [item.get_url() for item in p.items]

            # return a dictionary as a response
            return {collection: results, 'pages': pages}
        return wrapped
    return decorator
