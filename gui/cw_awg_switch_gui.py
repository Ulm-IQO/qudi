# -*- coding: utf-8 -*-
"""
This file contains the Qudi GUI module base class.

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

from gui.guibase import GUIBase
from qtpy import QtWidgets, uic, QtCore
import os
from core.module import Connector


class CwAwgSwitchMainWindow(QtWidgets.QMainWindow):
    """
    Create the Main Window based on the *.ui file.
    """
    def __init__(self, **kwargs):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'switch_cwmw_awg.ui')

        # Load it
        super().__init__(**kwargs)
        uic.loadUi(ui_file, self)
        self.show()


class CwAwgSwitchGui(GUIBase):
    """
    """
    _modclass = 'CwAwgSwitchGui'
    _modtype = 'gui'

    # declare connectors
    cwawgswitchlogic = Connector(interface='CwAwgSwitchLogic')

    sigSelectionChanged = QtCore.Signal(bool)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        self._mw = CwAwgSwitchMainWindow()

        self.cwawgswitchlogic().sigSelectionUpdated.connect(self.update_switch_state,
                                                            QtCore.Qt.QueuedConnection)
        self.sigSelectionChanged.connect(self.cwawgswitchlogic().toggle_cw_awg,
                                         QtCore.Qt.QueuedConnection)
        self._mw.cw_pushButton.clicked.connect(self.select_cw, QtCore.Qt.QueuedConnection)
        self._mw.awg_pushButton.clicked.connect(self.select_awg, QtCore.Qt.QueuedConnection)
        self._mw.cw_awg_horizontalSlider.valueChanged.connect(self.slider_changed,
                                                              QtCore.Qt.QueuedConnection)
        self.show()

    def on_deactivate(self):
        self.sigSelectionChanged.disconnect()
        self.cwawgswitchlogic().sigSelectionUpdated.disconnect()

        self._mw.cw_awg_horizontalSlider.valueChanged.disconnect()
        self._mw.awg_pushButton.clicked.disconnect()
        self._mw.cw_pushButton.clicked.disconnect()

        self._mw.close()
        return

    def show(self):
        """Make window visible and put it above all other windows. """
        self._mw.show()
        self._mw.activateWindow()
        self._mw.raise_()

    def slider_changed(self, value):
        self.sigSelectionChanged.emit(not bool(value))
        return

    def select_cw(self):
        self.sigSelectionChanged.emit(True)
        return

    def select_awg(self):
        self.sigSelectionChanged.emit(False)
        return

    def update_switch_state(self, select_cw):
        if not isinstance(select_cw, bool):
            return

        self._mw.cw_pushButton.blockSignals(True)
        self._mw.awg_pushButton.blockSignals(True)
        self._mw.cw_awg_horizontalSlider.blockSignals(True)

        self._mw.cw_pushButton.setChecked(select_cw)
        self._mw.awg_pushButton.setChecked(not select_cw)
        self._mw.cw_awg_horizontalSlider.setValue(int(not select_cw))

        self._mw.cw_pushButton.blockSignals(False)
        self._mw.awg_pushButton.blockSignals(False)
        self._mw.cw_awg_horizontalSlider.blockSignals(False)
        return
