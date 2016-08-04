# -*- coding: utf-8 -*-
"""
A context manager for handling sys.displayhook.

QuDi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

QuDi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with QuDi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>

"""

#-----------------------------------------------------------------------------
#  Authors:
#
#  * Robert Kern
#  * Brian Granger
#  Copyright (C) 2008-2011  The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file documentation/BSDLicense_IPython.md, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

import sys

#-----------------------------------------------------------------------------
# Classes and functions
#-----------------------------------------------------------------------------


class DisplayTrap:
    """Object to manage sys.displayhook.

    This came from IPython.core.kernel.display_hook, but is simplified
    (no callbacks or formatters) until more of the core is refactored.
    """

    def __init__(self, hook=None):
        self.old_hook = None
        self.hook = hook
        # We define this to track if a single BuiltinTrap is nested.
        # Only turn off the trap when the outermost call to __exit__ is made.
        self._nested_level = 0

    def __enter__(self):
        """ Enter a code segment where displayhook is set.
        """
        if self._nested_level == 0:
            self.set()
        self._nested_level += 1
        return self

    def __exit__(self, type, value, traceback):
        """ Leave a code segmen swhere displayhook is unset.
        
          @param type:
          @param value:
          @param traceback:
        """
        if self._nested_level == 1:
            self.unset()
        self._nested_level -= 1
        # Returning False will cause exceptions to propagate
        return False

    def set(self):
        """Set the hook."""
        if self.hook is not None and sys.displayhook is not self.hook:
            self.old_hook = sys.displayhook
            sys.displayhook = self.hook

    def unset(self):
        """Unset the hook."""
        if self.hook is not None and sys.displayhook is not self.old_hook:
            sys.displayhook = self.old_hook

