# -*- coding: utf-8 -*-



# Form implementation generated from reading ui file 'ConfocalWindowTemplate.ui'
#
# Created: Thu Apr 23 09:28:53 2015
#      by: PyQt4 UI code generator 4.10.4
#
# WARNING! All changes made in this file will be lost!

#from PyQt4 import QtCore, QtGui
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph as pg

from collections import OrderedDict
from core.Base import Base
import numpy as np

# To convert the *.ui file to a raw ConfocalGuiUI.py file use the python script
# in the Anaconda directory, which you can find in:
#
# "<Installation-dir of Anacona>\Anaconda3\Lib\site-packages\PyQt4\uic\pyuic.py".
#
# Then use that script like
#
# "<Installation-dir of Anacona>\Anaconda3\Lib\site-packages\PyQt4\uic\pyuic.py" ConfocalWindowTemplate.ui > ConfocalGui_ui.py
#
# to convert to ConfocalGuiUI.py.
from gui.Confocal.ConfocalGuiUI import Ui_MainWindow




class CrossROI(pg.ROI):
    """Create a Region of interest, which is a zoomable rectangular. """
    
    def __init__(self, pos, size, **args):
        pg.ROI.__init__(self, pos, size, **args)
        center = [0.5, 0.5]    
        self.addTranslateHandle(center)


class CrossLine(pg.InfiniteLine):
    """ Construct one line for the Crosshair in th plot.

      @param float pos: optional parameter to set the position
      @param float angle: optional parameter to set the angle of the line
      @param dict pen: Configure the pen.

      For additional options consider the documentation of pyqtgraph.InfiniteLine

    """
    def __init__(self, **args):
        pg.InfiniteLine.__init__(self, **args)

    def adjust(self, extroi):
        """
        Run this function to adjust the position of the Crosshair-Line
        """
        if self.angle == 0:
            self.setValue(extroi.pos()[1] + extroi.size()[1] * 0.5 )
        if self.angle == 90:
            self.setValue(extroi.pos()[0] + extroi.size()[0] * 0.5 )

    def set_x(self,value):
        self.setValue(value)


class ConfocalMainWindow(QtGui.QMainWindow,Ui_MainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.setupUi(self)
        
        

class ConfocalGui(Base,QtGui.QMainWindow,Ui_MainWindow):
    """
    Main Confocal Class for xy and xz scans
    """
    sigStartCounter = QtCore.Signal()
    sigStopCounter = QtCore.Signal()

    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        c_dict = {'onactivate': self.initUI}
        Base.__init__(self,
                    manager,
                    name,
                    config,
                    c_dict)
        
        self._modclass = 'ConfocalGui'
        self._modtype = 'gui'
        
        ## declare connectors
        self.connector['in']['confocallogic1'] = OrderedDict()
        self.connector['in']['confocallogic1']['class'] = 'ConfocalLogic'
        self.connector['in']['confocallogic1']['object'] = None

        self.logMsg('The following configuration was found.', 
                    msgType='status')
                            
        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]), 
                        msgType='status')                      

    def initUI(self, e=None):
        """ Definition and initialisation of the GUI plus staring the measurement.

        Configure and         
        
        """
         
        self._scanning_logic = self.connector['in']['confocallogic1']['object']
        print("Scanning logic is", self._scanning_logic)
        
        # Use the inherited class 'Ui_ConfocalGuiTemplate' to create now the 
        # GUI element:
        self._mw = ConfocalMainWindow()
        
        arr = np.ones((200, 200), dtype=float)
        arr[45:55, 45:55] = 0
        arr[25, :] = 5
        arr[:, 25] = 5
        arr[75, :] = 5
        arr[:, 75] = 5
        arr[50, :] = 10
        arr[:, 50] = 10
        arr += np.sin(np.linspace(0, 20, 200)).reshape(1, 200)
        arr += np.random.normal(size=(200,200))
