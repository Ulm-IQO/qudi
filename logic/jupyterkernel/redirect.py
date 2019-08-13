# -*- coding: utf-8 -*-
"""
"""

import sys


class _RedirectStream:
    """ A base class for a context manager to redirect streams from the sys module."""
    _stream = None

    def __init__(self, new_target=None):
        self._new_target = new_target
        # We use a list of old targets to make this CM re-entrant
        self._old_targets = []

    def open(self, new_target):
        self._new_target = new_target
        self._old_targets.append(getattr(sys, self._stream))
        setattr(sys, self._stream, self._new_target)
        return self._new_target

    def close(self):
        if len(self._old_targets) > 0:
            setattr(sys, self._stream, self._old_targets.pop())
            self._new_target.close()
        return getattr(sys, self._stream)

    def __enter__(self):
        if self._new_target is None:
            return getattr(sys, self._stream)
        return self.open(self._new_target)

    def __exit__(self, exctype, excinst, exctb):
        self.close()


class RedirectedStdOut(_RedirectStream):
    """Context manager for temporarily redirecting stdout to another file."""
    _stream = "stdout"


class RedirectedStdErr(_RedirectStream):
    """Context manager for temporarily redirecting stderr to another file."""
    _stream = "stderr"
