# -*- coding: utf-8 -*-
"""
Created on Mon Apr 27 17:54:58 2015

@author: user-admin
"""

from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph as pg
import numpy as np

from collections import OrderedDict
from core.Base import Base
from gui.Tracker.TrackerGuiUI import Ui_MainWindow
from gui.Tracker.TrackerSettingsUI import Ui_SettingsDialog
from gui.Confocal.ConfocalGui import ColorBar

# To convert the *.ui file to a raw TrackerGuiUI.py file use the python script
# in the Anaconda directory, which you can find in:
#
# "<Installation-dir of Anacona>\Anaconda3\Lib\site-packages\PyQt4\uic\pyuic.py".
#
# Then use that script like
#
# "<Installation-dir of Anacona>\Anaconda3\Lib\site-packages\PyQt4\uic\pyuic.py" TrackerGuiUI.ui > TrackerGuiUI.py
#
# to convert to TrackerGuiUI.py.



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
            
            
class TrackerMainWindow(QtGui.QMainWindow,Ui_MainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.setupUi(self)
        
class TrackerSettingDialog(QtGui.QDialog,Ui_SettingsDialog):
    def __init__(self):
        QtGui.QDialog.__init__(self)
        self.setupUi(self)

            
               
            
class TrackerGui(Base,QtGui.QMainWindow,Ui_MainWindow):
    """
    Main Tracker Class
    """
    
    

    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        c_dict = {'onactivate': self.initUI}
        Base.__init__(self,
                    manager,
                    name,
                    config,
                    c_dict)
        
        self._modclass = 'TrackerGui'
        self._modtype = 'gui'
        
        ## declare connectors
        self.connector['in']['trackerlogic1'] = OrderedDict()
        self.connector['in']['trackerlogic1']['class'] = 'TrackerLogic'
        self.connector['in']['trackerlogic1']['object'] = None

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
        """ Definition, configuration and initialisation of the tracker GUI.
          
          @param class e: event class from Fysom


        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules.
        
        """
        
        self._tracker_logic = self.connector['in']['trackerlogic1']['object']
        print("Tracking logic is", self._tracker_logic)
        
#        self._save_logic = self.connector['in']['savelogic']['object']
#        print("Save logic is", self._save_logic)  
        
        # Use the inherited class 'Ui_TrackerGuiTemplate' to create now the 
        # GUI element:
        self._mw = TrackerMainWindow()
        self._sw = TrackerSettingDialog()
        
        # Get the image for the display from the logic:
        arr01 = self._tracker_logic.xy_refocus_image[:,:,3].transpose()
        arr02 = self._tracker_logic.z_refocus_line


        # Load the image in the display:
        self.xy_refocus_image = pg.ImageItem(arr01)
#        self.xy_refocus_image.setRect(QtCore.QRectF(0, 0, 100, 100))        
        self.xy_refocus_image.setRect(QtCore.QRectF(self._tracker_logic._trackpoint_x - 0.5 * self._tracker_logic.refocus_XY_size , self._tracker_logic._trackpoint_y - 0.5 * self._tracker_logic.refocus_XY_size , self._tracker_logic.refocus_XY_size, self._tracker_logic.refocus_XY_size))               
#        self.xy_refocus_image.setRect(QtCore.QRectF(self._tracker_logic._trackpoint_x - 0.5 * self._tracker_logic.refocus_XY_size+1, self._tracker_logic._trackpoint_y - 0.5 * self._tracker_logic.refocus_XY_size+1, self._tracker_logic._X_values[1]-self._tracker_logic._X_values[0], self._tracker_logic._Y_values[1]-self._tracker_logic._Y_values[0]))               
        
#        self._tracker_logic._trackpoint_x - 0.5 * self._tracker_logic.refocus_XY_size        
        
#        self._X_values = np.arange(xmin, xmax + self.refocus_XY_step, self.refocus_XY_step)
#        self._Y_values = np.arange(ymin, ymax + self.refocus_XY_step, self.refocus_XY_step)
#        self._Z_values = self._trackpoint_z * np.ones(self._X_values.shape)        
        
        
        self.xz_refocus_image = pg.PlotDataItem(self._tracker_logic._zimage_Z_values,arr02)
        self.xz_refocus_fit_image = pg.PlotDataItem(self._tracker_logic._zimage_Z_values,self._tracker_logic.z_fit_data, pen=QtGui.QPen(QtGui.QColor(255,0,255,255)))
        
        # Add the display item to the xy and xz VieWidget, which was defined in
        # the UI file.
        self._mw.xy_refocus_ViewWidget.addItem(self.xy_refocus_image)
        self._mw.xz_refocus_ViewWidget.addItem(self.xz_refocus_image)
        self._mw.xz_refocus_ViewWidget.addItem(self.xz_refocus_fit_image)
        
        #Add crosshair to the xy refocus scan
        self.vLine = pg.InfiniteLine(pen=QtGui.QPen(QtGui.QColor(255,0,255,255), 0.01), pos=50, angle=90, movable=False)
        self.hLine = pg.InfiniteLine(pen=QtGui.QPen(QtGui.QColor(255,0,255,255), 0.01), pos=50, angle=0, movable=False)
        self._mw.xy_refocus_ViewWidget.addItem(self.vLine, ignoreBounds=True)
        self._mw.xy_refocus_ViewWidget.addItem(self.hLine, ignoreBounds=True)
        
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

            
        self.xy_refocus_image.setLookupTable(lut)
        
        # Add color bar:        
        self.xy_cb = ColorBar(self.colmap_norm, 100, 100000, label='Counts')#Foo (Hz)')#, [0., 0.5, 1.0])          
             
        self._mw.xy_refocus_cb_ViewWidget.addItem(self.xy_cb)
        self._mw.xy_refocus_cb_ViewWidget.hideAxis('bottom')
        
        # Connect to default values:
        self._sw.xy_refocusrange_InputWidget.setText(str(self._tracker_logic.refocus_XY_size))
        self._sw.xy_refocusstepsize_InputWidget.setText(str(self._tracker_logic.refocus_XY_step))
        self._sw.z_refocusrange_InputWidget.setText(str(self._tracker_logic.refocus_Z_size))
        self._sw.z_refocusstepsize_InputWidget.setText(str(self._tracker_logic.refocus_Z_step))
        self._sw.count_freq_InputWidget.setText(str(self._tracker_logic._clock_frequency))
        self._sw.return_slow_InputWidget.setText(str(self._tracker_logic.return_slowness))
        
        # Add to the QLineEdit Widget a Double Validator to ensure only a 
        # float input.
        validator = QtGui.QDoubleValidator()
        validator2 = QtGui.QIntValidator()
        self._sw.xy_refocusrange_InputWidget.setValidator(validator)
        self._sw.xy_refocusstepsize_InputWidget.setValidator(validator)
        self._sw.z_refocusrange_InputWidget.setValidator(validator)
        self._sw.z_refocusstepsize_InputWidget.setValidator(validator)
        self._sw.count_freq_InputWidget.setValidator(validator2)
        self._sw.return_slow_InputWidget.setValidator(validator)
        
                
#        # Update the inputed/displayed numbers if return key is hit:
#        self._sw.xy_refocusrange_InputWidget.returnPressed.connect(self.update_xy_refocusrange)
#        self._sw.xy_refocusstepsize_InputWidget.returnPressed.connect(self.update_xy_refocusstepsize)
#        self._sw.z_refocusrange_InputWidget.returnPressed.connect(self.update_z_refocusrange)
#        self._sw.z_refocusstepsize_InputWidget.returnPressed.connect(self.update_z_refocusstepsize)
#        
#        # Declare for which fields changes are applied if the cursor is leaving
#        # the field:
#        self._sw.xy_refocusrange_InputWidget.editingFinished.connect(self.update_xy_refocusrange)
#        self._sw.xy_refocusstepsize_InputWidget.editingFinished.connect(self.update_xy_refocusstepsize)
#        self._sw.z_refocusrange_InputWidget.editingFinished.connect(self.update_z_refocusrange)
#        self._sw.z_refocusstepsize_InputWidget.editingFinished.connect(self.update_z_refocusstepsize)

        
        self._tracker_logic.signal_xy_image_updated.connect(self.refresh_xy_image)
        self._tracker_logic.signal_z_image_updated.connect(self.refresh_z_image)
        self._mw.action_Settings.triggered.connect(self.menue_settings)
        self._sw.accepted.connect(self.update_settings)
        self._sw.rejected.connect(self.reject_settings)
        self._sw.buttonBox.button(QtGui.QDialogButtonBox.Apply).clicked.connect(self.update_settings)
        
        
        print('Main Tracker Windows shown:')
        self._mw.show()
    
    
    def update_settings(self):
        self._tracker_logic.refocus_XY_size = float(self._sw.xy_refocusrange_InputWidget.text())
        self._tracker_logic.refocus_XY_step = float(self._sw.xy_refocusstepsize_InputWidget.text())
        self._tracker_logic.refocus_Z_size = float(self._sw.z_refocusrange_InputWidget.text())
        self._tracker_logic.refocus_Z_step = float(self._sw.z_refocusstepsize_InputWidget.text())
        self._tracker_logic.set_clock_frequency(self._sw.count_freq_InputWidget.text())
        self._tracker_logic.return_slowness = float(self._sw.return_slow_InputWidget.text())
        
        
    def reject_settings(self):
        self._sw.xy_refocusrange_InputWidget.setText(str(self._tracker_logic.refocus_XY_size))
        self._sw.xy_refocusstepsize_InputWidget.setText(str(self._tracker_logic.refocus_XY_step))
        self._sw.z_refocusrange_InputWidget.setText(str(self._tracker_logic.refocus_Z_size))
        self._sw.z_refocusstepsize_InputWidget.setText(str(self._tracker_logic.refocus_Z_step))
        self._sw.count_freq_InputWidget.setText(str(self._tracker_logic._clock_frequency))
        self._sw.return_slow_InputWidget.setText(str(self._tracker_logic.return_slowness))
        
    def refresh_xy_colorbar(self):
        self._mw.xy_refocus_cb_ViewWidget.clear()
        self.xy_cb = ColorBar(self.colmap_norm, 100, self.xy_refocus_image.image.max(), label='Counts')#Foo (Hz)')#, [0., 0.5, 1.0])               
        self._mw.xy_refocus_cb_ViewWidget.addItem(self.xy_cb)
        
    
#    def update_xy_refocusrange(self):
#        print('set xy refra')
#        self._tracker_logic.refocus_XY_size = float(self._sw.xy_refocusrange_InputWidget.text())
#        
#    def update_xy_refocusstepsize(self):
#        print('set xy refst')
#        self._tracker_logic.refocus_XY_step = float(self._sw.xy_refocusstepsize_InputWidget.text())
#        
#    def update_z_refocusrange(self):
#        print('set z refra')
#        self._tracker_logic.refocus_Z_size = float(self._sw.z_refocusrange_InputWidget.text())
#        
#    def update_z_refocusstepsize(self):
#        print('set z refst')
#        self._tracker_logic.refocus_Z_step = float(self._sw.z_refocusstepsize_InputWidget.text())
    
    
    def menue_settings(self):
        self._sw.exec_()

    
    def refresh_xy_image(self):
        self.xy_refocus_image.setImage(image=self._tracker_logic.xy_refocus_image[:,:,3].transpose())
#        self.xy_refocus_image.setRect(QtCore.QRectF(self._tracker_logic.x_range[0], self._tracker_logic.y_range[0], self._tracker_logic.x_range[1]-self._tracker_logic.x_range[0], self._tracker_logic.y_range[1]-self._tracker_logic.y_range[0]))
#        self.xy_refocus_image.setRect(QtCore.QRectF(self._tracker_logic._X_values[0], self._tracker_logic._Y_values[0], self._tracker_logic._X_values[1]-self._tracker_logic._X_values[0], self._tracker_logic._Y_values[1]-self._tracker_logic._Y_values[0]))        
        self.xy_refocus_image.setRect(QtCore.QRectF(self._tracker_logic._trackpoint_x - 0.5 * self._tracker_logic.refocus_XY_size , self._tracker_logic._trackpoint_y - 0.5 * self._tracker_logic.refocus_XY_size , self._tracker_logic.refocus_XY_size, self._tracker_logic.refocus_XY_size))               
        self.vLine.setValue(self._tracker_logic.refocus_x)
        print('set vline to', self._tracker_logic.refocus_x)
        self.hLine.setValue(self._tracker_logic.refocus_y)
        print('set hline to', self._tracker_logic.refocus_y)
        self.refresh_xy_colorbar()
#        if self._tracker_logic.getState() != 'locked':
#            self.signal_refocus_finished.emit()
        
    def refresh_z_image(self):
        self.xz_refocus_image.setData(self._tracker_logic._zimage_Z_values,self._tracker_logic.z_refocus_line)
        self.xz_refocus_fit_image.setData(self._tracker_logic._zimage_Z_values,self._tracker_logic.z_fit_data)
#        if self._tracker_logic.getState() != 'locked':
#            self.signal_refocus_finished.emit()
