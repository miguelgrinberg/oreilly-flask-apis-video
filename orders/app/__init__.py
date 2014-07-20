import os
from flask import Flask, jsonify, g
from flask.ext.sqlalchemy import SQLAlchemy
from .decorators import json, no_cache, rate_limit

db = SQLAlchemy()


def create_app(config_name):
    """Create an application instance."""
    app = Flask(__name__)

    # apply configuration
    cfg = os.path.join(os.getcwd(), 'config', config_name + '.py')
    app.config.from_pyfile(cfg)

    # initialize extensions
    db.init_app(app)

    # register blueprints
    from .api_v1 import api as api_blueprint
    app.register_blueprint(api_blueprint, url_prefix='/api/v1')

    # register an after request handler
    @app.after_request
    def after_request(rv):
        headers = getattr(g, 'headers', {})
        rv.headers.extend(headers)
        return rv

    # authentication token route
    from .auth import auth
    @app.route('/get-auth-token')
    @auth.login_required
    @rate_limit(1, 600)  # one call per 10 minute period
    @no_cache
    @json
    def get_auth_token():
        return {'token': g.user.generate_auth_token()}

    return app
