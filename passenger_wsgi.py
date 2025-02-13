import os
import sys

# Add your application directory to Python path
VENV_PATH = os.path.join(os.getcwd(), "venv")
PYTHON_PATH = os.path.join(VENV_PATH, "lib", "python3.11", "site-packages")
INTERP = os.path.join(VENV_PATH, "bin", "python3")

if sys.executable != INTERP:
    os.execl(INTERP, INTERP, *sys.argv)

sys.path.insert(0, PYTHON_PATH)
sys.path.insert(0, os.getcwd())

# Set environment variable
os.environ["ENV"] = "production"

from src.main import app

# Create WSGI application
application = app 