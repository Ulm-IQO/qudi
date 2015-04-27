# -*- coding: utf-8 -*-
from PyQt4 import QtGui, QtCore
from . import LogWidgetTemplate
from pyqtgraph import FeedbackButton
import pyqtgraph.configfile as configfile
from core.util.Mutex import Mutex
import numpy as np
from pyqtgraph import FileDialog
import weakref
import re


class LogWidget(QtGui.QWidget):
    """A widget to show log entries and filter them.
    """
    
    sigDisplayEntry = QtCore.Signal(object) ## for thread-safetyness
    sigAddEntry = QtCore.Signal(object) ## for thread-safetyness
    sigScrollToAnchor = QtCore.Signal(object)  # for internal use.

    Stylesheet = """
        body {color: #000; font-family: sans;}
        .entry {}
        .error .message {color: #900}
        .warning .message {color: #740}
        .user .message {color: #009}
        .status .message {color: #090}
        .logExtra {margin-left: 40px;}
        .traceback {color: #555; height: 0px;}
        .timestamp {color: #FFF;}
    """
    pageTemplate = """
        <html>
        <head>
            <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
            <style type="text/css">
            %s    </style>
    
            <script type="text/javascript">
                function showDiv(id) {
                    div = document.getElementById(id);
                    div.style.visibility = "visible";
                    div.style.height = "auto";
                }
            </script>
        </head>
        <body>
        </body>
        </html> """ % Stylesheet

    def __init__(self, parent):
        """Creates the log widget.

        @param object parent: Qt parent object for log widet

        """
        QtGui.QWidget.__init__(self, parent)
        self.ui = LogWidgetTemplate.Ui_Form()
        self.ui.setupUi(self)
        #self.ui.input.hide()
        self.ui.filterTree.topLevelItem(1).setExpanded(True)
        
        self.entries = [] ## stores all log entries in memory
        self.cache = {} ## for storing html strings of entries that have already been processed
        self.displayedEntries = []
        self.typeFilters = []
        self.importanceFilter = 0
        self.dirFilter = False
        self.entryArrayBuffer = np.zeros(1000, dtype=[ ### a record array for quick filtering of entries
            ('index', 'int32'),
            ('importance', 'int32'),
            ('msgType', '|S10'),
            ('directory', '|S100'),
            ('entryId', 'int32')
        ])
        self.entryArray = self.entryArrayBuffer[:0]
        
        self.filtersChanged()
        
        self.sigDisplayEntry.connect(self.displayEntry, QtCore.Qt.QueuedConnection)
        self.sigAddEntry.connect(self.addEntry, QtCore.Qt.QueuedConnection)
        self.ui.exportHtmlBtn.clicked.connect(self.exportHtml)
        self.ui.filterTree.itemChanged.connect(self.setCheckStates)
        self.ui.importanceSlider.valueChanged.connect(self.filtersChanged)
        self.ui.output.anchorClicked.connect(self.linkClicked)
        self.sigScrollToAnchor.connect(self.scrollToAnchor, QtCore.Qt.QueuedConnection)
        
        
    def loadFile(self, f):
        """Load a log file for display.

          @param str f: path to file that should be laoded.

        f must be able to be read by pyqtgraph configfile.py
        """
        log = configfile.readConfigFile(f)
        self.entries = []
        self.entryArrayBuffer = np.zeros(len(log),dtype=[
            ('index', 'int32'),
            ('importance', 'int32'),
            ('msgType', '|S10'),
            ('directory', '|S100'),
            ('entryId', 'int32')
        ])
        self.entryArray = self.entryArrayBuffer[:]
                                   
        i = 0
        for k,v in log.items():
            v['id'] = k[9:]  ## record unique ID to facilitate HTML generation (javascript needs this ID)
            self.entries.append(v)
            self.entryArray[i] = np.array(
                    [(i,
                    v.get('importance', 5),
                    v.get('msgType', 'status'),
                    v.get('currentDir', ''),
                    v.get('entryId', v['id']))
                    ],
                    dtype=[('index', 'int32'),
                    ('importance', 'int32'),
                    ('msgType', '|S10'),
                    ('directory', '|S100'),
                    ('entryId', 'int32')]
                )
            i += 1
            
        self.filterEntries() ## puts all entries through current filters and displays the ones that pass
        
    def addEntry(self, entry):
        """Add a log entry to the list.
        """
        ## All incoming messages begin here
        ## for thread-safetyness:
        isGuiThread = QtCore.QThread.currentThread() == QtCore.QCoreApplication.instance().thread()
        if not isGuiThread:
            self.sigAddEntry.emit(entry)
            return
        
        self.entries.append(entry)
        i = len(self.entryArray)
        
        entryDir = entry.get('currentDir', None)
        if entryDir is None:
            entryDir = ''
        arr = np.array(
                [(i,
                entry['importance'],
                entry['msgType'],
                entryDir,
                entry['id']
                )],
                dtype = [
                    ('index', 'int32'),
                    ('importance', 'int32'),
                    ('msgType', '|S10'),
                    ('directory', '|S100'),
                    ('entryId', 'int32')
                ]
            )
        
        ## make more room if needed
        if len(self.entryArrayBuffer) == len(self.entryArray):
            newArray = np.empty(len(self.entryArrayBuffer)+1000, self.entryArrayBuffer.dtype)
            newArray[:len(self.entryArray)] = self.entryArray
            self.entryArrayBuffer = newArray
        self.entryArray = self.entryArrayBuffer[:len(self.entryArray)+1]
        self.entryArray[i] = arr
        self.checkDisplay(entry) ## displays the entry if it passes the current filters

    def setCheckStates(self, item, column):
        if item == self.ui.filterTree.topLevelItem(1):
            if item.checkState(0):
                for i in range(item.childCount()):
                    item.child(i).setCheckState(0, QtCore.Qt.Checked)
        elif item.parent() == self.ui.filterTree.topLevelItem(1):
            if not item.checkState(0):
                self.ui.filterTree.topLevelItem(1).setCheckState(0, QtCore.Qt.Unchecked)
        self.filtersChanged()
        
    def filtersChanged(self):
        ### Update self.typeFilters, self.importanceFilter, and self.dirFilter to reflect changes.
        tree = self.ui.filterTree
        
        self.typeFilters = []
        for i in range(tree.topLevelItem(1).childCount()):
            child = tree.topLevelItem(1).child(i)
            if tree.topLevelItem(1).checkState(0) or child.checkState(0):
                text = child.text(0)
                self.typeFilters.append(str(text))
            
        self.importanceFilter = self.ui.importanceSlider.value()
