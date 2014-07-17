from flask import jsonify, request
from . import api
from .. import db
from ..models import Customer


@api.route('/customers/', methods=['GET'])
def get_customers():
    return jsonify({'customers': [customer.get_url() for customer in
                                  Customer.query.all()]})

@api.route('/customers/<int:id>', methods=['GET'])
def get_customer(id):
    return jsonify(Customer.query.get_or_404(id).export_data())

@api.route('/customers/', methods=['POST'])
def new_customer():
    customer = Customer()
    customer.import_data(request.json)
    db.session.add(customer)
    db.session.commit()
    return jsonify({}), 201, {'Location': customer.get_url()}

@api.route('/customers/<int:id>', methods=['PUT'])
def edit_customer(id):
    customer = Customer.query.get_or_404(id)
    customer.import_data(request.json)
    db.session.add(customer)
    db.session.commit()
    return jsonify({})