#
#        self.xy_image = pg.ImageItem(arr)
#        self._mw.graphicsView.addItem(self.xy_image)
#        
#        # create Region of Interest
#        
#        cr = CrossROI([100, 100], [10, 10], pen={'color': "00F", 'width': 1},removable=True )
#        
#        self._mw.graphicsView.addItem(cr)
#        
#        self._mw.graphicsView.enableMouse = False        
#        
#        ilh = CrossLine(pos=cr.pos()+cr.size()*0.5, angle=0, pen={'color': "00F", 'width': 1} )
#        ilv = CrossLine(pos=cr.pos()+cr.size()*0.5, angle=90, pen={'color': "00F", 'width': 1} )
#
#
#        cr.sigRegionChanged.connect(ilh.adjust)
#        cr.sigRegionChanged.connect(ilv.adjust)
#
#        self._mw.graphicsView.addItem(ilh)
#        self._mw.graphicsView.addItem(ilv)
#
#
#        cr2 = CrossROI([100, 100], [20, 20], pen={'color': "00F", 'width': 1},removable=True )
#
#        self._mw.graphicsView_2.addItem(cr2)
#
#        ilh2 = CrossLine(pos=cr2.pos()+cr.size()*0.5, angle=0, pen={'color': "00F", 'width': 1} )
#        ilv2 = CrossLine(pos=cr2.pos()+cr.size()*0.5, angle=90, pen={'color': "00F", 'width': 1} )
#
#        cr2.sigRegionChanged.connect(ilh2.adjust)
#        cr2.sigRegionChanged.connect(ilv2.adjust)
#
#        self._mw.graphicsView_2.addItem(ilh2)
#        self._mw.graphicsView_2.addItem(ilv2)

        self.xy_image = pg.ImageItem(arr)
        self.xz_image = pg.ImageItem(arr)
        self._mw.xy_ViewWidget.addItem(self.xy_image)
        self._mw.xz_ViewWidget.addItem(self.xz_image)
        
        
        # create Region of Interest for xy image:
        self.roi_xy = CrossROI([100, 100], [10, 10], pen={'color': "00F", 'width': 1},removable=True )
        
        # Add to the xy Image Widget
        self._mw.xy_ViewWidget.addItem(self.roi_xy)
        
        # create horizontal and vertical line in xy image
        self.hline_xy = CrossLine(pos=self.roi_xy.pos()+self.roi_xy.size()*0.5, angle= 0, pen={'color': "00F", 'width': 1} )
        self.vline_xy = CrossLine(pos=self.roi_xy.pos()+self.roi_xy.size()*0.5, angle=90, pen={'color': "00F", 'width': 1} )

        # connect the change of a region with the adjustment of the crosshair
        self.roi_xy.sigRegionChanged.connect(self.hline_xy.adjust)
        self.roi_xy.sigRegionChanged.connect(self.vline_xy.adjust)

        self.roi_xy.sigRegionChanged.connect(self.slider_x_adjust)
        self.roi_xy.sigRegionChanged.connect(self.slider_y_adjust)

        # add the configured crosshair to the xy Widget
        self._mw.xy_ViewWidget.addItem(self.hline_xy)
        self._mw.xy_ViewWidget.addItem(self.vline_xy)

        # create Region of Interest for xz image:
        self.roi_xz = CrossROI([100, 100], [20, 20], pen={'color': "00F", 'width': 1},removable=True )

        # Add to the xy Image Widget
        self._mw.xz_ViewWidget.addItem(self.roi_xz)

        self.hline_xz = CrossLine(pos=self.roi_xz.pos()+self.roi_xz.size()*0.5, angle=0, pen={'color': "00F", 'width': 1} )
        self.vline_xz = CrossLine(pos=self.roi_xz.pos()+self.roi_xz.size()*0.5, angle=90, pen={'color': "00F", 'width': 1} )

        self.roi_xz.sigRegionChanged.connect(self.hline_xz.adjust)
        self.roi_xz.sigRegionChanged.connect(self.vline_xz.adjust)
        
        self.roi_xz.sigRegionChanged.connect(self.slider_x_adjust)
        self.roi_xz.sigRegionChanged.connect(self.slider_z_adjust)        
        
        self._mw.xz_ViewWidget.addItem(self.hline_xz)
        self._mw.xz_ViewWidget.addItem(self.vline_xz)        
        

        
        # Set a Range for the sliders:
        self._mw.x_SliderWidget.setRange(0,200)
        self._mw.y_SliderWidget.setRange(0,200) 
        self._mw.z_SliderWidget.setRange(0,200)

        
        self._mw.x_SliderWidget.valueChanged.connect(self.roi_xy_change_x)
        self._mw.y_SliderWidget.valueChanged.connect(self.roi_xy_change_y)

        self._mw.x_SliderWidget.valueChanged.connect(self.roi_xz_change_x)
        self._mw.z_SliderWidget.valueChanged.connect(self.roi_xz_change_z)

        #self._mw.x_SliderWidget.valueChanged.connect(stwo.setValue)        
        self._mw.x_current_InputWidget.setText(str(0.0))        
        
        # Add to the QLineEdit Widget a Double Validator to ensure only a 
        # float input.
        validator = QtGui.QDoubleValidator()
        self._mw.x_current_InputWidget.setValidator(validator)
        self._mw.y_current_InputWidget.setValidator(validator)
        self._mw.z_current_InputWidget.setValidator(validator)

        self._mw.x_SliderWidget.valueChanged.connect(self.update_current_x)
        self._mw.y_SliderWidget.valueChanged.connect(self.update_current_y)
        self._mw.z_SliderWidget.valueChanged.connect(self.update_current_z)
        #self.x_current_InputWidget


        print('Main Confocal Windows shown:')
        self._mw.show()
        
        #self._mw.x_SliderWidget.SliderChange.connect()
        
        #print(dir(self._mw.x_SliderWidget))


    def roi_xy_change_x(self,x_pos):
        self.roi_xy.setPos([x_pos,self.roi_xy.pos()[1]])
        
    def roi_xy_change_y(self,y_pos):
        self.roi_xy.setPos([self.roi_xy.pos()[0],y_pos])        
        
    def roi_xz_change_x(self,x_pos):
        self.roi_xz.setPos([x_pos,self.roi_xz.pos()[1]])

    def roi_xz_change_z(self,z_pos):
        self.roi_xz.setPos([self.roi_xz.pos()[0],z_pos])
        
    def slider_x_adjust(self,roi):
        self._mw.x_SliderWidget.setValue(roi.pos()[0])

    def slider_y_adjust(self,roi):
        self._mw.y_SliderWidget.setValue(roi.pos()[1])

    def slider_z_adjust(self,roi):
        self._mw.z_SliderWidget.setValue(roi.pos()[1])
        
    def update_current_x(self,text):
        self._mw.x_current_InputWidget.setText(str(text))
        
    def update_current_y(self,text):
        self._mw.y_current_InputWidget.setText(str(text))        
    
    def update_current_z(self,text):
        self._mw.z_current_InputWidget.setText(str(text))   