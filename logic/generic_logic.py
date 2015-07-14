# -*- coding: utf-8 -*-
"""
This file contains the QuDi GUI module base class.

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

Copyright (C) 2015 Jan M. Binder jan.binder@uni-ulm.de
"""

from core.base import Base

class GenericLogic(Base):
    """A generic logic interface class.
    """
    _modclass = 'GenericLogic'
    _modtype = 'Logic'
    def __init__(self, manager, name, configuation, callbacks, **kwargs):
        """ Initialzize a logic module.

          @param object manager: Manager object that has instantiated this object
          @param str name: unique module name
          @param dict configuration: module configuration as a dict
          @param dict callbacks: dict of callback functions for Fysom state machine
          @param dict kwargs: dict of additional arguments
        """
        super().__init__(manager, name, configuation, callbacks, **kwargs)
        
    def getModuleThread(self):
        """ Get the thread associated to this module.

          @return QThread: thread with qt event loop associated with this module
        """
        return self._manager.tm._threads['mod-logic-' + self._name].thread
