import os

basedir = os.path.abspath(os.path.dirname(__file__))  # Gets path of directory this file is in


class Config():
    SECRET_KEY = os.environ.get('SECRET_KEY')  # 'w7eugir27r2hf2832ui397f3u239' Secret Key for CSRF should be stored as environment variables.
    # SQLAlchemy config
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True  # Automatically commits database changes at the end of each request ''''Deprecated''''
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # SMTP config for flask_mail
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.googlemail.com')  # better to not use local host as server
    MAIL_PORT = int(os.environ.get('MAIL_PORT', '587'))
    MAIL_USE_TLS = True  # TLS: Transport Layer Security
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')  # $ export MAIL_USERNAME=<Gmail username>
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    TEST_MAIL_SUBJECT_PREFIX = '[Test]'
    TEST_MAIL_SENDER = 'Test Admin <' + os.environ.get('MAIL_USERNAME') + '@gmail.com>'
    TEST_ADMIN = os.environ.get('TEST_ADMIN')
    POSTS_PER_PAGE = 15
    FOLLOWS_PER_PAGE = 10
    COMMENTS_PER_PAGE = 10
    # ???Session Config ???

    @staticmethod  # Allows for application to costomise configuration
    def init_app(app):
        pass

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
                                'sqlite:///' + os.path.join(basedir, 'dev-data.sqlite')

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or \
                                'sqlite://'  # This runs database in-memory as it is not needed otherwise.

class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
                                'sqlite:///' + os.path.join(basedir, 'data.sqlite')


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,

    'default': DevelopmentConfig
}
