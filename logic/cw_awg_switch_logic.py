# -*- coding: utf-8 -*-
"""
Simple switch logic to control switching of MW channels between CW source and AWG via TTL pulse.

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

from qtpy import QtCore
from logic.generic_logic import GenericLogic
from core.configoption import ConfigOption
from core.connector import Connector
from core.statusvariable import StatusVar


class CwAwgSwitchLogic(GenericLogic):
    """ Logic module for a single TTL switch
    """
    _modclass = 'cwawgswitchlogic'
    _modtype = 'logic'

    ttl_generator = Connector(interface='NationalInstrumentsXSeries')

    _cw_selected = StatusVar('cw_selected', True)
    _ttl_channel = ConfigOption('ttl_channel', missing='error')

    sigSelectionUpdated = QtCore.Signal(bool)

    def __init__(self, config, **kwargs):
        """ Create logic object

          @param dict config: configuration in a dict
          @param dict kwargs: additional parameters as a dict
        """
        super().__init__(config=config, **kwargs)
        return

    def on_activate(self):
        """ Prepare logic module for work.
        """
        self.ttl_generator().digital_channel_switch(self._ttl_channel, not self._cw_selected)
        return

    def on_deactivate(self):
        """ Deactivate module.
        """
        pass

    def toggle_cw_awg(self, use_cw=None):
        """

        @param use_cw:
        @return:
        """
        if use_cw is None or not isinstance(use_cw, bool):
            use_cw = not self._cw_selected

        self.ttl_generator().digital_channel_switch(self._ttl_channel, not use_cw)
        self._cw_selected = use_cw
        self.sigSelectionUpdated.emit(self._cw_selected)
        return
