# -*- coding: utf-8 -*-

from pyqtgraph.Qt import QtCore
from collections import OrderedDict
from .util.Mutex import Mutex

class ThreadManager(QtCore.QObject):
    """ This class keeps track of all the QThreads that are needed somewhere.
    """
    sigLogMessage = QtCore.Signal(object)

    def __init__(self):
        super().__init__()
        self._threads = OrderedDict()
        self.lock = Mutex()

    def newThread(self, name):
        """ Create a new thread with a name, return its object
          @param str name: unique name of thread

          @return QThread: new thred, none if failed
        """
        self.threadLog('Creating thread: \"{0}\".'.format(name))
        with self.lock:
            if 'name' in self._threads:
                return None
            self._threads[name] = ThreadItem(name)
            self._threads[name].sigThreadHasQuit.connect(self.cleanupThread)
        return self._threads[name].thread

    def cleanupThread(self, name):
        """Remove thread from thread list if it is not running anymore.
          
          @param str name: unique thread name
        """
        self.threadLog('Cleaning up thread {0}.'.format(name))
        if 'name' in self._threads and not self._threads[name].thread.isRunning():
            with self.lock:
                self._threads.pop(name)

    def quitThread(self, name):
        """Stop event loop of QThread.

          @param str name: unique thread name
        """
        if name in self._threads:
            self.threadLog('Quitting thread {0}.'.format(name))
            self._threads[name].thread.quit()
        else:
            self.threadLog('You tried quitting a nonexistent thread {0}.'.format(name))

    def quitAllThreads(self):
        """Stop event loop of all QThreads.
        """
        self.threadLog('Quit all threads')
        for name in self._threads:
            self._threads[name].thread.quit()

    def threadLog(self, msg, **kwargs):
        """Log a message with message type thread and importance 3.

          @param str msg: the log message
          @param dict kwargs: named parameters for logMsg
        """
        kwargs['importance'] = 3
        kwargs['msgType'] = 'thread'
        self.sigLogMessage.emit((msg, kwargs))


class ThreadItem(QtCore.QObject):
    """ This class represents a QThread.

      @signal str sigThreadHasQuit: sents a signal containig the name of the thread tha has quit
    """
    sigThreadHasQuit = QtCore.Signal(str)

    def __init__(self, name):
        """ Create a ThreadItwm object

          @param str name: unique name of the thread
        """
        super().__init__()
        self.thread = QtCore.QThread()
        self.name = name
        self.thread.finished.connect(self.myThreadHasQuit)
        
    def myThreadHasQuit(self):
        """ Signal handler for quitting thread.
            Re-emits signal containing the unique thread name.
        """
        self.sigThreadHasQuit.emit(self.name)


