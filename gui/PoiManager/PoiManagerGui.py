# -*- coding: utf-8 -*-
"""
Created on Tue May 5 2015

Lachlan Rogers
"""

from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph as pg
import numpy as np

from collections import OrderedDict
from core.Base import Base
from gui.PoiManager.PoiManagerGuiUI import Ui_PoiManager
from gui.Confocal.ConfocalGui import ColorBar



class PointMarker(pg.CircleROI):
    """Creates a circle as a marker. 
        
        @param int[2] pos: (length-2 sequence) The position of the ROI’s origin.
        @param int[2] size: (length-2 sequence) The size of the ROI’s bounding rectangle.
        @param **args: All extra keyword arguments are passed to ROI()
        
        Have a look at: 
        http://www.pyqtgraph.org/documentation/graphicsItems/roi.html    
    """
    
    def __init__(self, pos, size, **args):
        pg.CircleROI.__init__(self, pos, size, **args)
#        handles=self.getHandles()
#        for handle in handles:
#            print(handle)
#            self.removeHandle(handle)


class CustomViewBox(pg.ViewBox):
    def __init__(self, *args, **kwds):
        pg.ViewBox.__init__(self, *args, **kwds)
        self.setMouseMode(self.RectMode)

    ## reimplement right-click to zoom out
    def mouseClickEvent(self, ev):
        if ev.button() == QtCore.Qt.RightButton:
            #self.autoRange()
            self.setXRange(0,5)
            self.setYRange(0,10)

    def mouseDragEvent(self, ev,axis=0):
        if (ev.button() == QtCore.Qt.LeftButton) and (ev.modifiers() & QtCore.Qt.ControlModifier):
            pg.ViewBox.mouseDragEvent(self, ev,axis)
        else:
            ev.ignore()
  
          
            
class PoiManagerMainWindow(QtGui.QMainWindow,Ui_PoiManager):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.setupUi(self)
        

            
               
            
class PoiManagerGui(Base,QtGui.QMainWindow,Ui_PoiManager):
    """
    This is the GUI Class for PoiManager
    """
    
    

    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        c_dict = {'onactivate': self.initUI}
        Base.__init__(self,
                    manager,
                    name,
                    config,
                    c_dict)
        
        self._modclass = 'PoiManagerGui'
        self._modtype = 'gui'
        
        ## declare connectors
        self.connector['in']['poimanagerlogic1'] = OrderedDict()
        self.connector['in']['poimanagerlogic1']['class'] = 'PoiManagerLogic'
        self.connector['in']['poimanagerlogic1']['object'] = None

        self.connector['in']['confocallogic1'] = OrderedDict()
        self.connector['in']['confocallogic1']['class'] = 'ConfocalLogic'
        self.connector['in']['confocallogic1']['object'] = None

#        self.connector['in']['savelogic'] = OrderedDict()
#        self.connector['in']['savelogic']['class'] = 'SaveLogic'
#        self.connector['in']['savelogic']['object'] = None

        self.logMsg('The following configuration was found.', 
                    msgType='status')
                            
        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]), 
                        msgType='status')  
                        
    def initUI(self, e=None):
        """ Definition, configuration and initialisation of the POI Manager GUI.
          
          @param class e: event class from Fysom


        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules.
        
        """
        
        self._poi_manager_logic = self.connector['in']['poimanagerlogic1']['object']
        self._confocal_logic = self.connector['in']['confocallogic1']['object']
        print("POI Manager logic is", self._poi_manager_logic)
        print("Confocal logic is", self._confocal_logic)
        
