# This Contructor gives time to set up the configuration settings using a factory function.
from flask import Flask, render_template
from flask_bootstrap import Bootstrap
from flask_mail import Mail  # Flask wrapper for smptlib.
from flask_moment import Moment  # Flask wrapper for moment.js that handles date &time formatting. jQuery is required
from flask_sqlalchemy import SQLAlchemy  # Flask wrapper for SQLAlchemy which is an ORM for many SQL dbs. Better Security and Migration.
from flask_login import LoginManager
from flask_pagedown import PageDown
from config import config  # from ../config.py

# Initialising without 'app'
bootstrap = Bootstrap()
mail = Mail()  # Google doesnt accept standard SMPT(Simple Mail Transfer Protocol), so "Allow less secure apps" has to selected in the GMail Account
moment = Moment()
pagedown = PageDown()
db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'  # Since login is in the 'auth' blueprint

# Factory function
def create_app(config_type):
    app = Flask(__name__)
    app.config.from_object(config[config_type])  # converts the attributes in this object to the config dictionary
    config[config_type].init_app(app)  # For additional configuration

    # each of these objects hv an 'init_app' method which is different from the one written in ../config.py
    bootstrap.init_app(app)
    mail.init_app(app)
    moment.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)
    pagedown.init_app(app)

    # attach routes and custon error pages blueprint
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    from .api import api as api_bluprint
    app.register_blueprint(api_bluprint, url_prefix='/api/v1')

    return app
