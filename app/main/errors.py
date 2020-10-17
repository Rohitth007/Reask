from flask import render_template, jsonify, request
from . import main  # blueprint from __init__.py


# here app_errorhandler has to be used instead of errorhandler to show effect for everything not only routes
@main.app_errorhandler(403)
def forbidden(e):
    # Since api client cant accept html, we send json
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        response = jsonify({'error': 'forbidden'})
        response.status_type = 403
        return response
    return render_template('403.html'), 403

@main.app_errorhandler(404)
def page_not_found(e):
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        response = jsonify({'error': 'not found'})
        response.status_type = 404
        return response
    return render_template('404.html'), 404

@main.app_errorhandler(500)
def internal_server_error(e):
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        response = jsonify({'error': 'internal server error'})
        response.status_type = 500
        return response
    return render_template('500.html'), 500
