from flask import jsonify, request
from . import api
from .. import db
from ..models import Order, Customer


@api.route('/orders/', methods=['GET'])
def get_orders():
    return jsonify({'orders': [order.get_url() for order in Order.query.all()]})

@api.route('/customers/<int:id>/orders/', methods=['GET'])
def get_customer_orders(id):
    customer = Customer.query.get_or_404(id)
    return jsonify({'orders': [order.get_url() for order in
                               customer.orders.all()]})

@api.route('/orders/<int:id>', methods=['GET'])
def get_order(id):
    return jsonify(Order.query.get_or_404(id).export_data())

@api.route('/customers/<int:id>/orders/', methods=['POST'])
def new_customer_order(id):
    customer = Customer.query.get_or_404(id)
    order = Order(customer=customer)
    order.import_data(request.json)
    db.session.add(order)
    db.session.commit()
    return jsonify({}), 201, {'Location': order.get_url()}

@api.route('/orders/<int:id>', methods=['PUT'])
def edit_order(id):
    order = Order.query.get_or_404(id)
    order.import_data(request.json)
    db.session.add(order)
    db.session.commit()
    return jsonify({})

@api.route('/orders/<int:id>', methods=['DELETE'])
def delete_order(id):
    order = Order.query.get_or_404(id)
    db.session.delete(order)
    db.session.commit()
    return jsonify({})
