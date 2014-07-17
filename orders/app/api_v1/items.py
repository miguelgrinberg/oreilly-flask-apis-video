from flask import jsonify, request
from . import api
from .. import db
from ..models import Order, Item


@api.route('/orders/<int:id>/items/', methods=['GET'])
def get_order_items(id):
    order = Order.query.get_or_404(id)
    return jsonify({'items': [item.get_url() for item in order.items.all()]})

@api.route('/items/<int:id>', methods=['GET'])
def get_item(id):
    return jsonify(Item.query.get_or_404(id).export_data())

@api.route('/orders/<int:id>/items/', methods=['POST'])
def new_order_item(id):
    order = Order.query.get_or_404(id)
    item = Item(order=order)
    item.import_data(request.json)
    db.session.add(item)
    db.session.commit()
    return jsonify({}), 201, {'Location': item.get_url()}

@api.route('/items/<int:id>', methods=['PUT'])
def edit_item(id):
    item = Item.query.get_or_404(id)
    item.import_data(request.json)
    db.session.add(item)
    db.session.commit()
    return jsonify({})

@api.route('/items/<int:id>', methods=['DELETE'])
def delete_item(id):
    item = Item.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    return jsonify({})
