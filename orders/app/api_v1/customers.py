from flask import request
from . import api
from .. import db
from ..models import Customer
from ..decorators import json


@api.route('/customers/', methods=['GET'])
@json
def get_customers():
    return {'customers': [customer.get_url() for customer in
                          Customer.query.all()]}

@api.route('/customers/<int:id>', methods=['GET'])
@json
def get_customer(id):
    return Customer.query.get_or_404(id)

@api.route('/customers/', methods=['POST'])
@json
def new_customer():
    customer = Customer()
    customer.import_data(request.json)
    db.session.add(customer)
    db.session.commit()
    return {}, 201, {'Location': customer.get_url()}

@api.route('/customers/<int:id>', methods=['PUT'])
@json
def edit_customer(id):
    customer = Customer.query.get_or_404(id)
    customer.import_data(request.json)
    db.session.add(customer)
    db.session.commit()
    return {}
