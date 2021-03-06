# python 2 backwards compatibility
from __future__ import print_function
from builtins import object, super
from future import standard_library
from six import string_types

from .base import ModelBase


class RequestQuota(ModelBase):
    """
    Models a request quota.

    :ivar guid: The GUID of the counter.
    :ivar max_requests: The maximum number of requests allowed during the time window.
    :ivar used_requests: The number of requests the user has used during the time window.
    :ivar time_window: The length of the time window in milliseconds.
    :ivar last_reset_time: The time that the counter was last reset, in milliseconds since epoch.
    :ivar next_reset_time: The time that the counter will next be reset, in milliseconds since epoch.
    """

    def __init__(self, guid, max_requests, used_requests, time_window, last_reset_time, next_reset_time):

        self.guid = guid
        self.max_requests = max_requests
        self.used_requests = used_requests
        self.time_window = time_window
        self.last_reset_time = last_reset_time
        self.next_reset_time = next_reset_time

    def to_dict(self, remove_nones=False):

        if remove_nones:
            return super().to_dict(remove_nones=True)

        d = {
            'guid': self.guid,
            'maxRequests': self.max_requests,
            'usedRequests': self.used_requests,
            'timeWindow': self.time_window,
            'lastResetTime': self.last_reset_time,
            'nextResetTime': self.next_reset_time
        }
        return d

    @classmethod
    def from_dict(cls, d):

        if d is None:
            return None

        return RequestQuota(guid=d.get('guid'),
                            max_requests=d.get('maxRequests'),
                            used_requests=d.get('usedRequests'),
                            time_window=d.get('timeWindow'),
                            last_reset_time=d.get('lastResetTime'),
                            next_reset_time=d.get('nextResetTime'))
