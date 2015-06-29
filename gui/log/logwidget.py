# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
"""
This file contains the QuDi log widget class.

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

Derived form ACQ4:
Copyright 2010  Luke Campagnola
Originally distributed under MIT/X11 license. See documentation/MITLicense.txt for more infomation.
"""

from PyQt4 import QtGui, QtCore
from gui.log import ui_logwidget
from pyqtgraph import FeedbackButton
import pyqtgraph.configfile as configfile
from core.util.mutex import Mutex
import numpy as np
from pyqtgraph import FileDialog
import weakref
import re

class LogModel(QtCore.QAbstractTableModel):

    def __init__(self):
        super().__init__()
        self.header = ['Id', 'Time', 'Type', '!', 'Message']
        self.fgColor = {
            'user':     QtGui.QColor('#F1F'),
            'thread':   QtGui.QColor('#11F'),
            'status':   QtGui.QColor('#1F1'),
            'warning':  QtGui.QColor('#F90'),
            'error':    QtGui.QColor('#F11')
        }
        self.entries = list()

    def rowCount(self, parent = QtCore.QModelIndex()):
        return len(self.entries)

    def columnCount(self, parent = QtCore.QModelIndex()):
        return len(self.header)

    def data(self, index,  role):
        if not index.isValid():
            return None
        elif role == QtCore.Qt.TextColorRole:
            return self.fgColor[self.entries[index.row()][2]]
        elif role == QtCore.Qt.DisplayRole:
            return self.entries[index.row()][index.column()]
        else:
            return None

    def setData(self, index, value, role = QtCore.Qt.EditRole):
        try:
            self.entries[index.row()] = value
        except Exception as e:
            print(e)
            return False
        topleft = self.createIndex(index.row(), 0)
        bottomright = self.createIndex(index.row(), 4)
        self.dataChanged.emit(topleft, bottomright)
        return True

    def headerData(self, section, orientation, role = QtCore.Qt.DisplayRole):
        if section < 0 and section > 3:
            return None
        elif role != QtCore.Qt.DisplayRole:
            return None
        elif orientation != QtCore.Qt.Horizontal:
            return None
        else:
            return self.header[section]

    def insertRows(self, row, count, parent = QtCore.QModelIndex()):
        self.beginInsertRows(parent, row, row + count - 1)
        insertion = list()
        for i in range(count):
            insertion.append([None, None, None, None, None])
        self.entries[row:row] = insertion
        self.endInsertRows()
        return True
        
    def addRow(self, row, data, parent = QtCore.QModelIndex()):
        return self.addRows(row, [data], parent)

    def addRows(self, row, data, parent = QtCore.QModelIndex()):
        count = len(data)
        self.beginInsertRows(parent, row, row + count - 1)
        self.entries[row:row] = data
        self.endInsertRows()
        topleft = self.createIndex(row, 0)
        bottomright = self.createIndex(row, 4)
        self.dataChanged.emit(topleft, bottomright)
        return True

    def removeRows(self, row, count, parent = QtCore.QModelIndex() ): 
        self.beginRemoveRows(parent, row, row + count - 1)
        self.entries[row:row+count] = []
        self.endRemoveRows()
        return True

class LogFilter(QtGui.QSortFilterProxyModel):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.minImportance = 5
        self.showTypes = ['user', 'thread', 'status', 'warning', 'error']

    def filterAcceptsRow(self, sourceRow, sourceParent):
        indexMessageType = self.sourceModel().index(sourceRow, 2)
        messageType = self.sourceModel().data(indexMessageType, QtCore.Qt.DisplayRole)
        indexMessageImportance = self.sourceModel().index(sourceRow, 3)
        messageImportance = self.sourceModel().data(indexMessageImportance, QtCore.Qt.DisplayRole)
        if messageImportance is None or messageType is None:
            return False
        return int(messageImportance) >= self.minImportance and messageType in self.showTypes

    def lessThan(self, left, right):
        leftData = self.sourceModel().data(self.sourceModel().index(left.row(), 0), QtCore.Qt.DisplayRole)
        rightData = self.sourceModel().data(self.sourceModel().index(right.row(), 0), QtCore.Qt.DisplayRole)
        return leftData < rightData

    def setImportance(self, minImportance):
        if minImportance >= 0 and minImportance <= 9:
            self.minImportance = minImportance
            self.invalidateFilter()

    def setTypes(self, showTypes):
        self.showTypes = showTypes
        self.invalidateFilter()

