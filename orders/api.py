import os
from datetime import datetime
from dateutil import parser as datetime_parser
from dateutil.tz import tzutc
from flask import Flask, url_for, jsonify, request
from flask.ext.sqlalchemy import SQLAlchemy
from utils import split_url


basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, '../data.sqlite')

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path

db = SQLAlchemy(app)


class ValidationError(ValueError):
    pass


@app.errorhandler(ValidationError)
def bad_request(e):
    response = jsonify({'status': 400, 'error': 'bad request',
                        'message': e.args[0]})
    response.status_code = 400
    return response

@app.errorhandler(404)
def not_found(e):
    response = jsonify({'status': 404, 'error': 'not found',
                        'message': 'invalid resource URI'})
    response.status_code = 404
    return response

@app.errorhandler(405)
def method_not_supported(e):
    response = jsonify({'status': 405, 'error': 'method not supported',
                        'message': 'the method is not supported'})
    response.status_code = 405
    return response

@app.errorhandler(500)
def internal_server_error(e):
    response = jsonify({'status': 500, 'error': 'internal server error',
                        'message': e.args[0]})
    response.status_code = 500
    return response


class Customer(db.Model):
    __tablename__ = 'customers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True)
    orders = db.relationship('Order', backref='customer', lazy='dynamic')

    def get_url(self):
        return url_for('get_customer', id=self.id, _external=True)

    def export_data(self):
        return {
            'self_url': self.get_url(),
            'name': self.name,
            'orders_url': url_for('get_customer_orders', id=self.id,
                                  _external=True)
        }

    def import_data(self, data):
        try:
            self.name = data['name']
        except KeyError as e:
            raise ValidationError('Invalid customer: missing ' + e.args[0])
        return self


class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True)
    items = db.relationship('Item', backref='product', lazy='dynamic')

    def get_url(self):
        return url_for('get_product', id=self.id, _external=True)

    def export_data(self):
        return {
            'self_url': self.get_url(),
            'name': self.name
        }

    def import_data(self, data):
        try:
            self.name = data['name']
        except KeyError as e:
            raise ValidationError('Invalid product: missing ' + e.args[0])
        return self


class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'),
                            index=True)
    date = db.Column(db.DateTime, default=datetime.now)
    items = db.relationship('Item', backref='order', lazy='dynamic',
                            cascade='all, delete-orphan')

    def get_url(self):
        return url_for('get_order', id=self.id, _external=True)

    def export_data(self):
        return {
            'self_url': self.get_url(),
            'customer_url': self.customer.get_url(),
            'date': self.date.isoformat() + 'Z',
            'items_url': url_for('get_order_items', id=self.id,
                                 _external=True)
        }

    def import_data(self, data):
        try:
            self.date = datetime_parser.parse(data['date']).astimezone(
                tzutc()).replace(tzinfo=None)
        except KeyError as e:
            raise ValidationError('Invalid order: missing ' + e.args[0])
        return self


class Item(db.Model):
    __tablename__ = 'items'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'),
                           index=True)
    quantity = db.Column(db.Integer)

    def get_url(self):
        return url_for('get_item', id=self.id, _external=True)

    def export_data(self):
        return {
            'self_url': self.get_url(),
            'order_url': self.order.get_url(),
            'product_url': self.product.get_url(),
            'quantity': self.quantity
        }

    def import_data(self, data):
        try:
            endpoint, args = split_url(data['product_url'])
            self.quantity = int(data['quantity'])
        except KeyError as e:
            raise ValidationError('Invalid order: missing ' + e.args[0])
        if endpoint != 'get_product' or not 'id' in args:
            raise ValidationError('Invalid product URL: ' +
                                  data['product_url'])
        self.product = Product.query.get(args['id'])
        if self.product is None:
            raise ValidationError('Invalid product URL: ' +
                                  data['product_url'])
        return self


@app.route('/customers/', methods=['GET'])
def get_customers():
    return jsonify({'customers': [customer.get_url() for customer in
                                  Customer.query.all()]})

@app.route('/customers/<int:id>', methods=['GET'])
def get_customer(id):
    return jsonify(Customer.query.get_or_404(id).export_data())

@app.route('/customers/', methods=['POST'])
def new_customer():
    customer = Customer()
    customer.import_data(request.json)
    db.session.add(customer)
    db.session.commit()
    return jsonify({}), 201, {'Location': customer.get_url()}

@app.route('/customers/<int:id>', methods=['PUT'])
def edit_customer(id):
    customer = Customer.query.get_or_404(id)
    customer.import_data(request.json)
    db.session.add(customer)
    db.session.commit()
    return jsonify({})


@app.route('/products/', methods=['GET'])
def get_products():
    return jsonify({'products': [product.get_url() for product in
                                 Product.query.all()]})

@app.route('/products/<int:id>', methods=['GET'])
def get_product(id):
    return jsonify(Product.query.get_or_404(id).export_data())

@app.route('/products/', methods=['POST'])
def new_product():
    product = Product()
    product.import_data(request.json)
    db.session.add(product)
    db.session.commit()
    return jsonify({}), 201, {'Location': product.get_url()}

@app.route('/products/<int:id>', methods=['PUT'])
def edit_product(id):
    product = Product.query.get_or_404(id)
    product.import_data(request.json)
    db.session.add(product)
    db.session.commit()
    return jsonify({})



@app.route('/orders/', methods=['GET'])
def get_orders():
    return jsonify({'orders': [order.get_url() for order in Order.query.all()]})

@app.route('/customers/<int:id>/orders/', methods=['GET'])
def get_customer_orders(id):
    customer = Customer.query.get_or_404(id)
    return jsonify({'orders': [order.get_url() for order in
                               customer.orders.all()]})

@app.route('/orders/<int:id>', methods=['GET'])
def get_order(id):
    return jsonify(Order.query.get_or_404(id).export_data())

@app.route('/customers/<int:id>/orders/', methods=['POST'])
def new_customer_order(id):
    customer = Customer.query.get_or_404(id)
    order = Order(customer=customer)
    order.import_data(request.json)
    db.session.add(order)
    db.session.commit()
    return jsonify({}), 201, {'Location': order.get_url()}

@app.route('/orders/<int:id>', methods=['PUT'])
def edit_order(id):
    order = Order.query.get_or_404(id)
    order.import_data(request.json)
    db.session.add(order)
    db.session.commit()
    return jsonify({})

@app.route('/orders/<int:id>', methods=['DELETE'])
def delete_order(id):
    order = Order.query.get_or_404(id)
    db.session.delete(order)
    db.session.commit()
    return jsonify({})


@app.route('/orders/<int:id>/items/', methods=['GET'])
def get_order_items(id):
    order = Order.query.get_or_404(id)
    return jsonify({'items': [item.get_url() for item in order.items.all()]})

@app.route('/items/<int:id>', methods=['GET'])
def get_item(id):
    return jsonify(Item.query.get_or_404(id).export_data())

@app.route('/orders/<int:id>/items/', methods=['POST'])
def new_order_item(id):
    order = Order.query.get_or_404(id)
    item = Item(order=order)
    item.import_data(request.json)
    db.session.add(item)
    db.session.commit()
    return jsonify({}), 201, {'Location': item.get_url()}

@app.route('/items/<int:id>', methods=['PUT'])
def edit_item(id):
    item = Item.query.get_or_404(id)
    item.import_data(request.json)
    db.session.add(item)
    db.session.commit()
    return jsonify({})

@app.route('/items/<int:id>', methods=['DELETE'])
def delete_item(id):
    item = Item.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    return jsonify({})

if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)
