"""Shim package for ML modules used in tests.

The ``ml`` package resides next to the backend directory.  The tests
import ``ml.data_generator`` directly, so we make the ``ml`` directory a
Python package.
"""
