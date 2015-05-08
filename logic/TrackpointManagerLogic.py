# -*- coding: utf-8 -*-
# unstable: Kay Jahnke

from logic.GenericLogic import GenericLogic
from pyqtgraph.Qt import QtCore
from core.util.Mutex import Mutex
from collections import OrderedDict
import numpy as np
import time

class TrackPoint(object):
    """ unstable: Kay Jahnke    
    The actual individual trackpoint is saved in this generic object.

    TODO: (Lachlan) thinks it would be better vocabulary to change name from "trackpoint" to "point of interest (POI)".  This is a better fit with the metaphor of "sample maps" and "regions of interest".  Not all POIs will be "tracked".  

    TODO: In general, we are working to make the code naturally match the usage metaphor of "sample maps" with fluorescent spots at certain positions.  The spots should normally keep a fixed position relative to each other, but the sample itself shifts.
    """
    
    def __init__(self, point = None, name=None):
        self._position_time_trace=[]
        self._name = time.strftime('Point_%Y%m%d_%M%S')
        self._key = str(self._name)
        self._creation_time = time.time()
        
        if point != None:
            if len(point) != 3:
                self.logMsg('Length of set trackpoint is not 3.', 
                             msgType='error')
            self._position_time_trace.append(np.array([self._creation_time,point[0],point[1],point[2]]))
        if name != None:
            self._name=name

    def set_pos_in_sample(self, point = None):
        '''Defines the position of the trackpoint relative to the sample, 
        allowing a sample map to be constructed that matches the user's concept.
        '''

        # Choose reference point for sample coordinates.  1st trackpoint?  Scanner (0,0,0)?
        # Define position of current POI in sample coordinates.  This involves vector subtraction with the *latest* known sample position.

        # Once set, this "pos in sample" will not be altered unless the user wants to manually redefine this POI (for example, they put the POI in the wrong place.
        pass
                
    def set_next_point(self, point = None): #TODO: rename to set_new_position, "point" is confusing with "trackpoint"
        """ Adds another trackpoint.
        
        @param float[3] point: position coordinates of the trackpoint
        
        @return int: error code (0:OK, -1:error)
        """
        if point != None:
            if len(point) != 3:
#                self.logMsg('Length of set trackpoint is not 3.', 
#                             msgType='error')
                return -1
            self._position_time_trace.append(np.array([time.time(),point[0],point[1],point[2]]))
        else:
            return -1
    
    def get_last_point(self): #TODO: rename to get_last_position, "point" is confusing with "trackpoint".
        """ Returns the most current trackpoint.
        
        @return float[3]: the position of the last point
        """
        if len(self._position_time_trace) > 0:
            return self._position_time_trace[-1][1:]
        else:
            return [-1.,-1.,-1.]
            
    def set_name(self, name= None):
        """ Sets the name of the trackpoint.
        
        @param string name: name to be set.
        
        @return int: error code (0:OK, -1:error)
        """
        if self._name is 'crosshair' or self._name is 'sample':            
#            self.logMsg('You can not change the name of the crosshair.', 
#                        msgType='error')
            return -1
        if name != None:
            self._name=name
            return 0
        if len(self._position_time_trace) > 0:
            self._name = time.strftime('Point_%Y%m%d_%M%S%',self._creation_time)
            return -1
        else:
            self._name = time.strftime('Point_%Y%m%d_%M%S%')
            return -1
            
    def get_name(self):
        """ Returns the name of the trackpoint.
        
        @return string: name
        """
        return self._name
        
    def get_key(self):
        """ Returns the dictionary key of the trackpoint.
        
        @return string: key
        """
        return self._key
        
    def get_trace(self): #instead of "trace": drift_log, history, 
        """ Returns the whole position time trace as array.
        
        @return float[][4]: the whole position time trace
        """
        
        return np.array(self._position_time_trace)
        
    def delete_last_point(self): #Rename to delete_last_position
        """ Delete the last poitn in the trace.
        
        @return float[4]: the point just deleted.
        """
        
        if len(self._position_time_trace) > 0:
            return self._position_time_trace.pop()
        else:
            return [-1.,-1.,-1.,-1.]
    
    
                