class HTMLDelegate(QtGui.QStyledItemDelegate):
    """
    """
    doc = QtGui.QTextDocument()

    def paint(self, painter, option, index):
        options = QtGui.QStyleOptionViewItemV4(option)
        self.initStyleOption(options,index)
        style = QtGui.QApplication.style() if options.widget is None else options.widget.style()
        self.doc.setHtml(options.text)
        options.text = ""
        style.drawControl(QtGui.QStyle.CE_ItemViewItem, options, painter);
        ctx = QtGui.QAbstractTextDocumentLayout.PaintContext()
        # Highlighting text if item is selected
        #if (optionV4.state & QStyle::State_Selected)
            #ctx.palette.setColor(QPalette::Text, optionV4.palette.color(QPalette::Active, QPalette::HighlightedText));
        textRect = style.subElementRect(QtGui.QStyle.SE_ItemViewItemText, options)
        painter.save()
        painter.translate(textRect.topLeft())
        painter.setClipRect(textRect.translated(-textRect.topLeft()))
        self.doc.documentLayout().draw(painter, ctx)
        painter.restore()

    def sizeHint(self, option, index):
        options = QtGui.QStyleOptionViewItemV4(option)
        self.initStyleOption(options,index)
        self.doc.setHtml(options.text)
        self.doc.setTextWidth(options.rect.width())
        return QtCore.QSize(self.doc.idealWidth(), self.doc.size().height())

    def setStylesheet(self, stylesheet):
        self.doc.setDefaultStyleSheet(stylesheet)

