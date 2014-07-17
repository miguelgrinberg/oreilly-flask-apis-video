from flask import jsonify, request
from . import api
from .. import db
from ..models import Product


@api.route('/products/', methods=['GET'])
def get_products():
    return jsonify({'products': [product.get_url() for product in
                                 Product.query.all()]})

@api.route('/products/<int:id>', methods=['GET'])
def get_product(id):
    return jsonify(Product.query.get_or_404(id).export_data())

@api.route('/products/', methods=['POST'])
def new_product():
    product = Product()
    product.import_data(request.json)
    db.session.add(product)
    db.session.commit()
    return jsonify({}), 201, {'Location': product.get_url()}

@api.route('/products/<int:id>', methods=['PUT'])
def edit_product(id):
    product = Product.query.get_or_404(id)
    product.import_data(request.json)
    db.session.add(product)
    db.session.commit()
    return jsonify({})
