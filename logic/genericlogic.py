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
        
        self.logMsg('The following configuration was found.', 
                    messageType='status')
        
        # checking for the right configuration
        for key in configuation.keys():
            self.logMsg('{}: {}'.format(key,configuation[key]), 
                        messageType='status')
                        
        self.is_tracker_client = True
        self.pause_order = 5
        self.default_join_timeout = 20
        self.default_track_timeout = 600
        self.stop_request = threading.Event()
        self.stop_request.clear()
        self.thread = None
        
    
    def startme(self):
        """Start the worker thread with target=run()"""
        ## try to clean up
        self.stopme()
        self.stop_request.clear()
        self.logMsg('Active threads: {0:d}'.format(threading.activeCount()), 
                        messageType='status')

        ## allocate new thread
        for i in range(1,10):
            try:
                self.thread = threading.Thread(target=self.runme,
                                        name=self._modclass + '.' + self._modtype + time.strftime('_%y%m%d_%M_%S'))
                self.thread.stop_request = threading.Event()
                self.thread.stop_request.clear()
                break
            except Exception as e:
                ## we've had problems with a "can't start new thread" exception. therefore we retry here
                self.log.exception(str(e))
                self.logMsg('Error creating a new thread: {!s}'.format(str(e)), 
                            messageType='error')
                self.logMsg('Active threads: {0:d}'.format(threading.activeCount()), 
                            messageType='status')
                time.sleep(5)
        ## set flags for tracker
        # TODO: maybe subclass thread and add these parameters, here we're storing data twice. but not now...
        self.thread.is_tracker_client = self.is_tracker_client
        self.thread.pause_order = self.pause_order
#        self.thread.command_queue = Queue.Queue()

        ## offer a pause, and then start
        self.offer_pause()
        self.thread.start()

    def stopme(self):
        """Stop the worker thread"""
        self.logMsg('setting stop request...', messageType='status')
        self.stop_request.set() ##if run() is not executed in extra thread, stop() still should abort run() by setting this flag
        if self.thread is None:
            self.logMsg('no thread to stop, returning, ...', messageType='status')
            return
        elif not self.thread.isAlive():
            self.logMsg('thread no longer alive, returning, ...', messageType='status')
            return
        elif self.thread is threading.current_thread():
            self.logMsg('stop request from current thread, returning...', messageType='status')
            return
        self.logMsg('waiting for thread to finish ...', messageType='status')
        self.thread.join(self.default_join_timeout)        
        self.logMsg('Active threads: {0:d}'.format(threading.activeCount()), 
                    messageType='status')

    def offer_pause(self):
        """If the tracker_manager wants to do some tracking, pause until it is done"""
        pass
        #queues are disabled for now
#        if self.thread is None or not self.thread.is_tracker_client: return:
#        q = self.thread.command_queue
#        if not q.empty():
#            cmd = q.get_nowait()
#            if cmd == 'pause_request':
#                self.logMsg('preparing pause...', messageType='status')
#                self.prepare_pause()
#                q.task_done()
#                cmd = q.get(timeout=self.default_track_timeout)
#                if cmd == 'resume':
#                    self.logMsg('releasing pause...', messageType='status')
#                    self.prepare_resume()
#                    q.task_done()
#                else:
#                    raise RuntimeError("Expected 'resume' but got:" + cmd)
#            else:
#                raise RuntimeError('Expected pause_request but got:' + cmd)

    def prepare_pause(self):
        """Prepare optimal conditions for the tracker (i.e. switch off MW pulses etc.)
        """        
        pass

    def prepare_resume(self):
        """Resume normal conditions after tracking pause
        """
        pass

    def runme(self):
        """NEVER CALL THIS METHOD DIRECTLY. Use start() and stop() instead. Override it to implement your measurement.
        Don't forget to offer_pause() once in a while.
        Also, include the line "if self.stop_request.isSet(): break" in your main loop if you can accept thread stop.
        """
        while(True):
            if self.stop_request.isSet():
                self.logMsg('Stopping thread', messageType='status')
                break
            
            time.sleep(1)
            self.offer_pause()
            time.sleep(1)
