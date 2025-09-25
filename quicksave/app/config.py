import os

# The absolute path to the root of the 'quicksave' project directory
# This assumes that the `quicksave` directory is a sub-directory of the project root.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# The absolute path to the database file
DB_PATH = os.path.join(PROJECT_ROOT, 'data', 'quicksave.db')

# The absolute path to the data directory
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')

# The absolute path to the templates directory
TEMPLATES_DIR = os.path.join(PROJECT_ROOT, 'app', 'templates')