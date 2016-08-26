# -*- coding: utf-8 -*-
"""
This file contains a webview for ipython notebooks.

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

import os
from qtpy import QtCore
from qtpy import QtWidgets
from qtpy import uic
from qtpy import QtWebEngineWidgets

from gui.guibase import GUIBase


class NotebookWebView(GUIBase):

    _modclass = 'NotebookWebView'
    _modtype = 'gui'
    ## declare connectors
    _in = {'notebooklogic': 'NotebookLogic'}

    def on_activate(self, e):
        """ Initializes all needed UI files and establishes the connectors.

        @param object e: Fysom.event object from Fysom class.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look in
                         the Base Class). This object contains the passed event,
                         the state before the event happened and the destination
                         of the state which should be reached after the event
                         had happened.
        """

        self._mw = NotebookMainWindow()
        url = QtCore.QUrl('http://localhost:8888')
        tw = self._mw.newTab()
        tw.load(url)
        self.restoreWindowPos(self._mw)
        self._mw.show()

    def on_deactivate(self, e):
        """ Deactivate the module properly.

        @param object e: Fysom.event object from Fysom class. A more detailed
                         explanation can be found in the method activation.
        """
        self.saveWindowPos(self._mw)
        self._mw.close()

    def show(self):
        self._mw.show()

class NotebookMainWindow(QtWidgets.QMainWindow):
    """ Helper class for window loaded from UI file.
    """
    def __init__(self):
        """ Create the switch GUI window.
        """
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_notebook.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)

        self.tabWidget.setTabsClosable(True)
        self.tabWidget.tabCloseRequested.connect(self.closeTab)
        self.tabWidget.currentChanged.connect(lambda index: self.setWindowTitle(self.tabWidget.tabText(index)))

    def newTab(self):
        tw = TabbedWebView(tabmanager=self)
        tabindex = self.tabWidget.addTab(tw, 'New')
        tw.titleChanged.connect(lambda title: self.tabWidget.setTabText(tabindex, 'qudi Notebook: ' + title))
        return tw

    def closeTab(self, index):
        if index > 0:
            self.tabWidget.removeTab(index)

class TabbedWebView(QtWebEngineWidgets.QWebEngineView):

    def __init__(self, parent=None, tabmanager=None):
        super().__init__(parent)
        self.tPage = TabbedWebPage(self)
        self.setPage(self.tPage)
        self.tm = tabmanager

    def createWindow(self, windowType):
        if self.tm is not None and windowType == QtWebEngineWidgets.QWebEnginePage.WebBrowserWindow:
            self.webView = self.tm.newTab()
            self.webView.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
            return self.webView

        return super().createWindow(windowType)

class TabbedWebPage(QtWebEngineWidgets.QWebEnginePage):

    def __init__(self, parent=None):
        super().__init__(parent)

    def triggerAction(self, action, checked=False):
        if action == QtWebEngineWidgets.QWebEnginePage.OpenLinkInNewWindow:
            self.createWindow(QtWebEngineWidgets.QWebEnginePage.WebBrowserWindow)

        return super().triggerAction(action, checked)

