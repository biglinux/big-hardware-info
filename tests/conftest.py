import os, sys
# Ensure local src is first in sys.path so tests import the local package, not an installed one
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
