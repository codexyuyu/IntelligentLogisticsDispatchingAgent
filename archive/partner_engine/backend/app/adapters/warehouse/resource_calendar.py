"""Owner: AC | Status: scaffold; shared resource occupancy and seven-day booking.
TODO[AC]: initial inventory occupancy, maintenance, capacity and explicit cleaning jobs.
NoOverlap alone does not create sequence-dependent setup time.
"""
from app.common.errors import FeatureNotImplemented


def build_resource_calendar():
    raise FeatureNotImplemented('warehouse.resource_calendar', 'AC')