#        self._save_logic = self.connector['in']['savelogic']['object']
#        print("Save logic is", self._save_logic)  
        
        # Use the inherited class 'Ui_PoiManagerGuiTemplate' to create now the 
        # GUI element:
        self._mw = PoiManagerMainWindow()

                
        #####################
        # Setting up display of ROI map xy image
        #####################

        # Get the image for the display from the logic: 
        roi_map_data = self._confocal_logic.xy_image[:,:,3].transpose()
             
        # Load the image in the display:
        self.roi_map_image = pg.ImageItem(roi_map_data)
        self.roi_map_image.setRect(QtCore.QRectF(self._confocal_logic.image_x_range[0], self._confocal_logic.image_y_range[0], self._confocal_logic.image_x_range[1]-self._confocal_logic.image_x_range[0], self._confocal_logic.image_y_range[1]-self._confocal_logic.image_y_range[0]))
        
        # Add the display item to the roi map ViewWidget defined in the UI file
        self._mw.roi_map_ViewWidget.addItem(self.roi_map_image)
        
        # create a color map that goes from dark red to dark blue:

        # Absolute scale relative to the expected data not important. This 
        # should have the same amount of entries (num parameter) as the number
        # of values given in color. 
        pos = np.linspace(0.0, 1.0, num=10)
        color = np.array([[127,  0,  0,255], [255, 26,  0,255], [255,129,  0,255],
                          [254,237,  0,255], [160,255, 86,255], [ 66,255,149,255],
                          [  0,204,255,255], [  0, 88,255,255], [  0,  0,241,255],
                          [  0,  0,132,255]], dtype=np.ubyte)
                      
        color_inv = np.array([ [  0,  0,132,255], [  0,  0,241,255], [  0, 88,255,255],
                               [  0,204,255,255], [ 66,255,149,255], [160,255, 86,255],
                               [254,237,  0,255], [255,129,  0,255], [255, 26,  0,255],
                               [127,  0,  0,255] ], dtype=np.ubyte)
        colmap = pg.ColorMap(pos, color_inv)
        
        self.colmap_norm = pg.ColorMap(pos, color/255)

        # get the LookUpTable (LUT), first two params should match the position
        # scale extremes passed to ColorMap(). 
        # I believe last one just has to be >= the difference between the min and max level set later
        lut = colmap.getLookupTable(0, 1, 2000)

            
        self.roi_map_image.setLookupTable(lut)

        #####################
        # Setting up display of sample shift plot
        #####################

        # Load image in the display
        self.x_shift_plot = pg.ScatterPlotItem([0],[0],symbol='o', pen='r')
        self.y_shift_plot = pg.ScatterPlotItem([0],[0],symbol='s', pen='g')
        self.z_shift_plot = pg.ScatterPlotItem([0],[0],symbol='t', pen='b')

        # Add the plot to the ViewWidget defined in the UI file
        self._mw.sample_shift_ViewWidget.addItem(self.x_shift_plot)
        self._mw.sample_shift_ViewWidget.addItem(self.y_shift_plot)
        self._mw.sample_shift_ViewWidget.addItem(self.z_shift_plot)


        #####################        
        # Connect signals
        #####################        

        self._mw.get_confocal_image_Button.clicked.connect(self.get_confocal_image)
        self._mw.set_poi_Button.clicked.connect(self.set_new_poi)
        self._mw.goto_poi_Button.clicked.connect(self.goto_poi)
        self._mw.delete_last_pos_Button.clicked.connect(self.delete_last_point)
        self._mw.manual_update_poi_Button.clicked.connect(self.manual_update_poi)
        self._mw.poi_name_Input.returnPressed.connect(self.change_poi_name)
        self._mw.delete_poi_Button.clicked.connect(self.delete_poi)

        self._mw.update_poi_Button.clicked.connect(self.update_poi_pos)

        self._mw.periodic_update_Button.stateChanged.connect(self.toggle_periodic_update)

        self._mw.shift_refresh_Button.clicked.connect(self._redraw_sample_shift)
        
        self._markers=[]
        
        #Signal at end of refocus
        self._poi_manager_logic.signal_refocus_finished.connect(self._redraw_sample_shift, QtCore.Qt.QueuedConnection)
        self._poi_manager_logic.signal_timer_updated.connect(self._update_timer, QtCore.Qt.QueuedConnection)
        self._poi_manager_logic.signal_poi_updated.connect(self._redraw_sample_shift, QtCore.Qt.QueuedConnection)
 
