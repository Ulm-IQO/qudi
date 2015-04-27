# -*- coding: utf-8 -*-



#from PyQt4 import QtCore, QtGui
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph as pg

from collections import OrderedDict
from core.Base import Base
from gui.Confocal.ConfocalGuiUI import Ui_MainWindow
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

        self.connector['in']['savelogic'] = OrderedDict()
        self.connector['in']['savelogic']['class'] = 'SaveLogic'
        self.connector['in']['savelogic']['object'] = None

        self.logMsg('The following configuration was found.', 
                    msgType='status')
                            
        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]), 
                        msgType='status')  

    def initUI(self, e=None):
        """ Definition, configuration and initialisation of the confocal GUI.
          
          @param class e: event class from Fysom


        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules.
        
        """
        
        self._scanning_logic = self.connector['in']['confocallogic1']['object']
        print("Scanning logic is", self._scanning_logic)
        
        self._save_logic = self.connector['in']['savelogic']['object']
        print("Save logic is", self._save_logic)  
        
        # Use the inherited class 'Ui_ConfocalGuiTemplate' to create now the 
        # GUI element:
        self._mw = ConfocalMainWindow()
        
        # Get the image for the display from the logic: 
        arr01 = self._scanning_logic.xy_image[:,:,3]
        arr02 = self._scanning_logic.xz_image[:,:,3]

        # Set initial position for the crosshair, default is the middle of the
        # screen:
        ini_pos_x_crosshair = len(arr01)/2
        ini_pos_y_crosshair = len(arr01)/2
        ini_pos_z_crosshair = len(arr02)/2
        
        # Load the image in the display:
        self.xy_image = pg.ImageItem(arr01)
        self.xz_image = pg.ImageItem(arr02)
        
        # Add the display item to the xy and xz VieWidget, which was defined in
        # the UI file.
        self._mw.xy_ViewWidget.addItem(self.xy_image)
        self._mw.xz_ViewWidget.addItem(self.xz_image)
        
        # Create Region of Interest for xy image:
        self.roi_xy = CrossROI([ini_pos_x_crosshair, ini_pos_y_crosshair], [len(arr01)/20, len(arr01)/20], pen={'color': "00F", 'width': 1},removable=True )
        # self.roi_xy = CrossROI([100, 100], [10, 10], pen={'color': "00F", 'width': 1},removable=True )
        
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
        
        # Some additional settings for the xy ViewWidget
        self._mw.xy_ViewWidget.setMouseEnabled(x=False,y=False)
        self._mw.xy_ViewWidget.disableAutoRange()
        self._mw.xy_ViewWidget.setAspectLocked(lock=True, ratio=1) 

        # create Region of Interest for xz image:
        self.roi_xz = CrossROI([ini_pos_x_crosshair, ini_pos_z_crosshair], [len(arr02)/20, len(arr02)/20], pen={'color': "00F", 'width': 1},removable=True )
        # self.roi_xz = CrossROI([100, 100], [20, 20], pen={'color': "00F", 'width': 1},removable=True )

        # Add to the xz Image Widget
        self._mw.xz_ViewWidget.addItem(self.roi_xz)

        self.hline_xz = CrossLine(pos=self.roi_xz.pos()+self.roi_xz.size()*0.5, angle=0, pen={'color': "00F", 'width': 1} )
        self.vline_xz = CrossLine(pos=self.roi_xz.pos()+self.roi_xz.size()*0.5, angle=90, pen={'color': "00F", 'width': 1} )

        self.roi_xz.sigRegionChanged.connect(self.hline_xz.adjust)
        self.roi_xz.sigRegionChanged.connect(self.vline_xz.adjust)
        
        self.roi_xz.sigRegionChanged.connect(self.slider_x_adjust)
        self.roi_xz.sigRegionChanged.connect(self.slider_z_adjust)        
        
        self._mw.xz_ViewWidget.addItem(self.hline_xz)
        self._mw.xz_ViewWidget.addItem(self.vline_xz)

        # Some additional settings for the xz ViewWidget
        self._mw.xz_ViewWidget.setMouseEnabled(x=False,y=False)
        self._mw.xz_ViewWidget.disableAutoRange()
        self._mw.xz_ViewWidget.setAspectLocked(lock=True, ratio=1)        
        
        self._mw.x_SliderWidget.setSingleStep(0.01)
       
        
        # Set a Range for the sliders:
        self._mw.x_SliderWidget.setRange(self._scanning_logic.x_range[0],self._scanning_logic.x_range[1])
        
        self._mw.y_SliderWidget.setRange(float(self._scanning_logic.y_range[0]),float(self._scanning_logic.y_range[1]))
        self._mw.z_SliderWidget.setRange(self._scanning_logic.z_range[0],self._scanning_logic.z_range[1])

        # Connect to maximal and minimal range:
        self._mw.x_min_InputWidget.setText(str(self._scanning_logic.image_x_range[0]))
        self._mw.x_max_InputWidget.setText(str(self._scanning_logic.image_x_range[1]))
        self._mw.y_min_InputWidget.setText(str(self._scanning_logic.image_y_range[0]))
        self._mw.y_max_InputWidget.setText(str(self._scanning_logic.image_y_range[1]))
        self._mw.z_min_InputWidget.setText(str(self._scanning_logic.image_z_range[0]))
        self._mw.z_max_InputWidget.setText(str(self._scanning_logic.image_z_range[1]))
 

        # Define what happend if the slider change the value: then adjust that
        # change for the region of interest.

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
        
        self._mw.x_min_InputWidget.setValidator(validator)
        self._mw.x_max_InputWidget.setValidator(validator)
        self._mw.y_min_InputWidget.setValidator(validator)
        self._mw.y_max_InputWidget.setValidator(validator)
        self._mw.z_min_InputWidget.setValidator(validator)
        self._mw.z_max_InputWidget.setValidator(validator)
        
        self._mw.xy_res_InputWidget.setValidator(validator)
        self._mw.z_res_InputWidget.setValidator(validator)

        #take the default values for resolutions from logic:
        self._mw.xy_res_InputWidget.setText(str(self._scanning_logic.xy_resolution))     
        self._mw.z_res_InputWidget.setText(str(self._scanning_logic.z_resolution))   
        
        # Connect the Slider with an update in the current values of x
        self._mw.x_SliderWidget.valueChanged.connect(self.update_current_x)
        self._mw.y_SliderWidget.valueChanged.connect(self.update_current_y)
        self._mw.z_SliderWidget.valueChanged.connect(self.update_current_z)

        # Update the inputed/displayed numbers if return key is hit:

        self._mw.x_current_InputWidget.returnPressed.connect(self.update_x_slider)
        self._mw.x_current_InputWidget.returnPressed.connect(self.update_y_slider)
        self._mw.z_current_InputWidget.returnPressed.connect(self.update_z_slider)
        
        self._mw.xy_res_InputWidget.returnPressed.connect(self.update_xy_resolution)
        self._mw.z_res_InputWidget.returnPressed.connect(self.update_z_resolution)
        
        self._mw.x_min_InputWidget.returnPressed.connect(self.change_x_image_range)
        self._mw.x_max_InputWidget.returnPressed.connect(self.change_x_image_range)
        self._mw.y_min_InputWidget.returnPressed.connect(self.change_y_image_range)
        self._mw.y_max_InputWidget.returnPressed.connect(self.change_y_image_range)
        self._mw.z_min_InputWidget.returnPressed.connect(self.change_z_image_range)
        self._mw.z_max_InputWidget.returnPressed.connect(self.change_z_image_range)
        
        # Declare for which fields changes are applied if the cursor is leaving
        # the field:

        self._mw.x_current_InputWidget.editingFinished.connect(self.update_x_slider)
        self._mw.y_current_InputWidget.editingFinished.connect(self.update_y_slider)
        self._mw.z_current_InputWidget.editingFinished.connect(self.update_z_slider)

        self._mw.xy_res_InputWidget.editingFinished.connect(self.update_xy_resolution)
        self._mw.z_res_InputWidget.editingFinished.connect(self.update_z_resolution)
        
        self._mw.x_min_InputWidget.editingFinished.connect(self.change_x_image_range)
        self._mw.x_max_InputWidget.editingFinished.connect(self.change_x_image_range)
        self._mw.y_min_InputWidget.editingFinished.connect(self.change_y_image_range)
        self._mw.y_max_InputWidget.editingFinished.connect(self.change_y_image_range)
        self._mw.z_min_InputWidget.editingFinished.connect(self.change_z_image_range)
        self._mw.z_max_InputWidget.editingFinished.connect(self.change_z_image_range)        
        
        
        # Connect the RadioButtons and connect to the event if they are touched:
        
        self._mw.ready_StateWidget.toggled.connect(self.ready_clicked)
        self._mw.xy_scan_StateWidget.toggled.connect(self.xy_scan_clicked)
        self._mw.xz_scan_StateWidget.toggled.connect(self.xz_scan_clicked)
