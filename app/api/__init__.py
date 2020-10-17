from flask import Blueprint

api = Blueprint('api', __name__)

# To prevent circular dependencies
from . import authentication, posts, comments, users, decorators, errors
