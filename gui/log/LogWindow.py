# -*- coding: utf-8 -*-
import time
import traceback
import sys, os

if __name__ == "__main__":
    #import os.path as osp
    d = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path = [os.path.join(d,'lib','util')] + sys.path + [d]

from PyQt4 import QtGui, QtCore
from .LogWidget import LogWidget
from pyqtgraph import FeedbackButton
import pyqtgraph.configfile as configfile
from core.util.Mutex import Mutex
from core.Base import Base
import numpy as np
from pyqtgraph import FileDialog
import weakref
import re

class LogWindow(Base):
    """LogWindow contains a LogWidget inside a window. LogWindow is responsible for collecting messages generated by the program/user, formatting them into a nested dictionary,
    and saving them in a log.txt file. The LogWidget takes care of displaying messages.
    """
    
    def __init__(self, manager, name, config):
        """Create LogWindow Instance

          @param object manager: te manager instance thet this Log window belongs to
          @param str name: the unique name of this module
          @param dict config: configuration of this module in a dictionary

        """
        callback = {'onactivate': self.initUI}
        Base.__init__(self, manager, name, config, callback)
        self.buttons = [] ## weak references to all Log Buttons get added to this list, so it's easy to make them all do things, like flash red.
        self.lock = Mutex()
        
    def initUI(self, e=None):
        """Create the actual log window. Called only by state machine

        @param object e: state change object from fysom stae machine
        """
        self.mw = QtGui.QMainWindow()
        self.mw.setWindowTitle("Log")
        path = os.path.dirname(__file__)
        self.mw.setWindowIcon(QtGui.QIcon(os.path.join(path, 'logIcon.png')))
        self.wid = LogWidget(self.mw)
        self.wid.ui.input = QtGui.QLineEdit()
        self.wid.ui.gridLayout.addWidget(self.wid.ui.input, 2, 0, 1, 3)
        self.wid.ui.dirLabel.setText("Current Storage Directory: None")
        self.mw.setCentralWidget(self.wid)
        self.mw.setGeometry(7,630,1000, 500)
        self.wid.ui.input.returnPressed.connect(self.textEntered)
        self.errorDialog = ErrorDialog(self)
        self._manager.logger.sigLoggedMessage.connect(self.addMessage)
        self.mw.show()

    def addMessage(self, entry):
        """ Add message to log window.
          
          @param dict entry: the log entry to be added in dict format

          This function is called usually as a Qt slot from the Logger instance
          that is receiving and saving the log messages.
        """
        self.wid.addEntry(entry) ## takes care of displaying the entry if it passes the current filters on the logWidget
        if entry['msgType'] == 'error':
            if self.errorDialog.show(entry) is False:
                self.flashButtons()
        
    def textEntered(self):
        """Add string from entry field on LogWidget to log and clear the entry field.
          This is usually called as a Qt slot when text is entered in the log
          widget user text entry field.
        """
        msg = str(self.wid.ui.input.text())
        currentDir = None
        self.logMsg(msg, importance=8, msgType='user', currentDir=currentDir)
        self.wid.ui.input.clear()

    def flashButtons(self):
        """Flash buttons on error.
        """
        for b in self.buttons:
            if b() is not None:
                b().failure(tip='An error occurred. Please see the log.', limitedTime = False)
    
    def resetButtons(self):
        """Stop flashing buttons.
        """
        for b in self.buttons:
            if b() is not None:
                b().reset()
    
    def show(self):
        """Make log window visible and put it above all other windows.
        """
        QtGui.QMainWindow.show(self.mw)
        self.mw.activateWindow()
        self.mw.raise_()
        self.resetButtons()
    
    def disablePopups(self, disable):
        """ Do/ do not show popupas on error.

          @param bool disable: True disables popups, false enable popups.
        """
        self.errorDialog.disable(disable)
        