#        print('Main POI Manager Window shown:')
        self._mw.show()
    
    def get_confocal_image(self):
        self.roi_map_image.getViewBox().enableAutoRange()
        self.roi_map_image.setRect(QtCore.QRectF(self._confocal_logic.image_x_range[0], self._confocal_logic.image_y_range[0], self._confocal_logic.image_x_range[1]-self._confocal_logic.image_x_range[0], self._confocal_logic.image_y_range[1]-self._confocal_logic.image_y_range[0]))
        self.roi_map_image.setImage(image=self._confocal_logic.xy_image[:,:,3].transpose(),autoLevels=True)

    
    def set_new_poi(self):
        ''' This method sets a new poi from the current crosshair position

        '''
        key=self._poi_manager_logic.add_poi()

        print('new poi '+key)
        print(self._poi_manager_logic.get_all_pois())
        print(self._poi_manager_logic.get_last_point(poikey=key))

        self.population_poi_list()

        # Set the newly added poi as the selected poi to manage.
        self._mw.active_poi_Input.setCurrentIndex(self._mw.active_poi_Input.findData(key))
        
    def delete_last_point(self):
        ''' This method deletes the last track position of a chosen poi
        '''
        
        key=self._mw.active_poi_Input.itemData(self._mw.active_poi_Input.currentIndex())
        self._poi_manager_logic.delete_last_point(poikey=key)


    def delete_poi(self):
        '''This method deletes a poi from the list of managed points
        '''
        key=self._mw.active_poi_Input.itemData(self._mw.active_poi_Input.currentIndex())
        self._poi_manager_logic.delete_poi(poikey=key)
    
        self.population_poi_list()

    def manual_update_poi(self):
        """ Manually adds a point to the trace of a given poi without refocussing.
        """
        
        key=self._mw.active_poi_Input.itemData(self._mw.active_poi_Input.currentIndex())

        self._poi_manager_logic.set_new_position(poikey=key)
        
    def toggle_periodic_update(self):
        if self._poi_manager_logic.timer ==  None:
            key=self._mw.active_poi_Input.itemData(self._mw.active_poi_Input.currentIndex())
            period = self._mw.update_period_Input.value()

            self._poi_manager_logic.start_periodic_refocus(duration=period, poikey = key)
            self._mw.periodic_update_Button.setChecked(True)

        else:
            self._poi_manager_logic.stop_periodic_refocus()
            self._mw.periodic_update_Button.setChecked(False)

    def goto_poi(self, key):
        ''' Go to the last known position of poi <key>
        '''
        
        key=self._mw.active_poi_Input.itemData(self._mw.active_poi_Input.currentIndex())

        self._poi_manager_logic.go_to_poi(poikey=key)

        print(self._poi_manager_logic.get_last_point(poikey=key))


    def population_poi_list(self):
        ''' Populate the dropdown box for selecting a poi
        '''
        self._mw.active_poi_Input.clear()
        self._mw.active_poi_Input.setInsertPolicy(QtGui.QComboBox.InsertAlphabetically)

        for marker in self._markers:
            self._mw.roi_map_ViewWidget.removeItem(marker)
            del marker
            
        self._markers=[]
        
        for key in self._poi_manager_logic.get_all_pois():
            #self._poi_manager_logic.track_point_list[key].set_name('Kay_'+key[6:])
            if key is not 'crosshair' and key is not 'sample':
                self._mw.active_poi_Input.addItem(self._poi_manager_logic.get_name(poikey=key), key)
                
                # Create Region of Interest as marker:
                position=self._poi_manager_logic.get_last_point(poikey=key)
                position=position[:2]-[2.5,2.5]
                self._markers.append(\
                    PointMarker(position, 
                                [5, 5], 
                                pen={'color': "F0F", 'width': 2}, 
                                movable=False, 
                                scaleSnap=True, 
                                snapSize=1.0))
                # Add to the Map Widget
                self._mw.roi_map_ViewWidget.addItem(self._markers[-1])

    def change_poi_name(self):
        '''Change the name of a poi
        '''

        key=self._mw.active_poi_Input.itemData(self._mw.active_poi_Input.currentIndex())

        newname=self._mw.poi_name_Input.text()


        self._poi_manager_logic.set_name(poikey=key, name=newname)

        self.population_poi_list()

        # Keep the renamed POI as the selected POI to manage.
        self._mw.active_poi_Input.setCurrentIndex(self._mw.active_poi_Input.findData(key))

        # After POI name is changed, empty name field
        self._mw.poi_name_Input.setText('')

    def update_poi_pos(self):

        key=self._mw.active_poi_Input.itemData(self._mw.active_poi_Input.currentIndex())

        self._poi_manager_logic.optimise_poi(poikey=key)

    def _update_timer(self):
        #placeholder=QtGui.QLineEdit()
        #placeholder.setText('{0:.1f}'.format(self._poi_manager_logic.time_left))
        
#        print(self._poi_manager_logic.time_left)
        self._mw.time_till_next_update_Display.display( self._poi_manager_logic.time_left )

    def _redraw_sample_shift(self):
        
        # Get trace data and calculate shifts in x,y,z
        poi_trace=self._poi_manager_logic.get_trace(poikey='sample')

        time_shift_data = poi_trace[:,0] - poi_trace[0,0]
        x_shift_data  = poi_trace[:,1] - poi_trace[0,1] 
        y_shift_data  = poi_trace[:,2] - poi_trace[0,2] 
        z_shift_data  = poi_trace[:,3] - poi_trace[0,3] 
        self.x_shift_plot.setData(time_shift_data, x_shift_data)
        self.y_shift_plot.setData(time_shift_data, y_shift_data)
        self.z_shift_plot.setData(time_shift_data, z_shift_data)
        
#        print (self._poi_manager_logic.get_trace(poikey='sample'))