#        self.updateDirFilter()
        self.filterEntries()
        
#    def updateDirFilter(self, dh=None):
#        if self.ui.filterTree.topLevelItem(0).checkState(0):
#            if dh==None:
#                self.dirFilter = self.manager.getDirOfSelectedFile().name()
#            else:
#                self.dirFilter = dh.name()
#        else:
#            self.dirFilter = False
        
    
        
    def filterEntries(self):
        """Runs each entry in self.entries through the filters and displays if it makes it through."""
        ### make self.entries a record array, then filtering will be much faster (to OR true/false arrays, + them)
        typeMask = self.entryArray['msgType'] == b''
        for t in self.typeFilters:
            typeMask += self.entryArray['msgType'] == t.encode('ascii')
        mask = (self.entryArray['importance'] > self.importanceFilter) * typeMask
        #if self.dirFilter != False:
        #    d = np.ascontiguousarray(self.entryArray['directory'])
        #    j = len(self.dirFilter)
        #    i = len(d)
        #    d = d.view(np.byte).reshape(i, 100)[:, :j]
        #    d = d.reshape(i*j).view('|S%d' % j)
        #    mask *= (d == self.dirFilter)
        self.ui.output.clear()
        self.ui.output.document().setDefaultStyleSheet(self.Stylesheet)
        indices = list(self.entryArray[mask]['index'])
        self.displayEntry([self.entries[i] for i in indices])
                          
    def checkDisplay(self, entry):
        ### checks whether entry passes the current filters and displays it if it does.
        if entry['msgType'] not in self.typeFilters:
            return
        elif entry['importance'] < self.importanceFilter:
            return
        elif self.dirFilter is not False:
            if entry['currentDir'][:len(self.dirFilter)] != self.dirFilter:
                return
        else:
            self.displayEntry([entry])
    
        
    def displayEntry(self, entries):
        ## entries should be a list of log entries
        
        ## for thread-safetyness:
        isGuiThread = QtCore.QThread.currentThread() == QtCore.QCoreApplication.instance().thread()
        if not isGuiThread:
            self.sigDisplayEntry.emit(entries)
            return
        
        for entry in entries:
            if id(entry) not in self.cache:
                self.cache[id(entry)] = self.generateEntryHtml(entry)
                
            html = self.cache[id(entry)]
            sb = self.ui.output.verticalScrollBar()
            isMax = sb.value() == sb.maximum()
            self.ui.output.append(html)
            self.displayedEntries.append(entry)
            
            if isMax:
                ## can't scroll to end until the web frame has processed the html change
                #frame.setScrollBarValue(QtCore.Qt.Vertical, frame.scrollBarMaximum(QtCore.Qt.Vertical))
                
                ## Calling processEvents anywhere inside an error handler is forbidden
                ## because this can lead to Qt complaining about paint() recursion.
                self.sigScrollToAnchor.emit(str(entry['id']))  ## queued connection
            
    def scrollToAnchor(self, anchor):
        self.ui.output.scrollToAnchor(anchor)
                
    def generateEntryHtml(self, entry):
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
        
        #return """
        #<div class='entry'>
            #<div class='%s'>
                #<span class='timestamp'>%s</span>
                #<span class='message'>%s</span>
                #%s
            #</div>
        #</div>
        #""" % (entry['msgType'], entry['timestamp'], msg, extra)
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
        text = re.sub(r'&', '&amp;', text)
        text = re.sub(r'>','&gt;', text)
        text = re.sub(r'<', '&lt;', text)
        text = re.sub(r'\n', '<br/>\n', text)
        return text
    
    def formatExceptionForHTML(self, entry, exception=None, count=1, entryId=None):
        ### Here, exception is a dict that holds the message, reasons, docs, traceback and oldExceptions (which are also dicts, with the same entries)
        ## the count and tracebacks keywords are for calling recursively
        if exception is None:
            exception = entry['exception']
        #if tracebacks is None:
            #tracebacks = []
            
        indent = 10
        
        text = self.cleanText(exception['message'])
        text = re.sub(r'^HelpfulException: ', '', text)
        messages = [text]
        
        if 'reasons' in exception:
            reasons = self.formatReasonsStrForHTML(exception['reasons'])
            text += reasons
            #self.displayText(reasons, entry, color, clean=False)
        if 'docs' in exception:
            docs = self.formatDocsStrForHTML(exception['docs'])
            #self.displayText(docs, entry, color, clean=False)
            text += docs
        
        traceback = [self.formatTracebackForHTML(exception['traceback'], count)]
        text = [text]
        
        if 'oldExc' in exception:
            exc, tb, msgs = self.formatExceptionForHTML(entry, exception['oldExc'], count=count+1)
            text.extend(exc)
            messages.extend(msgs)
            traceback.extend(tb)
            
        #else:
            #if len(tracebacks)==count+1:
                #n=0
            #else: 
                #n=1
            #for i, tb in enumerate(tracebacks):
                #self.displayTraceback(tb, entry, number=i+n)
        if count == 1:
            exc = "<div class=\"exception\"><ol>" + "\n".join(["<li>%s</li>" % ex for ex in text]) + "</ol></div>"
            tbStr = "\n".join(["<li><b>%s</b><br/><span class='traceback'>%s</span></li>" % (messages[i], tb) for i,tb in enumerate(traceback)])
            #traceback = "<div class=\"traceback\" id=\"%s\"><ol>"%str(entryId) + tbStr + "</ol></div>"
            entry['tracebackHtml'] = tbStr

            #return exc + '<a href="#" onclick="showDiv(\'%s\')">Show traceback</a>'%str(entryId) + traceback
            return exc + '<a href="exc:%s">Show traceback %s</a>'%(str(entryId), str(entryId))
        else:
            return text, traceback, messages
        
        
    def formatTracebackForHTML(self, tb, number):
        try:
            tb = [line for line in tb if not line.startswith("Traceback (most recent call last)")]
        except:
            print("\n"+str(tb)+"\n")
            raise
        return re.sub(" ", "&nbsp;", ("").join(map(self.cleanText, tb)))[:-1]
        #tb = [self.cleanText(strip(x)) for x in tb]
        #lines = []
        #prefix = ''
        #for l in ''.join(tb).split('\n'):
            #if l == '':
                #continue
            #if l[:9] == "Traceback":
                #prefix = ' ' + str(number) + '. '
                #continue
            #spaceCount = 0
            #while l[spaceCount] == ' ':
                #spaceCount += 1
            #if prefix is not '':
                #spaceCount -= 1
            #lines.append("&nbsp;"*(spaceCount*4) + prefix + l)
            #prefix = ''
        #return '<div class="traceback">' + '<br />'.join(lines) + '</div>'
        #self.displayText('<br />'.join(lines), entry, color, clean=False)
        
    def formatReasonsStrForHTML(self, reasons):
        #indent = 6
        reasonStr = "<table class='reasons'><tr><td>Possible reasons include:\n<ul>\n"
        for r in reasons:
            r = self.cleanText(r)
            reasonStr += "<li>" + r + "</li>\n"
            #reasonStr += "&nbsp;"*22 + chr(97+i) + ". " + r + "<br>"
        reasonStr += "</ul></td></tr></table>\n"
        return reasonStr
    
    def formatDocsStrForHTML(self, docs):
        #indent = 6
        docStr = "<div class='docRefs'>Relevant documentation:\n<ul>\n"
        for d in docs:
            d = self.cleanText(d)
            docStr += "<li><a href=\"doc:%s\">%s</a></li>\n" % (d, d)
        docStr += "</ul></div>\n"
        return docStr
    
    def exportHtml(self, fileName=False):
        if fileName is False:
            self.fileDialog = FileDialog(self, "Save HTML as...", "htmltemp.log")
            #self.fileDialog.setFileMode(QtGui.QFileDialog.AnyFile)
            self.fileDialog.setAcceptMode(QtGui.QFileDialog.AcceptSave)
            self.fileDialog.show()
            self.fileDialog.fileSelected.connect(self.exportHtml)
            return
        if fileName[-5:] != '.html':
            fileName += '.html'
            
        #doc = self.ui.output.document().toHtml('utf-8')
        #for e in self.displayedEntries:
            #if e.has_key('tracebackHtml'):
                #doc = re.sub(r'<a href="exc:%s">(<[^>]+>)*Show traceback %s(<[^>]+>)*</a>'%(str(e['id']), str(e['id'])), e['tracebackHtml'], doc)
                
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
        url = url.toString()
        if url[:4] == 'doc:':
            #self.manager.showDocumentation(url[4:])
            print("Not implemented")
        elif url[:4] == 'exc:':
            cursor = self.ui.output.document().find('Show traceback %s' % url[4:])
            try:
                tb = self.entries[int(url[4:])-1]['tracebackHtml']
            except KeyError:
                tb = 'Can\'t get the backtrace as there is no tracebackHtml key in the entry dict. Something is royally fucked here.'
            except IndexError:
                try:
                    tb = self.entries[self.entryArray[self.entryArray['entryId']==(int(url[4:]))]['index']]['tracebackHtml']
                except:
                    print("requested index %d, but only %d entries exist." % (int(url[4:])-1, len(self.entries)))
                    raise
            cursor.insertHtml(tb)

    def clear(self):
        self.ui.output.clear()
        self.displayedEntryies = []


