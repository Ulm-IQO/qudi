"""
This module provides an adapter around Fysom which can be used as a drop in
replacement but supports cooperative multiple inheritance.
"""

import fysom


class Fysom():
    """
    This provides an adapter class for fysom which makes it compatible with
    cooperative multiple inheritance.
    """
    def __init__(self, cfg=None, initial=None, events=None, callbacks=None,
            final=None, **kwargs):
        """
        Constructor. It creates the Fysom object.
        """
        if cfg is None:
            cfg = {}
        self._fysom = fysom.Fysom(cfg, initial, events, callbacks, final)
        super().__init__(**kwargs)

    def __getattr__(self, name):
        """
        This basically copies the attributes of Fysom. Note that Fysom
        makes use of dynamical attributes heavily. If the attribute is not
        found in the fysom object, AttributeError raised.

        @param name str: name of attribute
        """
        if hasattr(self._fysom, name):
            return getattr(self._fysom, name)
        else:
            raise AttributeError("'{}' object has no attribute '{}'".format(
                self.__class__, name))