class LogWidget(QtGui.QWidget):
    """A widget to show log entries and filter them.
    """
    sigDisplayEntry = QtCore.Signal(object) ## for thread-safetyness
    sigAddEntry = QtCore.Signal(object) ## for thread-safetyness
    sigScrollToAnchor = QtCore.Signal(object)  # for internal use.

    def __init__(self, logStyleSheet):
        """Creates the log widget.

        @param object parent: Qt parent object for log widet
        @param str logStyleSheet: stylesheet for log view

        """
        super().__init__()
        self.ui = ui_logwidget.Ui_Form()
        self.ui.setupUi(self)

        self.logLength = 1000
        self.stylesheet = logStyleSheet

        self.model = LogModel()
        self.filtermodel = LogFilter()
        self.filtermodel.setSourceModel(self.model)
        self.idg = HTMLDelegate()
        self.idg.setStylesheet(self.stylesheet)
        #self.ui.output.setItemDelegate(HTMLDelegate())
        self.ui.output.setModel(self.filtermodel)
        self.ui.output.horizontalHeader().setResizeMode(0, QtGui.QHeaderView.ResizeToContents)
        self.ui.output.horizontalHeader().setResizeMode(1, QtGui.QHeaderView.ResizeToContents)
        self.ui.output.horizontalHeader().setResizeMode(2, QtGui.QHeaderView.ResizeToContents)
        self.ui.output.horizontalHeader().setResizeMode(3, QtGui.QHeaderView.ResizeToContents)
        self.ui.output.horizontalHeader().setResizeMode(4, QtGui.QHeaderView.Stretch)
        self.ui.output.verticalHeader().hide()
        

        self.sigDisplayEntry.connect(self.displayEntry, QtCore.Qt.QueuedConnection)
        self.sigAddEntry.connect(self.addEntry, QtCore.Qt.QueuedConnection)
        self.ui.filterTree.itemChanged.connect(self.setCheckStates)
        self.ui.importanceSlider.valueChanged.connect(self.filtersChanged)
        #self.ui.output.anchorClicked.connect(self.linkClicked)
        
        self.sigScrollToAnchor.connect(self.scrollToAnchor, QtCore.Qt.QueuedConnection)
        
        
    def loadFile(self, f):
        """Load a log file for display.

          @param str f: path to file that should be laoded.

        f must be able to be read by pyqtgraph configfile.py
        """
        pass
        
    def addEntry(self, entry):
        """Add a log entry to the log view.
          
          @param dict entry: log entry in dict format
        """
        ## All incoming messages begin here
        ## for thread-safetyness:
        isGuiThread = QtCore.QThread.currentThread() == QtCore.QCoreApplication.instance().thread()
        if not isGuiThread:
            self.sigAddEntry.emit(entry)
            return
        if self.model.rowCount() > self.logLength:
            self.model.removeRows(0, self.model.rowCount() - self.logLength)
        logEntry = [ entry['id'], entry['timestamp'], entry['msgType'], entry['importance'], entry['message'] ]
        self.model.addRow(self.model.rowCount(), logEntry)
        
    def displayEntry(self, entry):
        self.ui.output.scrollTo(self.model.index(entry, 0))

    def setLogLength(self, length):
        if length > 0:
            self.logLength = length

    def setCheckStates(self, item, column):
        """ Set state of the checkbox in the filter list and update log view.

          @param int item: Item number
          @param int column: Column number
        """
        if item == self.ui.filterTree.topLevelItem(1):
            if item.checkState(0):
                for i in range(item.childCount()):
                    item.child(i).setCheckState(0, QtCore.Qt.Checked)
        elif item.parent() == self.ui.filterTree.topLevelItem(1):
            if not item.checkState(0):
                self.ui.filterTree.topLevelItem(1).setCheckState(0, QtCore.Qt.Unchecked)

        typeFilter = []
        for i in range(self.ui.filterTree.topLevelItem(1).childCount()):
            child = self.ui.filterTree.topLevelItem(1).child(i)
            if self.ui.filterTree.topLevelItem(1).checkState(0) or child.checkState(0):
                text = child.text(0)
                typeFilter.append(str(text))
        print(typeFilter)
        self.filtermodel.setTypes(typeFilter)
        
    def filtersChanged(self):
        """ This function is called to update the filter list when the log filters have been changed.
        """
        self.filtermodel.setImportance(self.ui.importanceSlider.value())
        
    def scrollToAnchor(self, anchor):
        """ Scroll the log view so the specified element is visible.
        
          @param object anchor: element that should be visible
        """
        pass
                
    def generateEntryHtml(self, entry):
        """ Build a HTML string from a log message dictionary.

          @param dict entry: log entry in dictionary form

          @return str: HTML string containing the formatted log message from the dictionary
        """
        msg = self.cleanText(entry['message'])
        
        reasons = ""
        docs = ""
        exc = ""
        if 'reasons' in entry:
            reasons = self.formatReasonStrForHTML(entry['reasons'])
        if 'docs' in entry:
            docs = self.formatDocsStrForHTML(entry['docs'])
        if entry.get('exception', None) is not None:
            exc = self.formatExceptionForHTML(entry, entryId=entry['id'])
            
        extra = reasons + docs + exc
        if extra != "":
            #extra = "<div class='logExtra'>" + extra + "</div>"
            extra = "<table class='logExtra'><tr><td>" + extra + "</td></tr></table>"
        return """
        <a name="%s"/><table class='entry'><tr><td>
            <table class='%s'><tr><td>
                <span class='timestamp'>%s</span>
                <span class='message'>%s</span>
                %s
            </td></tr></table>
        </td></tr></table>
        """ % (str(entry['id']), entry['msgType'], entry['timestamp'], msg, extra)
        
    @staticmethod
    def cleanText(text):
        """ Escape special characters for HTML.

          @param str text: string with special characters to be escaped

          @return str: string where special characters have been replaced by theit HTML sequences

          FIXME: there is probably a pre-defined metod for this, use it!
        """
        text = re.sub(r'&', '&amp;', text)
        text = re.sub(r'>','&gt;', text)
        text = re.sub(r'<', '&lt;', text)
        text = re.sub(r'\n', '<br/>\n', text)
        return text
    
    def formatExceptionForHTML(self, entry, exception=None, count=1, entryId=None):
        """ Format exception with backtrsce in HTML.
          @param dict entrs: log entry in dictionary form
          @param Exception exception: Python exception object
          @param int count: recursion counter for recursive backtrace parsing
          @param int entryId: ID number of the log entry that this exception belongs to

          @return (str, str, str): HTML formatted exception and backtrace

          Here, exception is a dict that holds the message, reasons, docs, traceback and oldExceptions (which are also dicts, with the same entries)
          the count and tracebacks keywords are for calling recursively
        """
        if exception is None:
            exception = entry['exception']
            
        indent = 10
        
        text = self.cleanText(exception['message'])
        text = re.sub(r'^HelpfulException: ', '', text)
        messages = [text]
        
        if 'reasons' in exception:
            reasons = self.formatReasonsStrForHTML(exception['reasons'])
            text += reasons
        if 'docs' in exception:
            docs = self.formatDocsStrForHTML(exception['docs'])
            text += docs
        
        traceback = [self.formatTracebackForHTML(exception['traceback'], count)]
        text = [text]
        
        if 'oldExc' in exception:
            exc, tb, msgs = self.formatExceptionForHTML(entry, exception['oldExc'], count=count+1)
            text.extend(exc)
            messages.extend(msgs)
            traceback.extend(tb)
        if count == 1:
            exc = "<div class=\"exception\"><ol>" + "\n".join(["<li>%s</li>" % ex for ex in text]) + "</ol></div>"
            tbStr = "\n".join(["<li><b>%s</b><br/><span class='traceback'>%s</span></li>" % (messages[i], tb) for i,tb in enumerate(traceback)])
            entry['tracebackHtml'] = tbStr
            return exc + '<a href="exc:%s">Show traceback %s</a>'%(str(entryId), str(entryId))
        else:
            return text, traceback, messages
        
        
    def formatTracebackForHTML(self, tb, number):
        """ Convert a traceback object to HTML for display.

          @param list tb: traceback as a list of strings
          @param number: FIXME: unused?

          @return str: HTML string containing the traceback
        """
        try:
            tb = [line for line in tb if not line.startswith("Traceback (most recent call last)")]
        except:
            print("\n"+str(tb)+"\n")
            raise
        return re.sub(" ", "&nbsp;", ("").join(map(self.cleanText, tb)))[:-1]
        
    def formatReasonsStrForHTML(self, reasons):
        """ Format an exception reason list as HTML.
        
          @param list(str) reasons: exception reasosn list

          @return str: HTML formatted string with reasons
        """
        reasonStr = "<table class='reasons'><tr><td>Possible reasons include:\n<ul>\n"
        for r in reasons:
            r = self.cleanText(r)
            reasonStr += "<li>" + r + "</li>\n"
        reasonStr += "</ul></td></tr></table>\n"
        return reasonStr
    
    def formatDocsStrForHTML(self, docs):
        """ Format a doc string list as links in HTML.

          @param docs: list of documentation urls

          @return str: documenation strings as links in HTML  format
        """ 
        #indent = 6
        docStr = "<div class='docRefs'>Relevant documentation:\n<ul>\n"
        for d in docs:
            d = self.cleanText(d)
            docStr += "<li><a href=\"doc:%s\">%s</a></li>\n" % (d, d)
        docStr += "</ul></div>\n"
        return docStr
    
    def exportHtml(self, fileName=False):
        """ Export visible log entries to a file as HTML.

          @param str fileName: name of file to save HTML in

          If no fileName is given, this opens a file dialog and asks for a location to save.
        """
        if fileName is False:
            self.fileDialog = FileDialog(self, "Save HTML as...", "htmltemp.log")
            self.fileDialog.setAcceptMode(QtGui.QFileDialog.AcceptSave)
            self.fileDialog.show()
            self.fileDialog.fileSelected.connect(self.exportHtml)
            return
        if fileName[-5:] != '.html':
            fileName += '.html'
        doc = self.pageTemplate
        for e in self.displayedEntries:
            doc += self.cache[id(e)]
        for e in self.displayedEntries:
            if 'tracebackHtml' in e:
                doc = re.sub(r'<a href="exc:%s">(<[^>]+>)*Show traceback %s(<[^>]+>)*</a>'%(str(e['id']), str(e['id'])), e['tracebackHtml'], doc)
        f = open(fileName, 'w')
        f.write(doc)
        f.close()
        
    def linkClicked(self, url):
        """ This function is called when a link in the log view is clicked to expand the text or show documentation.
        """
        url = url.toString()

