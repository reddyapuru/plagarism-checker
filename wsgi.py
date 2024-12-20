import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import app as application  # Ensure this points to the Flask app instance
