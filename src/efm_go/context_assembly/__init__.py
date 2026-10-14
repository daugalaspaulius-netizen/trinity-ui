"""Owners composed by :mod:`efm_go.context`.

``efm_go.context`` stays the import path every caller uses; it imports each
module here when it loads and re-binds their names. This package imports nothing,
so loading it never loads an owner on its own.
"""