class TrackpointManagerLogic(GenericLogic):
    """unstable: Kay Jahnke
    This is the Logic class for tracking bright features in the confocal scan.
    """

    signal_refocus_finished = QtCore.Signal()
    signal_timer_updated = QtCore.Signal()
    

    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        state_actions = {'onactivate': self.activation}
        GenericLogic.__init__(self, manager, name, config, state_actions, **kwargs)
        self._modclass = 'trackerlogic'
        self._modtype = 'logic'

        ## declare connectors
        self.connector['in']['optimiser1'] = OrderedDict()
        self.connector['in']['optimiser1']['class'] = 'OptimiserLogic'
        self.connector['in']['optimiser1']['object'] = None
        self.connector['in']['scannerlogic'] = OrderedDict()
        self.connector['in']['scannerlogic']['class'] = 'ConfocalLogic'
        self.connector['in']['scannerlogic']['object'] = None
        
        self.connector['out']['trackerlogic'] = OrderedDict()
        self.connector['out']['trackerlogic']['class'] = 'TrackpointManagerLogic'
        

        self.logMsg('The following configuration was found.', 
                    msgType='status')
                            
        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]), 
                        msgType='status')
        
        self.track_point_list = dict()
        self._current_trackpoint_key = None
        self.go_to_crosshair_after_refocus = True
        
        # timer and its handling for the periodic refocus
        self.timer = None
        self.time_left = 0
        self.timer_step = 0
        self.timer_duration = 300
                                
        #locking for thread safety
        self.threadlock = Mutex()
                               
    def activation(self, e):
        """ Initialisation performed during activation of the module.
        """
        
        self._optimiser_logic = self.connector['in']['optimiser1']['object']
#        print("Optimiser Logic is", self._optimiser_logic)
        self._confocal_logic = self.connector['in']['scannerlogic']['object']
