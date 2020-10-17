import os
from app import create_app, db
from app.models import User, Role, Permission
from flask_migrate import Migrate  # Flask wrapper for Alembic which is a schema version control for databases

app = create_app(os.getenv('FLASK_CONFIG_TYPE') or 'default')
migrate = Migrate(app, db)  # Initialising Migration

# To make some functions already imported using '$ flask shell'
@app.shell_context_processor
def make_shell_context():
    return dict(db=db, User=User, Role=Role, Permission=Permission)

@app.cli.command()
def test():
    '''Run the test. The function name is used as the command. 'test' in this case.'''
    import unittest
    tests = unittest.TestLoader().discover('tests')   # Automatically searches for tests. but an empty __init__.py is needed
    unittest.TextTestRunner(verbosity=2).run(tests)   # Runs it twice

'''
Dont forget to set $ export FLASK_APP=<main_script_name>.py if name is not app.py

REQUIREMENTS.TXT
(venv) $ pip freeze > requirements.txt  - to make file
(venv) $ pip install -r requirements.txt  - to install

MIGRATE DATABASE
$ flask db init - to make a migration repo
$ flask db migrate -m "message" - make changes to db
$ flask db upgrade - add changes
$ flask db downgrade - go back to prev (could loose data)
'''
