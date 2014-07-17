from flask import request
from . import api
from .. import db
from ..models import Product
from ..decorators import json


@api.route('/products/', methods=['GET'])
@json
def get_products():
    return {'products': [product.get_url() for product in
                         Product.query.all()]}

@api.route('/products/<int:id>', methods=['GET'])
@json
def get_product(id):
    return Product.query.get_or_404(id)

@api.route('/products/', methods=['POST'])
@json
def new_product():
    product = Product()
    product.import_data(request.json)
    db.session.add(product)
    db.session.commit()
    return {}, 201, {'Location': product.get_url()}

@api.route('/products/<int:id>', methods=['PUT'])
@json
def edit_product(id):
    product = Product.query.get_or_404(id)
    product.import_data(request.json)
    db.session.add(product)
    db.session.commit()
    return {}
