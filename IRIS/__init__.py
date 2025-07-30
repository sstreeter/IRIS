# IRIS/__init__.py

# Expose MockAppInstance and Helpers directly when IRIS is imported
# This resolves the ImportError when other modules try to import them from IRIS.helpers
from .helpers import MockAppInstance, Helpers
