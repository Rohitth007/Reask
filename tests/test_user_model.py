import unittest
import time
from app.models import User, Permission, AnonymousUser
from app import db

class UserModelTestCase(unittest.TestCase):
    ### Password Tests
    def test_password_setter(self):
        u = User(hash_password = 'cat')
        self.assertFalse(u.password_hash is None)  # Checks if password_hash is None is False

    def test_no_password_getter(self):
        u = User(hash_password = 'cat')
        with self.assertRaises(AttributeError):
            u.password

    def test_password_verification(self):
        u = User(hash_password = 'cat')
        self.assertTrue(u.verify_password('cat'))
        self.assertFalse(u.verify_password('dog'))

    def test_password_salts_are_random(self):  # Password+salt is hashed to give different hashes.
        u = User(hash_password = 'cat')
        u2 = User(hash_password = 'cat')
        self.assertTrue(u.password_hash != u2.password_hash)

    ### JSON Token Tests
    def test_valid_confirmation_token(self):
        u = User(hash_password = 'cat')
        db.session.add(u)
        db.session.commit()
        self.assertFalse(u.confirmed)
        token = u.generate_confirmation_token()
        self.assertTrue(u.confirm(token))
        self.assertTrue(u.confirmed)

    def test_invalid_confirmation_token(self):
        u1 = User(hash_password = 'cat')
        u2 = User(hash_password = 'dog')
        db.session.add(u1)
        db.session.add(u2)
        db.session.commit()
        token = u1.generate_confirmation_token()
        self.assertFalse(u2.confirm(token))

    def test_expired_confirmation_token(self):
        u = User(hash_password = 'cat')
        db.session.add(u)
        db.session.commit()
        token = u.generate_confirmation_token(1)
        time.sleep(2)
        self.assertFalse(u.confirm(token))

    ### Permission Tests
    def test_user_role(self):
        u = User(email = "test@example.com", hash_password='cat')
        self.assertTrue(u.can(Permission.FOLLOW))
        self.assertTrue(u.can(Permission.COMMENT))
        self.assertTrue(u.can(Permission.WRITE))
        self.assertFalse(u.can(Permission.MODERATE))
        self.assertFalse(u.can(Permission.ADMIN))

    def test_anonymous_user(self):
        u = AnonymousUser()
        self.assertFalse(u.can(Permission.FOLLOW))
        self.assertFalse(u.can(Permission.COMMENT))
        self.assertFalse(u.can(Permission.WRITE))
        self.assertFalse(u.can(Permission.MODERATE))
        self.assertFalse(u.can(Permission.ADMIN))
