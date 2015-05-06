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
                
    def set_next_point(self, point = None):
        """ Adds another trackpoint.
        
        @param float[3] point: position coordinates of the trackpoint
        
        @return int: error code (0:OK, -1:error)
        """
        if point != None:
            if len(point) != 3:
                self.logMsg('Length of set trackpoint is not 3.', 
                             msgType='error')
                return -1
            self._position_time_trace.append(np.array([time.time(),point[0],point[1],point[2]]))
        else:
            return -1
    
    def get_last_point(self):
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
        
        if len(self._position_time_trace) > 0:
            self._name = time.strftime('Point_%Y%m%d_%M%S%',self._creation_time)
        else:
            self._name = time.strftime('Point_%Y%m%d_%M%S%')
        if name != None:
            self._name=name
            
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
        
    def delete_last_point(self):
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
        self._current_trackpoint_name = None
        self.go_to_crosshair_after_refocus = True
                                
        #locking for thread safety
        self.threadlock = Mutex()
                               
    def activation(self, e):
        """ Initialisation performed during activation of the module.
        """
        
        self._optimiser_logic = self.connector['in']['optimiser1']['object']
#        print("Optimiser Logic is", self._optimiser_logic)
        self._confocal_logic = self.connector['in']['scannerlogic']['object']
#        print("Confocal Logic is", self._confocal_logic)
        
        crosshair=TrackPoint(point=[0,0,0], name='crosshair')
        crosshair._key='crosshair'
        self.track_point_list[crosshair._key] = crosshair
        
        self._optimiser_logic.signal_refocus_finished.connect(self._refocus_done, QtCore.Qt.QueuedConnection)
                
#        self.testing()
        
    def testing(self):
        self._optimiser_logic.start_refocus()
        name=self.add_trackpoint()
        print (name)
        
        self._optimiser_logic.start_refocus()
                    
    def add_trackpoint(self):
        
        new_track_point=TrackPoint(point=self._confocal_logic.get_position())
        self.track_point_list[new_track_point.get_name()] = new_track_point
        
        return new_track_point.get_name()
        
    def get_all_trackpoints(self):
        return self.track_point_list.keys()
        
    def change_name(self,trackpointname = None, newname = None):
        if trackpointname != None and trackpointname in self.track_point_list.keys():
            self.track_point_list[trackpointname].set_name(newname)
            return 0
        else:
            self.logMsg('The given Trackpoint ({}) does not exist.'.format(trackpointname), 
                msgType='error')
            return -1
            
    def delete_trackpoint(self,trackpointname = None):        
        if trackpointname != None and trackpointname in self.track_point_list.keys():
            if trackpointname is 'crosshair':
                self.logMsg('You cannot delete the crosshair.', msgType='warning')
                return -1
            del self.track_point_list[trackpointname]
            return 0
        else:
            self.logMsg('The given Trackpoint ({}) does not exist.'.format(trackpointname), 
                msgType='error')
            return -1
        
    def optimise_trackpoint(self,trackpointname = None):
        if trackpointname != None and trackpointname in self.track_point_list.keys():
            self.track_point_list['crosshair'].set_next_point(point=self._optimiser_logic.get_position())
            self._current_trackpoint_name = trackpointname
            self._optimiser_logic.start_refocus(trackpoint=self.track_point_list[trackpointname])
            return 0
        else:
            self.logMsg('The given Trackpoint ({}) does not exist.'.format(trackpointname), 
                msgType='error')
            return -1
                
    def go_to_trackpoint(self, trackpointname = None):
        if trackpointname != None and trackpointname in self.track_point_list.keys():
            self._current_trackpoint_name = trackpointname
            x,y,z = self.track_point_list[trackpointname]
            self._confocal_logic.set_position(x=x, y=y, z=z)
        else:
            self.logMsg('The given Trackpoint ({}) does not exist.'.format(trackpointname), 
                msgType='error')
            return -1
                
    def _refocus_done(self):
        if self._optimiser_logic.is_crosshair:                
            self.track_point_list['crosshair'].\
                    set_next_point([self._optimiser_logic.refocus_x, 
                                    self._optimiser_logic.refocus_y, 
                                    self._optimiser_logic.refocus_z])
            return 0
            
        if self._current_trackpoint_name != None and self._current_trackpoint_name in self.track_point_list.keys():
            self.track_point_list[self._current_trackpoint_name].\
                    set_next_point([self._optimiser_logic.refocus_x, 
                                    self._optimiser_logic.refocus_y, 
                                    self._optimiser_logic.refocus_z])
                                    
            if self.go_to_crosshair_after_refocus:
                self.go_to_trackpoint(trackpointname = 'crosshair')
            else:
                self.go_to_trackpoint(trackpointname = self._current_trackpoint_name)
                
            return 0
        else:
            self.logMsg('The given Trackpoint ({}) does not exist.'.format(self._current_trackpoint_name), 
                msgType='error')
            return -1