# -*- coding: utf-8 -*-
"""
This file contains the qudi main window for the QD Plot GUI module.

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

__all__ = ('QDPlotMainWindow',)

import os
from PySide2 import QtCore, QtWidgets, QtGui

from qudi.core.paths import get_artwork_dir


class QDPlotMainWindow(QtWidgets.QMainWindow):
    """ The main window for the QD Plot GUI
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setWindowTitle('qudi: QD Plotter')

        self.setTabPosition(QtCore.Qt.TopDockWidgetArea, QtWidgets.QTabWidget.North)
        self.setTabPosition(QtCore.Qt.BottomDockWidgetArea, QtWidgets.QTabWidget.North)
        self.setTabPosition(QtCore.Qt.LeftDockWidgetArea, QtWidgets.QTabWidget.North)
        self.setTabPosition(QtCore.Qt.RightDockWidgetArea, QtWidgets.QTabWidget.North)

        self.resize(900, 600)

        # Create QActions
        icon_path = os.path.join(get_artwork_dir(), 'icons')

        icon = QtGui.QIcon(os.path.join(icon_path, 'oxygen', '22x22', 'application-exit.png'))
        self.action_close = QtWidgets.QAction('Close')
        self.action_close.setIcon(icon)

        icon = QtGui.QIcon(os.path.join(icon_path, 'oxygen', '22x22', 'document-save.png'))
        self.action_save_all = QtWidgets.QAction('Save All')
        self.action_save_all.setToolTip('Save all available plots, each in their own file.')
        self.action_save_all.setIcon(icon)

        icon = QtGui.QIcon(os.path.join(icon_path, 'oxygen', '22x22', 'configure.png'))
        self.action_show_fit_configuration = QtWidgets.QAction('Fit Configuration')
        self.action_show_fit_configuration.setToolTip('Open a dialog to edit data fitting configurations.')
        self.action_show_fit_configuration.setIcon(icon)

        icon = QtGui.QIcon(os.path.join(icon_path, 'oxygen', '22x22', 'document-new.png'))
        self.action_new_plot = QtWidgets.QAction('New Plot')
        self.action_new_plot.setToolTip('Adds another DockWidget for a new Plot.')
        self.action_new_plot.setIcon(icon)

        icon = QtGui.QIcon(os.path.join(icon_path, 'oxygen', '22x22', 'zoom-fit-best.png'))
        self.action_restore_tabbed_view = QtWidgets.QAction('Restore tabbed view')
        self.action_restore_tabbed_view.setToolTip('Restore the tabbed view of the DockWidgets for the plots.')
        self.action_restore_tabbed_view.setIcon(icon)

        self.action_restore_side_by_side_view = QtWidgets.QAction('Restore side by side view')
        self.action_restore_side_by_side_view.setToolTip('Restore the side by side of the DockWidgets for the plots.')
        self.action_restore_side_by_side_view.setIcon(icon)

        self.action_restore_arced_view = QtWidgets.QAction('Restore arced view')
        self.action_restore_arced_view.setToolTip('Restore the arced view of the DockWidgets for the plots.')
        self.action_restore_arced_view.setIcon(icon)

        # Create menu bar and add actions
        menu_bar = QtWidgets.QMenuBar()
        menu = menu_bar.addMenu('File')
        menu.addAction(self.action_new_plot)
        menu.addSeparator()
        menu.addAction(self.action_save_all)
        menu.addSeparator()
        menu.addAction(self.action_close)

        menu = menu_bar.addMenu('View')
        menu.addAction(self.action_show_fit_configuration)
        menu.addSeparator()
        menu.addAction(self.action_restore_tabbed_view)
        menu.addAction(self.action_restore_side_by_side_view)
        menu.addAction(self.action_restore_arced_view)

        self.setMenuBar(menu_bar)

        # Connect close actions
        self.action_close.triggered.connect(self.close)
