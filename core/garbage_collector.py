import gc

from qtpy.QtCore import QTimer
from qtpy.QtCore import Slot
import logging
logger = logging.getLogger('gc')


class GarbageCollector(object):
    '''
    Disable automatic garbage collection and instead collect manually
    on a timer.

    This is done to ensure that garbage collection only happens in the GUI
    thread, as otherwise Qt can crash.

    Parameters
    ==========
    @param interval float: timeout interval in seconds. Default: 1s
    @param debug bool: debug output. Default: False

    Version history:
    - Original:
        Credit:  Erik Janssens
        Source:  http://pydev.blogspot.com/2014/03/should-python-garbage-collector-be.html
    - Modified: pyqtgraph
    - Modified: qudi
    '''

    def __init__(self, interval=1.0, debug=False):
        """
        Initializes garbage collector

        @param interval float: timeout interval in seconds. Default: 1s
        @param debug bool: debug output. Default: False
        """
        self.debug = debug
        if debug:
            gc.set_debug(gc.DEBUG_LEAK)

        self.timer = QTimer()
        self.timer.timeout.connect(self.check)

        self.threshold = gc.get_threshold()
        gc.disable()
        self.timer.start(interval * 1000)

    @Slot()
    def check(self):
        """
        Method called by the garbage collector timer to check if there is
        something to collect.
        """
        # return self.debug_cycles() # uncomment to just debug cycles
        l0, l1, l2 = gc.get_count()
        if self.debug:
            logger.debug('gc_check called: {0} {1} {2}'.format(l0, l1, l2))
        if l0 > self.threshold[0]:
            num = gc.collect(0)
            if self.debug:
                logger.debug('collecting gen 0, found: {0:d} unreachable'
                             ''.format(num))
            if l1 > self.threshold[1]:
                num = gc.collect(1)
                if self.debug:
                    logger.debug('collecting gen 1, found: {0:d} unreachable'
                                 ''.format(num))
                if l2 > self.threshold[2]:
                    num = gc.collect(2)
                    if self.debug:
                        logger.debug('collecting gen 2, found: {0:d} '
                                     'unreachable'.format(num))

    def debug_cycles(self):
        """
        Method called in check() to debug cycles. Uncomment the corresponding
        line in the implementation of check().
        """
        gc.collect()
        for obj in gc.garbage:
            print(obj, repr(obj), type(obj))
