# -*- coding: utf-8 -*-

from core.Base import Base
import time
import threading 
#import Queue

class genericlogic(Base):
    """This is the Interface class to define the controls for the simple 
    microwave hardware.
    """
    
    def __init__(self, manager, name, configuation, callbacks, **kwargs):
        Base.__init__(self, manager, name, configuation, callbacks, **kwargs)
        self._modclass = 'genericlogic'
        self._modtype = 'genericlogic'
        
#        self.logMsg('The following configuration was found.', 
#                    msgType='status')
#        
#        # checking for the right configuration
#        for key in configuation.keys():
#            self.logMsg('{}: {}'.format(key,configuation[key]), 
#                        msgType='status')
                        
#        self.default_join_timeout = 10
#        self._threads = []
        
    
#    def getWorkerThread(self):
#        """Start the worker thread with target=run()"""

#    def stopme(self):
#        """Stop the worker thread"""
#        self.logMsg('setting stop request...', msgType='status')
#        self._my_stop_request.set() ##if run() is not executed in extra thread, stop() still should abort run() by setting this flag
#        if self.thread is None:
#            self.logMsg('no thread to stop, returning, ...', msgType='status')
#            return
#        elif not self.thread.isAlive():
#            self.logMsg('thread no longer alive, returning, ...', msgType='status')
#            return
#        elif self.thread is threading.current_thread():
#            self.logMsg('stop request from current thread, returning...', msgType='status')
#            return
#        self.logMsg('waiting for thread to finish ...', msgType='status')
#        self.thread.join(self.default_join_timeout)        
#        self.logMsg('Active threads at stop: {0:d}'.format(threading.activeCount()), 
#                    msgType='status')
#
#    def offer_pause(self):
#        """If the tracker_manager wants to do some tracking, pause until it is done"""
#        pass
#        #queues are disabled for now
#        if self.thread is None or not self.thread.is_tracker_client: return:
#        q = self.thread.command_queue
#        if not q.empty():
#            cmd = q.get_nowait()
#            if cmd == 'pause_request':
#                self.logMsg('preparing pause...', msgType='status')
#                self.prepare_pause()
#                q.task_done()
#                cmd = q.get(timeout=self.default_track_timeout)
#                if cmd == 'resume':
#                    self.logMsg('releasing pause...', msgType='status')
#                    self.prepare_resume()
#                    q.task_done()
#                else:
#                    raise RuntimeError("Expected 'resume' but got:" + cmd)
#            else:
#                raise RuntimeError('Expected pause_request but got:' + cmd)

#    def prepare_pause(self):
#        """Prepare optimal conditions for the tracker (i.e. switch off MW pulses etc.)
#        """        
#        pass

#    def prepare_resume(self):
#        """Resume normal conditions after tracking pause
#        """
#        pass

#    def runme(self):
#        """NEVER CALL THIS METHOD DIRECTLY. Use start() and stop() instead. Override it to implement your measurement.
#        Don't forget to offer_pause() once in a while.
#        Also, include the line "if self.stop_request.isSet(): break" in your main loop if you can accept thread stop.
#        """
#        while(True):
#            if self._my_stop_request.isSet():
#                self.logMsg('Stopping thread', msgType='status')
#                break
#            
#            time.sleep(1)
#            self.offer_pause()
#            time.sleep(1)
