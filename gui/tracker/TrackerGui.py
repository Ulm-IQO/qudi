# -*- coding: utf-8 -*-
"""
Created on Mon Apr 27 17:54:58 2015

@author: user-admin
"""

from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph as pg

from collections import OrderedDict
from core.Base import Base
from gui.Tracker.TrackerGuiUI import Ui_MainWindow
# To convert the *.ui file to a raw ConfocalGuiUI.py file use the python script
# in the Anaconda directory, which you can find in:
#
# "<Installation-dir of Anacona>\Anaconda3\Lib\site-packages\PyQt4\uic\pyuic.py".
#
# Then use that script like
#
# "<Installation-dir of Anacona>\Anaconda3\Lib\site-packages\PyQt4\uic\pyuic.py" ConfocalWindowTemplate.ui > ConfocalGuiUI.py
#
# to convert to ConfocalGuiUI.py.




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
        
        # Get the image for the display from the logic:
        arr01 = self._tracker_logic.xy_refocus_image[:,:,3]
        arr02 = self._tracker_logic.z_refocus_line


        # Load the image in the display:
        self.xy_refocus_image = pg.ImageItem(arr01)
        self.xy_refocus_image.setRect(QtCore.QRectF(0, 0, 100, 100))
        self.xz_refocus_image = pg.PlotDataItem(arr02)
#        self.xz_refocus_image.setRect(QtCore.QRectF(0, 0, 100, 100))
        
        # Add the display item to the xy and xz VieWidget, which was defined in
        # the UI file.
        self._mw.xy_refocus_ViewWidget.addItem(self.xy_refocus_image)
        self._mw.xz_refocus_ViewWidget.addItem(self.xz_refocus_image)
        
        self._tracker_logic.signal_xy_image_updated.connect(self.refresh_xy_image)
        self._tracker_logic.signal_z_image_updated.connect(self.refresh_z_image)
        
        print('Main Tracker Windows shown:')
        self._mw.show()
        
    def refresh_xy_image(self):
        self.xy_refocus_image.setImage(image=self._tracker_logic.xy_refocus_image[:,:,3])
#        if self._tracker_logic.getState() != 'locked':
#            self.signal_refocus_finished.emit()
        
    def refresh_z_image(self):
        self.xz_refocus_image.setImage(image=self._tracker_logic.z_refocus_line)
#        if self._tracker_logic.getState() != 'locked':
#            self.signal_refocus_finished.emit()
