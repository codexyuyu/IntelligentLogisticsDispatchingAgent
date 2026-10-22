"""Owner: AC | Status: scaffold; after four-week fixed-origin MVP.
TODO[AC]: bounded warehouse candidates; explicit transfer legs and stock conservation.
Never enumerate 2**n assignments or change warehouse IDs without moving stock.
"""
from app.common.errors import FeatureNotImplemented


def select_warehouse_candidates():
    raise FeatureNotImplemented('warehouse_selection', 'AC')
