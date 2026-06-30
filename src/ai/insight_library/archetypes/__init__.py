"""Importing this package populates base.REGISTRY with every domain's archetypes.

Add one import line per domain module. Each module calls register(...) at import.
"""
from . import labor  # noqa: F401

# Fan-out domains are appended here as their modules land:
# from . import revenue, pricing, payments, products, inventory, timing, customer,
#               marketing, footfall, channel, fusion, risk, cashflow  # noqa
try:
    from . import revenue  # noqa: F401
except Exception:
    pass
try:
    from . import pricing  # noqa: F401
except Exception:
    pass
try:
    from . import payments  # noqa: F401
except Exception:
    pass
try:
    from . import products  # noqa: F401
except Exception:
    pass
try:
    from . import inventory  # noqa: F401
except Exception:
    pass
try:
    from . import timing  # noqa: F401
except Exception:
    pass
try:
    from . import customer  # noqa: F401
except Exception:
    pass
try:
    from . import marketing  # noqa: F401
except Exception:
    pass
try:
    from . import footfall  # noqa: F401
except Exception:
    pass
try:
    from . import channel  # noqa: F401
except Exception:
    pass
try:
    from . import fusion  # noqa: F401
except Exception:
    pass
try:
    from . import risk  # noqa: F401
except Exception:
    pass
try:
    from . import cashflow  # noqa: F401
except Exception:
    pass
try:
    from . import capacity  # noqa: F401
except Exception:
    pass
try:
    from . import experience  # noqa: F401
except Exception:
    pass
try:
    from . import growth  # noqa: F401
except Exception:
    pass
try:
    from . import localmarket  # noqa: F401
except Exception:
    pass
try:
    from . import digital  # noqa: F401
except Exception:
    pass

from .base import REGISTRY  # noqa: E402,F401