#        self._mw.refocus_StateWidget.toggled.connect(self.refocus_clicked)


        self._scanning_logic.signal_image_updated.connect(self.refresh_image)
        #self._scanning_logic.signal_scan_lines_next.connect(self.refresh_image)
        print('Main Confocal Windows shown:')
        self._mw.show()
        
        # Now that the ROI is connected to events, set again to initial pos:        
        self.roi_xy.setPos([ini_pos_x_crosshair+0.001, ini_pos_y_crosshair+0.001]) 
        # Now that the ROI is connected to events, set again to initial pos:        
        self.roi_xz.setPos([ini_pos_x_crosshair+0.001, ini_pos_y_crosshair+0.001])          


    def ready_clicked(self):
        pass

            
    def xy_scan_clicked(self, enabled):
        self._scanning_logic.stop_scanning()
        if enabled:
            self._scanning_logic.stop_scanning()
            self._scanning_logic.start_scanning()
            
    def xz_scan_clicked(self, enabled):
        self._scanning_logic.stop_scanning()
        if enabled:
            self._scanning_logic.start_scanning(zscan = True)
            
#    def refocus_clicked(self, enabled):
#        self._scanning_logic.stop_scanning()
#        if enabled:
            
   
   
    def roi_xy_change_x(self,x_pos):
        self.roi_xy.setPos([x_pos,self.roi_xy.pos()[1]])
        self._scanning_logic.set_position(x=x_pos)
        
    def roi_xy_change_y(self,y_pos):
        self.roi_xy.setPos([self.roi_xy.pos()[0],y_pos])        
        self._scanning_logic.set_position(y=y_pos) 
        
    def roi_xz_change_x(self,x_pos):
        self.roi_xz.setPos([x_pos,self.roi_xz.pos()[1]])
        self._scanning_logic.set_position(x=x_pos) 

    def roi_xz_change_z(self,z_pos):
        self.roi_xz.setPos([self.roi_xz.pos()[0],z_pos])
        self._scanning_logic.set_position(z=z_pos)       
        
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
        
    def update_x_slider(self):
        self._mw.x_SliderWidget.setValue(float(self._mw.x_current_InputWidget.text()))
        
    def update_y_slider(self):
        self._mw.y_SliderWidget.setValue(float(self._mw.y_current_InputWidget.text()))
        
    def update_z_slider(self):
        self._mw.z_SliderWidget.setValue(float(self._mw.z_current_InputWidget.text()))  
        
    def update_xy_resolution(self):
        self._scanning_logic.set_position(float(self._mw.xy_res_InputWidget.text()))
        print(self._mw.xy_res_InputWidget.text())
        
    def update_z_resolution(self):
        self._scanning_logic.set_position(float(self._mw.z_res_InputWidget.text()))
        print(self._mw.z_res_InputWidget.text())
    
    def change_x_image_range(self):
        self._scanning_logic.image_x_range = [float(self._mw.x_min_InputWidget.text()), float(self._mw.x_max_InputWidget.text())]
        
    def change_y_image_range(self):
        self._scanning_logic.image_y_range = [float(self._mw.y_min_InputWidget.text()), float(self._mw.y_max_InputWidget.text())]
        
    def change_z_image_range(self):
        self._scanning_logic.image_z_range = [float(self._mw.z_min_InputWidget.text()), float(self._mw.z_max_InputWidget.text())]
        
    def refresh_image(self):
        if self._mw.xy_scan_StateWidget.isChecked():
            self.xy_image.setImage(image=self._scanning_logic.xy_image[:,:,3])
        elif self._mw.xz_scan_StateWidget.isChecked():
            self.xz_image.setImage(image=self._scanning_logic.xz_image[:,:,3])
        
        if self._scanning_logic.getState() != 'locked':
            self._mw.ready_StateWidget.click()
        