class ErrorDialog(QtGui.QDialog):
    """This class provides a popup window for notification with the option to
      show the next error popup in the queue and to show the log window where
      you can see the traceback for an exception.
    """
    def __init__(self, logWindow):
        QtGui.QDialog.__init__(self)
        self.logWindow = logWindow
        self.setWindowFlags(QtCore.Qt.Window)
        #self.setWindowModality(QtCore.Qt.NonModal)
        self.setWindowTitle('QuDi Error')
        wid = QtGui.QDesktopWidget()
        screenWidth = wid.screen(wid.primaryScreen()).width()
        screenHeight = wid.screen(wid.primaryScreen()).height()
        self.setGeometry((screenWidth-500)/2,(screenHeight-100)/2,500,100)
        self.layout = QtGui.QVBoxLayout()
        self.layout.setContentsMargins(3,3,3,3)
        self.setLayout(self.layout)
        self.messages = []
        
        self.msgLabel = QtGui.QLabel()
        #self.msgLabel.setWordWrap(False)
        #self.msgLabel.setMaximumWidth(800)
        self.msgLabel.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        #self.msgLabel.setFrameStyle(QtGui.QFrame.Box)
        #self.msgLabel.setStyleSheet('QLabel { font-weight: bold }')
        self.layout.addWidget(self.msgLabel)
        self.msgLabel.setMaximumWidth(800)
        self.msgLabel.setMinimumWidth(500)
        self.msgLabel.setWordWrap(True)
        self.layout.addStretch()
        self.disableCheck = QtGui.QCheckBox('Disable error message popups')
        self.layout.addWidget(self.disableCheck)
        
        self.btnLayout = QtGui.QHBoxLayout()
        self.btnLayout.addStretch()
        self.okBtn = QtGui.QPushButton('OK')
        self.btnLayout.addWidget(self.okBtn)
        self.nextBtn = QtGui.QPushButton('Show next error')
        self.btnLayout.addWidget(self.nextBtn)
        self.nextBtn.hide()
        self.logBtn = QtGui.QPushButton('Show Log...')
        self.btnLayout.addWidget(self.logBtn)
        self.btnLayoutWidget = QtGui.QWidget()
        self.layout.addWidget(self.btnLayoutWidget)
        self.btnLayoutWidget.setLayout(self.btnLayout)
        self.btnLayout.addStretch()
        
        self.okBtn.clicked.connect(self.okClicked)
        self.nextBtn.clicked.connect(self.nextMessage)
        self.logBtn.clicked.connect(self.logClicked)
        
        
    def show(self, entry):
        ## rules are:
        ##   - Try to show friendly error messages
        ##   - If there are any helpfulExceptions, ONLY show those
        ##     otherwise, show everything
        self.lastEntry = entry
        
        ## extract list of exceptions
        exceptions = []
        #helpful = []
        key = 'exception'
        exc = entry
        while key in exc:
            exc = exc[key]
            if exc is None:
                break
            ## ignore this error if it was generated on the command line.
            tb = exc.get('traceback', ['',''])
            if len(tb) > 1 and 'File "<stdin>"' in tb[1]:
                return False
            
            if exc is None:
                break
            key = 'oldExc'
            if exc['message'].startswith('HelpfulException'):
                exceptions.append('<b>' + self.cleanText(re.sub(r'^HelpfulException: ', '', exc['message'])) + '</b>')
            elif exc['message'] == 'None':
                continue
            else:
                exceptions.append(self.cleanText(exc['message']))
                
        msg = '<b>' + entry['message'] + '</b><br>' + '<br>'.join(exceptions)
        
        if self.disableCheck.isChecked():
            return False
        if self.isVisible():
            self.messages.append(msg)
            self.nextBtn.show()
            self.nextBtn.setEnabled(True)
            self.nextBtn.setText('Show next error (%d more)' % len(self.messages))
        else:
            w = QtGui.QApplication.activeWindow()
            self.nextBtn.hide()
            self.msgLabel.setText(msg)
            self.open()
            if w is not None:
                cp = w.geometry().center()
                self.setGeometry(cp.x() - self.width()/2., cp.y() - self.height()/2., self.width(), self.height())
        #self.activateWindow()
        self.raise_()
            
    @staticmethod
    def cleanText(text):
        text = re.sub(r'&', '&amp;', text)
        text = re.sub(r'>','&gt;', text)
        text = re.sub(r'<', '&lt;', text)
        text = re.sub(r'\n', '<br/>\n', text)
        return text
        
    def closeEvent(self, ev):
        QtGui.QDialog.closeEvent(self, ev)
        self.messages = []
        
    def okClicked(self):
        self.accept()
        self.messages = []
        
    def logClicked(self):
        self.accept()
        self.logWindow.show()
        self.messages = []
        
    def nextMessage(self):
        self.msgLabel.setText(self.messages.pop(0))
        self.nextBtn.setText('Show next error (%d more)' % len(self.messages))
        if len(self.messages) == 0:
            self.nextBtn.setEnabled(False)
        
    def disable(self, disable):
        self.disableCheck.setChecked(disable)
    
    
if __name__ == "__main__":
    #import sys
    #import os.path as osp
    #d = osp.dirname(osp.dirname(osp.abspath(__file__)))
    #sys.path = [osp.join(d, 'util')] + sys.path + [d]
    #from acq4.util import acq4.pyqtgraph
    app = QtGui.QApplication([])
    log = LogWindow(None)
    log.show()
    original_excepthook = sys.excepthook
    
    def excepthook(*args):
        global original_excepthook
        log.displayException(*args)
        ret = original_excepthook(*args)
        sys.last_traceback = None           ## the important bit
        
    
    sys.excepthook = excepthook

    app.exec_()
