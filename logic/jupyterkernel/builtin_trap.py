# -*- coding: utf-8 -*-
""" A context manager for managing things injected into __builtin__.

Qudi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Qudi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Qudi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

#-----------------------------------------------------------------------------
#  Authors:
#
#  * Brian Granger
#  * Fernando Perez
#
#  Copyright (C) 2010-2011  The IPython Development Team.
#
#  Distributed under the terms of the BSD License.
#
#  Complete license in the file documentation/BSDLicense_IPython.md,
#  distributed with this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

import builtins as builtin_mod

#-----------------------------------------------------------------------------
# Classes and functions
#-----------------------------------------------------------------------------

class __BuiltinUndefined: pass
BuiltinUndefined = __BuiltinUndefined()

class __HideBuiltin: pass
HideBuiltin = __HideBuiltin()


class BuiltinTrap:
    """ Protect builtins from code in some environment. """
    def __init__(self):
        self._orig_builtins = {}
        # We define this to track if a single BuiltinTrap is nested.
        # Only turn off the trap when the outermost call to __exit__ is made.
        self._nested_level = 0
        # builtins we always add - if set to HideBuiltin, they will just
        # be removed instead of being replaced by something else
        self.auto_builtins = {'exit': HideBuiltin,
                              'quit': HideBuiltin,
                              }
    def __enter__(self):
        """ Enter a code segment that should not chane builtins """
        if self._nested_level == 0:
            self.activate()
        self._nested_level += 1
        # I return self, so callers can use add_builtin in a with clause.
        return self

    def __exit__(self, type, value, traceback):
        """ Leave a code segment that should not change builtins
        
          @param type:
          @prarm value:
          @param traceback:
        """
        if self._nested_level == 1:
            self.deactivate()
        self._nested_level -= 1
        # Returning False will cause exceptions to propagate
        return False

    def add_builtin(self, key, value):
        """Add a builtin and save the original."""
        bdict = builtin_mod.__dict__
        orig = bdict.get(key, BuiltinUndefined)
        if value is HideBuiltin:
            if orig is not BuiltinUndefined: #same as 'key in bdict'
                self._orig_builtins[key] = orig
                del bdict[key]
        else:
            self._orig_builtins[key] = orig
            bdict[key] = value

    def remove_builtin(self, key, orig):
        """Remove an added builtin and re-set the original."""
        if orig is BuiltinUndefined:
            del builtin_mod.__dict__[key]
        else:
            builtin_mod.__dict__[key] = orig

    def activate(self):
        """Store ipython references in the __builtin__ namespace."""

        add_builtin = self.add_builtin
        for name, func in iter(self.auto_builtins.items()):
            add_builtin(name, func)

    def deactivate(self):
        """Remove any builtins which might have been added by add_builtins, or
        restore overwritten ones to their previous values."""
        remove_builtin = self.remove_builtin
        for key, val in iter(self._orig_builtins.items()):
            remove_builtin(key, val)
        self._orig_builtins.clear()
        self._builtins_added = False
