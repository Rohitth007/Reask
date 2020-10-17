# unit tests
import unittest
from flask import current_app
from app import create_app, db

''' Automatically first call the setUp function and ends with tearDown after every test.
    any function starting with 'test_' is tested. '''
class BasicTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()  # Binds the app context to the current app
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_app_exists(self):
        self.assertFalse(current_app is None)

    def test_app_is_testing(self):
        self.assertTrue(current_app.config['TESTING'])
