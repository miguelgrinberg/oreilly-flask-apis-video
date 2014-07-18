import coverage
COV = coverage.coverage(branch=True, include='api*')
COV.start()

import os
os.environ['DATABASE_URL'] = 'sqlite:///../test.sqlite'

import unittest
from werkzeug.exceptions import NotFound
from api import app, db, User
from test_client import TestClient

class TestAPI(unittest.TestCase):
    default_username = 'dave'
    default_password = 'cat'

    def setUp(self):
        self.app = app
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()
        u = User(username=self.default_username)
        u.set_password(self.default_password)
        db.session.add(u)
        db.session.commit()
        self.client = TestClient(self.app, u.generate_auth_token(), '')

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_customers(self):
        # get list of customers
        rv, json = self.client.get('/customers/')
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(json['customers'] == [])

        # add a customer
        rv, json = self.client.post('/customers/', data={'name': 'john'})
        self.assertTrue(rv.status_code == 201)
        location = rv.headers['Location']
        rv, json = self.client.get(location)
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(json['name'] == 'john')
        rv, json = self.client.get('/customers/')
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(json['customers'] == [location])

        # edit the customer
        rv, json = self.client.put(location, data={'name': 'John Smith'})
        self.assertTrue(rv.status_code == 200)
        rv, json = self.client.get(location)
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(json['name'] == 'John Smith')

    def test_products(self):
        # get list of products
        rv, json = self.client.get('/products/')
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(json['products'] == [])

        # add a customer
        rv, json = self.client.post('/products/',
                                    data={'name': 'prod1'})
        self.assertTrue(rv.status_code == 201)
        location = rv.headers['Location']
        rv, json = self.client.get(location)
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(json['name'] == 'prod1')
        rv, json = self.client.get('/products/')
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(json['products'] == [location])

        # edit the customer
        rv, json = self.client.put(location, data={'name': 'product1'})
        self.assertTrue(rv.status_code == 200)
        rv, json = self.client.get(location)
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(json['name'] == 'product1')

    def test_orders_and_items(self):
        # define a customer
        rv, json = self.client.post('/customers/',
                                    data={'name': 'john'})
        self.assertTrue(rv.status_code == 201)
        customer = rv.headers['Location']
        rv, json = self.client.get(customer)
        orders_url = json['orders_url']
        rv, json = self.client.get(orders_url)
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(json['orders'] == [])

        # define two products
        rv, json = self.client.post('/products/',
                                    data={'name': 'prod1'})
        self.assertTrue(rv.status_code == 201)
        prod1 = rv.headers['Location']
        rv, json = self.client.post('/products/',
                                    data={'name': 'prod2'})
        self.assertTrue(rv.status_code == 201)
        prod2 = rv.headers['Location']

        # create an order
        rv, json = self.client.post(orders_url,
                                    data={'date': '2014-01-01T00:00:00Z'})
        self.assertTrue(rv.status_code == 201)
        order = rv.headers['Location']
        rv, json = self.client.get(order)
        items_url = json['items_url']
        rv, json = self.client.get(items_url)
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(json['items'] == [])
        rv, json = self.client.get('/orders/')
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(len(json['orders']) == 1)
        self.assertTrue(order in json['orders'])

        # edit the order
        rv, json = self.client.put(order,
                                   data={'date': '2014-02-02T00:00:00Z'})
        self.assertTrue(rv.status_code == 200)
        rv, json = self.client.get(order)
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(json['date'] == '2014-02-02T00:00:00Z')

        # add two items to order
        rv, json = self.client.post(items_url, data={'product_url': prod1,
                                                     'quantity': 2})
        self.assertTrue(rv.status_code == 201)
        item1 = rv.headers['Location']
        rv, json = self.client.post(items_url, data={'product_url': prod2,
                                                     'quantity': 1})
        self.assertTrue(rv.status_code == 201)
        item2 = rv.headers['Location']
        rv, json = self.client.get(items_url)
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(len(json['items']) == 2)
        self.assertTrue(item1 in json['items'])
        self.assertTrue(item2 in json['items'])
        rv, json = self.client.get(item1)
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(json['product_url'] == prod1)
        self.assertTrue(json['quantity'] == 2)
        self.assertTrue(json['order_url'] == order)
        rv, json = self.client.get(item2)
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(json['product_url'] == prod2)
        self.assertTrue(json['quantity'] == 1)
        self.assertTrue(json['order_url'] == order)

        # edit the second item
        rv, json = self.client.put(item2, data={'product_url': prod2,
                                                'quantity': 3})
        self.assertTrue(rv.status_code == 200)
        rv, json = self.client.get(item2)
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(json['product_url'] == prod2)
        self.assertTrue(json['quantity'] == 3)
        self.assertTrue(json['order_url'] == order)

        # delete first item
        rv, json = self.client.delete(item1)
        self.assertTrue(rv.status_code == 200)
        rv, json = self.client.get(items_url)
        self.assertFalse(item1 in json['items'])
        self.assertTrue(item2 in json['items'])

        # delete order
        rv, json = self.client.delete(order)
        self.assertTrue(rv.status_code == 200)
        with self.assertRaises(NotFound):
            rv, json = self.client.get(item2)
        rv, json = self.client.get('/orders/')
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(len(json['orders']) == 0)

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAPI)
    unittest.TextTestRunner(verbosity=2).run(suite)
    COV.stop()
    COV.report()
