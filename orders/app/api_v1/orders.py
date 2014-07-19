from flask import request
from . import api
from .. import db
from ..models import Order, Customer
from ..decorators import json, paginate


@api.route('/orders/', methods=['GET'])
@json
@paginate('orders')
def get_orders():
    return Order.query

@api.route('/customers/<int:id>/orders/', methods=['GET'])
@json
@paginate('orders')
def get_customer_orders(id):
    customer = Customer.query.get_or_404(id)
    return customer.orders

@api.route('/orders/<int:id>', methods=['GET'])
@json
def get_order(id):
    return Order.query.get_or_404(id)

@api.route('/customers/<int:id>/orders/', methods=['POST'])
@json
def new_customer_order(id):
    customer = Customer.query.get_or_404(id)
    order = Order(customer=customer)
    order.import_data(request.json)
    db.session.add(order)
    db.session.commit()
    return {}, 201, {'Location': order.get_url()}

@api.route('/orders/<int:id>', methods=['PUT'])
@json
def edit_order(id):
    order = Order.query.get_or_404(id)
    order.import_data(request.json)
    db.session.add(order)
    db.session.commit()
    return {}

@api.route('/orders/<int:id>', methods=['DELETE'])
@json
def delete_order(id):
    order = Order.query.get_or_404(id)
    db.session.delete(order)
    db.session.commit()
    return {}
