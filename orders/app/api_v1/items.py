from flask import request
from . import api
from .. import db
from ..models import Order, Item
from ..decorators import json, paginate


@api.route('/orders/<int:id>/items/', methods=['GET'])
@json
@paginate('items')
def get_order_items(id):
    order = Order.query.get_or_404(id)
    return order.items

@api.route('/items/<int:id>', methods=['GET'])
@json
def get_item(id):
    return Item.query.get_or_404(id).export_data()

@api.route('/orders/<int:id>/items/', methods=['POST'])
@json
def new_order_item(id):
    order = Order.query.get_or_404(id)
    item = Item(order=order)
    item.import_data(request.json)
    db.session.add(item)
    db.session.commit()
    return {}, 201, {'Location': item.get_url()}

@api.route('/items/<int:id>', methods=['PUT'])
@json
def edit_item(id):
    item = Item.query.get_or_404(id)
    item.import_data(request.json)
    db.session.add(item)
    db.session.commit()
    return {}

@api.route('/items/<int:id>', methods=['DELETE'])
@json
def delete_item(id):
    item = Item.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    return {}
