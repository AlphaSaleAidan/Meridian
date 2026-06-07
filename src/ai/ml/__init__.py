"""Wave 2+ ML model backends (masterplan).

Each module here is an *opt-in* upgrade over an incumbent statistical
path, selected by a ``MERIDIAN_*_BACKEND`` env var and lazy-imported so
the production Railway build (which does not install the heavy deps)
never breaks. Every helper returns ``None`` on any failure so the caller
falls back to the incumbent — default behaviour is byte-for-byte
unchanged until an operator opts in.
"""