#        print("Confocal Logic is", self._confocal_logic)
        
        # initally add crosshair to the trackpoints
        crosshair=TrackPoint(point=[0,0,0], name='crosshair')
        crosshair._key='crosshair'
        self.track_point_list[crosshair._key] = crosshair
        
        # initally add sample to the trackpoints
        sample=TrackPoint(point=[0,0,0], name='sample')
        sample._key='sample'
        self.track_point_list[sample._key] = sample
        
        # listen for the refocus to finish
        self._optimiser_logic.signal_refocus_finished.connect(self._refocus_done, QtCore.Qt.QueuedConnection)
                
        self.testing()
        
    def testing(self):
        """ Debug function for testing. """
        pass
                    
    def add_trackpoint(self):
        """ Creates a new trackpoint and adds it to the list.
                
        @return int: key of this new trackpoint
        
        The initial position is taken from the current crosshair.
        """
        
        new_track_point=TrackPoint(point=self._confocal_logic.get_position())
        self.track_point_list[new_track_point.get_key()] = new_track_point
        
        return new_track_point.get_key()
        
    def get_all_trackpoints(self):
        """ Returns a list of the names of all existing trankpoints.
        
        @return string[]: List of names of the trackpoints
        
        Also crosshair and sample are included.
        """
        
        return self.track_point_list.keys()
            
    def delete_trackpoint(self,trackpointkey = None):   
        """ Completely deletes the whole given trackpoint.
        
        @param string trackpointkey: the key of the trackpoint
        
        @return int: error code (0:OK, -1:error)
        
        Does not delete the crosshair and sample.
        """
        
        if trackpointkey != None and trackpointkey in self.track_point_list.keys():
            if trackpointkey is 'crosshair' or trackpointkey is 'sample':
                self.logMsg('You cannot delete the crosshair or sample.', msgType='warning')
                return -1
            del self.track_point_list[trackpointkey]
            return 0
        else:
            self.logMsg('The given Trackpoint ({}) does not exist.'.format(trackpointkey), 
                msgType='error')
            return -1
        
    def optimise_trackpoint(self,trackpointkey = None):
        """ Starts the optimisation procedure for the given trackpoint.
        
        @param string trackpointkey: the key of the trackpoint
        
        @return int: error code (0:OK, -1:error)
        
        This is threaded, so it returns directly. 
        The function _refocus_done handles the data when the optimisation returns.
        """
        
        if trackpointkey != None and trackpointkey in self.track_point_list.keys():
            self.track_point_list['crosshair'].set_next_point(point=self._confocal_logic.get_position())
            self._current_trackpoint_key = trackpointkey
            self._optimiser_logic.start_refocus(trackpoint=self.track_point_list[trackpointkey].get_last_point())
            return 0
        else:
            self.logMsg('The given Trackpoint ({}) does not exist.'.format(trackpointkey), 
                msgType='error')
            return -1
                
    def go_to_trackpoint(self, trackpointkey = None):
        """ Goes to the given trackpoint and saves it as the current one.
        
        @param string trackpointkey: the key of the trackpoint
        
        @return int: error code (0:OK, -1:error)
        """
        if trackpointkey != None and trackpointkey in self.track_point_list.keys():
            self._current_trackpoint_key = trackpointkey
            x,y,z = self.track_point_list[trackpointkey].get_last_point()
            self._confocal_logic.set_position(x=x, y=y, z=z)
        else:
            self.logMsg('The given Trackpoint ({}) does not exist.'.format(trackpointkey), 
                msgType='error')
            return -1
            
    def get_last_point(self, trackpointkey = None):
        """ Gets the most recent coordinates of the given trackpoint.
        
        @param string trackpointkey: the key of the trackpoint
        
        @return int: error code (0:OK, -1:error)
        """
        
        if trackpointkey != None and trackpointkey in self.track_point_list.keys():
            return self.track_point_list[trackpointkey].get_last_point()
        else:
            self.logMsg('The given Trackpoint ({}) does not exist.'.format(trackpointkey), 
                msgType='error')
            return [-1.,-1.,-1.]
                
    def get_name(self, trackpointkey = None):
        """ Gets the name of the given trackpoint.
        
        @param string trackpointkey: the key of the trackpoint
        
        @return int: error code (0:OK, -1:error)
        """
        
        if trackpointkey != None and trackpointkey in self.track_point_list.keys():
            return self.track_point_list[trackpointkey].get_name()
        else:
            self.logMsg('The given Trackpoint ({}) does not exist.'.format(trackpointkey), 
                msgType='error')
            return -1
                
    def set_next_point(self, trackpointkey = None, point = None):
        """ Adds another point to the trace of the given trackpoint.
        
        @param string trackpointkey: the key of the trackpoint
        @param float[3] point: coordinates of the next point
        
        @return int: error code (0:OK, -1:error)
        """
                
        if trackpointkey != None and point != None and trackpointkey in self.track_point_list.keys():
            if len(point) != 3:
                self.logMsg('Length of set trackpoint is not 3.', 
                             msgType='error')
                return -1
            return self.track_point_list[trackpointkey].set_next_point(point=point)
        else:
            self.logMsg('The given Trackpoint ({}) does not exist.'.format(trackpointkey), 
                msgType='error')
            return -1
            
    def set_name(self, trackpointkey = None, name = None):
        """ Sets the name of the given trackpoint.
        
        @param string trackpointkey: the key of the trackpoint
        @param string name: name of the trackpoint to be set
        
        @return int: error code (0:OK, -1:error)
        """
                
        if trackpointkey != None and name != None and trackpointkey in self.track_point_list.keys():
            return self.track_point_list[trackpointkey].set_name(name=name)
        else:
            self.logMsg('The given Trackpoint ({}) does not exist.'.format(trackpointkey), 
                msgType='error')
            return -1
            
    def delete_last_point(self, trackpointkey = None):
        """ Deletes the last tracked point from the trace of the given trackpoint.
        
        @param string trackpointkey: the key of the trackpoint
        
        @return int: error code (0:OK, -1:error)
        """
                
        if trackpointkey != None and trackpointkey in self.track_point_list.keys():
            return self.track_point_list['sample'].delete_last_point()
            return self.track_point_list[trackpointkey].delete_last_point()
        else:
            self.logMsg('The given Trackpoint ({}) does not exist.'.format(trackpointkey), 
                msgType='error')
            return -1
            
    def get_trace(self, trackpointkey = None):
        """ Get the full time trace of the given trackpoint.
        
        @param string trackpointkey: the key of the trackpoint for the trace
        
        @return int: error code (0:OK, -1:error)
        """
                
        if trackpointkey != None and trackpointkey in self.track_point_list.keys():
            return self.track_point_list[trackpointkey].get_trace()
        else:
            self.logMsg('The given Trackpoint ({}) does not exist.'.format(trackpointkey), 
                msgType='error')
            return [-1.,-1.,-1,-1]
            
    
    def set_current_trackpoint(self, trackpointkey = None):
        """ Set the internal current trackpoint.
        
        @param string trackpointkey: the key of the current trackpoint to be set
        
        @return int: error code (0:OK, -1:error)
        """
                
        if trackpointkey != None and trackpointkey in self.track_point_list.keys():
            self._current_trackpoint_key = trackpointkey
            return 0
        else:
            self.logMsg('The given Trackpoint ({}) does not exist.'.format(trackpointkey), 
                msgType='error')
            return -1
            
    def start_periodic_refocus(self, duration=None, trackpointkey = None):
        """ Starts the perodic refocussing of the trackpoint.
        
        @param float duration: (optional) the time between periodic refocussion
        @param string trackpointkey: (optional) the key of the current trackpoint to be set and refocussed on.
        
        @return int: error code (0:OK, -1:error)
        """
        if duration!=None:
            self.timer_duration=duration
        else:
            self.logMsg('No timer duration given, using {} s.'.format(self.timer_duration), 
                msgType='warning')
            
        if trackpointkey != None and trackpointkey in self.track_point_list.keys():
            self._current_trackpoint_key = trackpointkey
        
        self.logMsg('Periodic refocus on {}.'.format(self._current_trackpoint_key), msgType='status')
            
        self.timer_step = time.time()
        self.timer = QtCore.QTimer()
        self.timer.setSingleShot(False)
        self.timer.timeout.connect(self._periodic_refocus_loop)
        self.timer.start(300)
        return 0
        
    def _periodic_refocus_loop(self):
        """ This is the looped function that does the actual periodic refocus.
        
        If the time has run out, it refocussed the current trackpoint.
        Otherwise it just updates the time that is left.
        """
        self.time_left = self.timer_step-time.time()+self.timer_duration
        self.signal_timer_updated.emit()
        if self.time_left <= 0:
            self.timer_step = time.time()
            self.optimise_trackpoint(trackpointkey = self._current_trackpoint_key)
        
    def stop_periodic_refocus(self):
        """ Stops the perodic refocussing of the trackpoint.
        
        @return int: error code (0:OK, -1:error)
        """
        if self.timer == None:
            self.logMsg('No timer to stop.', 
                msgType='warning')
            return -1
        self.timer.stop()
        self.timer = None
        return 0
                
    def _refocus_done(self):
        """ Gets called automatically after the refocus is done and saves the new point.
        
        Also it tracks the sample and may go back to the crosshair.
        
        @return int: error code (0:OK, -1:error)
        """
        positions = [self._optimiser_logic.refocus_x, 
                     self._optimiser_logic.refocus_y, 
                     self._optimiser_logic.refocus_z]
                     
        if self._optimiser_logic.is_crosshair:                
            self.track_point_list['crosshair'].\
                    set_next_point(point=positions)
            return 0
            
        if self._current_trackpoint_key != None and self._current_trackpoint_key in self.track_point_list.keys():
            sample_shift=positions-self.track_point_list[self._current_trackpoint_key].get_last_point()
            sample_shift+=self.track_point_list['sample'].get_last_point()
            self.track_point_list['sample'].set_next_point(point=sample_shift)
            self.track_point_list[self._current_trackpoint_key].\
                    set_next_point(point=positions)
            
            if (not (self._current_trackpoint_key is 'crosshair')) and (not (self._current_trackpoint_key is 'sample')):
                self.signal_refocus_finished.emit()
                
            if self.go_to_crosshair_after_refocus:
                temp_key=self._current_trackpoint_key
                self.go_to_trackpoint(trackpointkey = 'crosshair')
                self._current_trackpoint_key = temp_key
            else:
                self.go_to_trackpoint(trackpointkey = self._current_trackpoint_key)
            return 0
        else:
            self.logMsg('The given Trackpoint ({}) does not exist.'.format(self._current_trackpoint_key), 
                msgType='error')
            return -1
