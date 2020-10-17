from flask import g, jsonify
from flask_httpauth import HTTPBasicAuth
from . import api
from .errors import unauthorized, forbidden
from ..models import User

auth = HTTPBasicAuth()


# Important is use HTTPS as email n password can be caught easily
# Since sensitive info sould leak,
# timed tokens is given as optional to the client.
@auth.verify_password
def verify_password(email_or_token, password):
    if email_or_token == '':
        return False
    if password == '':
        g.current_user = User.verify_auth_token(email_or_token)
        g.token_used = True
        return g.current_user is not None
    user = User.query.filter_by(email=email_or_token).first()
    if not user:
        return False
    g.current_user = user
    return user.verify_password(password)


@auth.error_handler
def auth_error():
    return unauthorized('Invalid credentials')


@api.before_request
@auth.login_required  # Calls verify_password function
def before_request():
    if not g.current_user.is_anonymous and not g.current_user.confirmed:
        return forbidden('Unconfirmed Account')


@api.route('/token/', methods=['POST'])
def get_token():
    ''' If token is stolen, they should not be able to generate new tokens
        using the old ones. Hence, token_used is needed.'''
    if g.current_user.is_anonymous or g.token_used:
        return unauthorized('Invalid credentials')
    token = g.current_user.generate_auth_token(expiration=3600)
    return jsonify({'token': token, 'expiration': 3600})
