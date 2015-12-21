
from pyqtgraph.Qt import QtCore, QtGui, uic
from PyQt4 import QtWebKit
from gui.guibase import GUIBase
import os

class NotebookWebView(GUIBase):

    _modclass = 'NotebookWebView'
    _modtype = 'gui'
    ## declare connectors
    _in = {'notebooklogic': 'NotebookLogic'}

    def __init__(self, manager, name, config, **kwargs):
        """Create an instance of the module.

          @param object manager:
          @param str name:
          @param dict config:
        """
        c_dict = {'onactivate': self.activation, 'ondeactivate': self.deactivation}
        super().__init__(manager, name, config, c_dict)

    def activation(self, e):
        self._mw = NotebookMainWindow()
        url = QtCore.QUrl('http://localhost:8888')
        tw = self._mw.newTab()
        tw.load(url)
        self.restoreWindowPos(self._mw)
        self._mw.show()

    def deactivation(self, e):
        self.saveWindowPos(self._mw)
        self._mw.close()

    def show(self):
        self._mw.show()

class NotebookMainWindow(QtGui.QMainWindow):
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

    def newTab(self):
        tw = TabbedWebView(tabmanager=self)
        tabindex = self.tabWidget.addTab(tw, 'New')
        tw.titleChanged.connect(lambda title: self.tabWidget.setTabText(tabindex, 'qudi Notebook: ' + title))
        return tw

class TabbedWebView(QtWebKit.QWebView):

    def __init__(self, parent=None, tabmanager=None):
        super().__init__(parent)
        self.tPage = TabbedWebPage(self)
        self.setPage(self.tPage)
        self.tm = tabmanager

    def createWindow(self, windowType):
        if self.tm is not None and windowType == QtWebKit.QWebPage.WebBrowserWindow:
            self.webView = self.tm.newTab()
            self.webView.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
            return self.webView

        return super().createWindow(windowType)

class TabbedWebPage(QtWebKit.QWebPage):

    def __init__(self, parent=None):
        super().__init__(parent)

    def triggerAction(self, action, checked=False):
        if action == QtWebKit.QWebPage.OpenLinkInNewWindow:
            self.createWindow(QtWebKit.QWebPage.WebBrowserWindow)

        return super().triggerAction(action, checked)

