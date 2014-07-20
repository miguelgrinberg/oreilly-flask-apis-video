import unittest
from werkzeug.exceptions import NotFound
from app import create_app, db
from app.models import User, Customer
from .test_client import TestClient


class TestAPI(unittest.TestCase):
    default_username = 'dave'
    default_password = 'cat'

    def setUp(self):
        self.app = create_app('testing')
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
        rv, json = self.client.get('/api/v1/customers/')
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(json['customers'] == [])

        # add a customer
        rv, json = self.client.post('/api/v1/customers/',
                                    data={'name': 'john'})
        self.assertTrue(rv.status_code == 201)
        location = rv.headers['Location']
        rv, json = self.client.get(location)
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(json['name'] == 'john')
        rv, json = self.client.get('/api/v1/customers/')
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
        rv, json = self.client.get('/api/v1/products/')
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(json['products'] == [])

        # add a customer
        rv, json = self.client.post('/api/v1/products/',
                                    data={'name': 'prod1'})
        self.assertTrue(rv.status_code == 201)
        location = rv.headers['Location']
        rv, json = self.client.get(location)
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(json['name'] == 'prod1')
        rv, json = self.client.get('/api/v1/products/')
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
        rv, json = self.client.post('/api/v1/customers/',
                                    data={'name': 'john'})
        self.assertTrue(rv.status_code == 201)
        customer = rv.headers['Location']
        rv, json = self.client.get(customer)
        orders_url = json['orders_url']
        rv, json = self.client.get(orders_url)
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(json['orders'] == [])

        # define two products
        rv, json = self.client.post('/api/v1/products/',
                                    data={'name': 'prod1'})
        self.assertTrue(rv.status_code == 201)
        prod1 = rv.headers['Location']
        rv, json = self.client.post('/api/v1/products/',
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
        rv, json = self.client.get('/api/v1/orders/')
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
        rv, json = self.client.get('/api/v1/orders/')
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(len(json['orders']) == 0)

    def test_pagination(self):
        # define 55 customers (3 pages at 25 per page)
        customers = []
        for i in range(0, 55):
            customers.append(Customer(name='customer_{0:02d}'.format(i)))
        db.session.add_all(customers)
        db.session.commit()

        # get first page of customer list
        rv, json = self.client.get('/api/v1/customers/')
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(len(json['customers']) == 25)
        self.assertTrue('pages' in json)
        self.assertIsNone(json['pages']['prev_url'])
        self.assertTrue(json['customers'][0] == customers[0].get_url())
        self.assertTrue(json['customers'][-1] == customers[24].get_url())
        page1_url = json['pages']['first_url']
        page2_url = json['pages']['next_url']

        # get second page of customer list
        rv, json = self.client.get(page2_url)
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(len(json['customers']) == 25)
        self.assertTrue(json['customers'][0] == customers[25].get_url())
        self.assertTrue(json['customers'][-1] == customers[49].get_url())
        self.assertTrue(page1_url == json['pages']['prev_url'])
        page3_url = json['pages']['next_url']
        self.assertTrue(page3_url == json['pages']['last_url'])

        # get third page of customer list
        rv, json = self.client.get(page3_url)
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(len(json['customers']) == 5)
        self.assertTrue(json['customers'][0] == customers[50].get_url())
        self.assertTrue(json['customers'][-1] == customers[54].get_url())
        self.assertTrue(json['pages']['prev_url'] == page2_url)
        self.assertIsNone(json['pages']['next_url'])

        # get second page, with expanded results
        rv, json = self.client.get(page2_url + '&expanded=1')
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(len(json['customers']) == 25)
        self.assertTrue(json['customers'][0]['name'] == customers[25].name)
        self.assertTrue(json['customers'][0]['self_url'] ==
                        customers[25].get_url())
        self.assertTrue(json['customers'][-1]['name'] == customers[49].name)
        page1_url_expanded = json['pages']['prev_url']

        # get first page expanded, using previous link from page 2
        rv, json = self.client.get(page1_url_expanded)
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(len(json['customers']) == 25)
        self.assertTrue(json['customers'][0]['name'] == customers[0].name)
        self.assertTrue(json['customers'][24]['name'] == customers[24].name)
