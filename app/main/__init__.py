# Since the ../../__init__.py constructor was used for delaying configuration
# view functions and error handellers cannot be written
# so 'Blueprint' is used , it acts dormant till the 'app' is registered.
# Hence, this constructor.
from flask import Blueprint

main = Blueprint('main', __name__)  # args: blueprint_name, module_or_package_location

from . import views, errors  # This should be imported last to not cause errors due to circular dependencies.
from ..models import Permission


# To access Permissions from template without having to send Permission each time.
@main.app_context_processor
def inject_permissions():
    return dict(Permission=Permission)
