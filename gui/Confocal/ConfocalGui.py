# -*- coding: utf-8 -*-



#from PyQt4 import QtCore, QtGui
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph as pg
import numpy as np

from collections import OrderedDict
from core.Base import Base
from gui.Confocal.ConfocalGuiUI import Ui_MainWindow
from gui.Confocal.ConfocalSettingsUI import Ui_SettingsDialog

# ============= HowTo Convert the corresponding *.ui file =====================
# To convert the *.ui file to a raw ConfocalGuiUI.py file use the python script
# in the Anaconda directory, which you can find in:
#
# "<Installation-dir of Anacona>\Anaconda3\Lib\site-packages\PyQt4\uic\pyuic.py".
#
# Then use that script like
#
# "<Installation-dir of Anacona>\Anaconda3\Lib\site-packages\PyQt4\uic\pyuic.py" ConfocalGuiUI.ui > ConfocalGuiUI.py
#
# to convert to ConfocalGuiUI.py.
# =============================================================================





class ColorBar(pg.GraphicsObject):
    """ Create a ColorBar according to a previously defined color map.
        
    @param cmap pyqtgraph colormap object: a defined colormap
    @param float width: width of the colorbar in x direction, starting from
                        the origin.
    @param float height: height of the colorbar in y direction, starting 
                         from the origin.
    @param numpy array ticks: optional, definition of the relative ticks marks
    @param string tick_labels: optional, a c-like format definition for the output of
                               the ticks.
    @param string label: optional, label for the colorbar.
    """    
    def __init__(self, cmap, width, height, ticks=None, tick_labels=None,
                 label=None):

        pg.GraphicsObject.__init__(self)
         
        # handle the passed arguments:
        label = label or ''
        w, h = width, height
        stops, colors = cmap.getStops('float')
        smn, spp = stops.min(), stops.ptp()
        stops = (stops - stops.min())/stops.ptp()
        if ticks is None:
            ticks = np.r_[0.0:1.0:5j] * spp + smn
        tick_labels = tick_labels or ["%0.2g" % (t,) for t in ticks]
 
        # setup picture
        self.pic = pg.QtGui.QPicture()
        p = pg.QtGui.QPainter(self.pic)
 
        # draw bar with gradient following colormap
        p.setPen(pg.mkPen('k'))
        grad = pg.QtGui.QLinearGradient(w/2.0, 0.0, w/2.0, h*1.0)
        for stop, color in zip(stops, colors):
            grad.setColorAt(1.0 - stop, pg.QtGui.QColor(*[255*c for c in color]))
        p.setBrush(pg.QtGui.QBrush(grad))
        p.drawRect(pg.QtCore.QRectF(0, 0, w, h))
 
        # draw ticks & tick labels
        mintx = 0.0
        for tick, tick_label in zip(ticks, tick_labels):
            y_ = (1.0 - (tick - smn)/spp) * h
            p.drawLine(0.0, y_, -5.0, y_)
            br = p.boundingRect(0, 0, 0, 0, pg.QtCore.Qt.AlignRight, tick_label)
            if br.x() < mintx:
                mintx = br.x()
            p.drawText(br.x() - 10.0, y_ + br.height() / 4.0, tick_label)
 
        # draw label
        br = p.boundingRect(0, 0, 0, 0, pg.QtCore.Qt.AlignRight, label)
        p.drawText(-br.width() / 2.0, h + br.height() + 5.0, label)
        
        # done
        p.end()
 
        # compute rect bounds for underlying mask
        self.zone = mintx - 12.0, -15.0, br.width() - mintx, h + br.height() + 30.0


    def paint(self, p, *args):
        """ Paint the underlying mask.

        @param object p: a pyqtgraph.QtGui.QPainter object, which is used to 
                         set the color of the pen.
        """        
        p.setPen(pg.QtGui.QColor('#222'))
        p.setBrush(pg.QtGui.QColor('#222'))
        p.drawRoundedRect(*(self.zone + (9.0, 9.0)))
        
        # paint colorbar
        p.drawPicture(0, 0, self.pic)


    def boundingRect(self):
        """ Get the position, width and hight of the displayed object.
        """
        return pg.QtCore.QRectF(self.pic.boundingRect())

#FIXME: A refresh function for the colorbar has to be implemented!

class CustomViewBox(pg.ViewBox):
    """ Predefine the view region and set what interaction are allowed. 
    
        Test to create a custom ViewBox and add that to the plot items in order
        to enable a zoom box with the right mouse click, while holding the 
        Control Key. Right now it is not working with that GUI configuration.
        It has to be figured out how to include the ViewBox.
    
    """
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
    """ Create a Region of interest, which is a zoomable rectangular. 
    
    @param float pos: optional parameter to set the position
    @param float size: optional parameter to set the size of the roi
    
    Have a look at: 
    http://www.pyqtgraph.org/documentation/graphicsItems/roi.html    
    """    
    def __init__(self, pos, size, **args):
        pg.ROI.__init__(self, pos, size, **args)
        # That is a relative position of the small box inside the region of 
        # interest, where 0 is the lowest value and 1 is the higherst:
        center = [0.5,0.5]
        # Translate the center to the intersection point of the crosshair.
        self.addTranslateHandle(center)


class CrossLine(pg.InfiniteLine):
    """ Construct one line for the Crosshair in the plot.

    @param float pos: optional parameter to set the position
    @param float angle: optional parameter to set the angle of the line
    @param dict pen: Configure the pen.

    For additional options consider the documentation of pyqtgraph.InfiniteLine
    """    
    def __init__(self, **args):
        pg.InfiniteLine.__init__(self, **args)
#        self.setPen(QtGui.QPen(QtGui.QColor(255, 0, 255),0.5))


    def adjust(self, extroi):
        """
        Run this function to adjust the position of the Crosshair-Line
    
        @param object extroi: external roi object from pyqtgraph
        """
        if self.angle == 0:
            self.setValue(extroi.pos()[1] + extroi.size()[1] * 0.5 )
        if self.angle == 90:
            self.setValue(extroi.pos()[0] + extroi.size()[0] * 0.5 )
        

class ConfocalMainWindow(QtGui.QMainWindow,Ui_MainWindow):
    """Create the Mainwindow based on the *.ui file.
    """
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.setupUi(self)
        
        
class ConfocalSettingDialog(QtGui.QDialog,Ui_SettingsDialog):
    def __init__(self):
        QtGui.QDialog.__init__(self)
        self.setupUi(self)
        

class ConfocalGui(Base,QtGui.QMainWindow,Ui_MainWindow):
    """ Main Confocal Class for xy and xz scans.
    """
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
        
        self.connector['in']['optimiserlogic1'] = OrderedDict()
        self.connector['in']['optimiserlogic1']['class'] = 'OptimiserLogic'
        self.connector['in']['optimiserlogic1']['object'] = None

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
        Moreover it sets default values.
        """
        #FIXME: can we delete all the commented stuff in this method?
        
        # Getting an access to all connectors:
        self._scanning_logic = self.connector['in']['confocallogic1']['object']
        self._save_logic = self.connector['in']['savelogic']['object']
        self._optimiser_logic = self.connector['in']['optimiserlogic1']['object']
        
        # Use the inherited class 'Ui_ConfocalGuiTemplate' to create now the 
        # GUI element:
        self._mw = ConfocalMainWindow()
        self._sd = ConfocalSettingDialog()
        
        # Get the image for the display from the logic. Transpose the received
        # matrix to get the proper scan. The graphig widget displays vector-
        # wise the lines and the lines are normally columns, but in our 
        # measurement we scan rows per row. That's why it has to be transposed.
        arr01 = self._scanning_logic.xy_image[:,:,3].transpose()
        arr02 = self._scanning_logic.xz_image[:,:,3].transpose()

        # Set initial position for the crosshair, default is the middle of the
        # screen:
        ini_pos_x_crosshair = len(arr01)/2
        ini_pos_y_crosshair = len(arr01)/2
        ini_pos_z_crosshair = len(arr02)/2

        # parameters for the signal proxy:
#        eventlimit = 0.01 # in signals per second
#        delay_sig = 0.4  # delay of the signal in seconds
        
        
        # Load the images for xy and xz in the display:
        self.xy_image = pg.ImageItem(arr01)
        self.xy_image.setRect(QtCore.QRectF(self._scanning_logic.image_x_range[0], 
                                            self._scanning_logic.image_y_range[0], 
                                            self._scanning_logic.image_x_range[1]-self._scanning_logic.image_x_range[0], 
                                            self._scanning_logic.image_y_range[1]-self._scanning_logic.image_y_range[0]))
        
        self.xz_image = pg.ImageItem(arr02)
        self.xz_image.setRect(QtCore.QRectF(self._scanning_logic.image_x_range[0], 
                                            self._scanning_logic.image_z_range[0], 
                                            self._scanning_logic.image_x_range[1]-self._scanning_logic.image_x_range[0], 
                                            self._scanning_logic.image_z_range[1]-self._scanning_logic.image_z_range[0]))
        
        # Set the state button as ready button as default setting.
        self._mw.ready_StateWidget.click()

        # Add the display item to the xy and xz ViewWidget, which was defined 
        # in the UI file:
        self._mw.xy_ViewWidget.addItem(self.xy_image)
        self._mw.xz_ViewWidget.addItem(self.xz_image)
    
        # Create Region of Interest for xy image and add to xy Image Widget:
        self.roi_xy = CrossROI([ini_pos_x_crosshair, ini_pos_y_crosshair], 
                               [len(arr01), len(arr01)], 
                               pen={'color': "F0F", 'width': 1}, 
                               removable=True)
        self._mw.xy_ViewWidget.addItem(self.roi_xy)
        
        # create horizontal and vertical line as a crosshair in xy image:
        self.hline_xy = CrossLine(pos=self.roi_xy.pos()+self.roi_xy.size()*0.5, 
                                  angle= 0, pen={'color': "F0F", 'width': 1} )
        self.vline_xy = CrossLine(pos=self.roi_xy.pos()+self.roi_xy.size()*0.5, 
                                  angle=90, pen={'color': "F0F", 'width': 1} )

        # connect the change of a region with the adjustment of the crosshair:
        self.roi_xy.sigRegionChanged.connect(self.hline_xy.adjust)
        self.roi_xy.sigRegionChanged.connect(self.vline_xy.adjust)


        # connect the change of a region with the adjustment of the sliders:
        # the proxy signals for that:
#        self.proxy_roi_xy_to_slider_x = pg.SignalProxy(self.roi_xy.sigRegionChanged, 
#                                                       delay=delay_sig, 
#                                                       rateLimit=eventlimit, 
#                                                       slot=self.slider_x_adjust)
#        self.proxy_roi_xy_to_slider_y = pg.SignalProxy(self.roi_xy.sigRegionChanged, 
#                                                       delay=delay_sig, 
#                                                       rateLimit=eventlimit, 
#                                                       slot=self.slider_y_adjust)
        # the normal signal connection for that:
        self.roi_xy.sigRegionChanged.connect(self.slider_x_adjust)
        self.roi_xy.sigRegionChanged.connect(self.slider_y_adjust)

        # add the configured crosshair to the xy Widget
        self._mw.xy_ViewWidget.addItem(self.hline_xy)
        self._mw.xy_ViewWidget.addItem(self.vline_xy)
        
        # Some additional settings for the xy ViewWidget
        self._mw.xy_ViewWidget.setMouseEnabled(x=False,y=False)
        self._mw.xy_ViewWidget.enableAutoRange()
#        self._mw.xy_ViewWidget.setAspectLocked(lock=True, ratio=1) 

        # Create Region of Interest for xz image and add to xy Image Widget:
        self.roi_xz = CrossROI([ini_pos_x_crosshair, ini_pos_z_crosshair], 
                               [len(arr02)/10, len(arr02)/10], 
                               pen={'color': "F0F", 'width': 1},
                               removable=True )
        self._mw.xz_ViewWidget.addItem(self.roi_xz)

        # create horizontal and vertical line as a crosshair in xz image:
        self.hline_xz = CrossLine(pos=self.roi_xz.pos()+self.roi_xz.size()*0.5, 
                                  angle=0, pen={'color': "F0F", 'width': 1} )
        self.vline_xz = CrossLine(pos=self.roi_xz.pos()+self.roi_xz.size()*0.5, 
                                  angle=90, pen={'color': "F0F", 'width': 1} )

        # connect the change of a region with the adjustment of the crosshair:
        self.roi_xz.sigRegionChanged.connect(self.hline_xz.adjust)
        self.roi_xz.sigRegionChanged.connect(self.vline_xz.adjust)
        
        # connect the change of a region with the adjustment of the sliders:
        # the proxy signals for that:
#        self.proxy_roi_xz_to_slider_x = pg.SignalProxy(self.roi_xz.sigRegionChanged, 
#                                                       delay=delay_sig, 
#                                                       rateLimit=eventlimit,
#                                                       slot=self.slider_x_adjust)
#        self.proxy_roi_xz_to_slider_z = pg.SignalProxy(self.roi_xz.sigRegionChanged, 
#                                                       delay=delay_sig, 
#                                                       rateLimit=eventlimit, 
#                                                       slot=self.slider_z_adjust)  
        
        # the normal signal connection for that:
        self.roi_xz.sigRegionChanged.connect(self.slider_x_adjust)
        self.roi_xz.sigRegionChanged.connect(self.slider_z_adjust)        
        
        # add the configured crosshair to the xz Widget:
        self._mw.xz_ViewWidget.addItem(self.hline_xz)
        self._mw.xz_ViewWidget.addItem(self.vline_xz)

        # Some additional settings for the xz ViewWidget
        self._mw.xz_ViewWidget.setMouseEnabled(x=False,y=False)
        self._mw.xz_ViewWidget.disableAutoRange()
        #self._mw.xz_ViewWidget.setAspectLocked(lock=True, ratio=1)               
        
        # Setup the Sliders:
        # Calculate the needed Range for the sliders. The image ranges comming 
        # from the Logic module must be in micrometer.

        self.slider_res = 0.001 # 1 nanometer resolution per one change, units 
                                # are micrometer
        
        # How many points are needed for that kind of resolution:
        num_of_points_x = (self._scanning_logic.x_range[1] - self._scanning_logic.x_range[0])/self.slider_res
        num_of_points_y = (self._scanning_logic.y_range[1] - self._scanning_logic.y_range[0])/self.slider_res
        num_of_points_z = (self._scanning_logic.z_range[1] - self._scanning_logic.z_range[0])/self.slider_res        
        
        # Set a Range for the sliders:
        self._mw.x_SliderWidget.setRange(0,num_of_points_x)
        self._mw.y_SliderWidget.setRange(0,num_of_points_y)
        self._mw.z_SliderWidget.setRange(0,num_of_points_z)

        # Predefine the maximal and minimal image range as the default values
        # for the display of the range:
        self._mw.x_min_InputWidget.setText(str(self._scanning_logic.image_x_range[0]))
        self._mw.x_max_InputWidget.setText(str(self._scanning_logic.image_x_range[1]))
        self._mw.y_min_InputWidget.setText(str(self._scanning_logic.image_y_range[0]))
        self._mw.y_max_InputWidget.setText(str(self._scanning_logic.image_y_range[1]))
        self._mw.z_min_InputWidget.setText(str(self._scanning_logic.image_z_range[0]))
        self._mw.z_max_InputWidget.setText(str(self._scanning_logic.image_z_range[1])) 

        # Connect the change of the slider with the adjustment of the ROI: 

        # the proxy signals for that:
#        self.proxy_slider_x_to_roi_xy = pg.SignalProxy(self._mw.x_SliderWidget.valueChanged, 
#                                                       delay=delay_sig, 
#                                                       rateLimit=eventlimit, 
#                                                       slot=self.roi_xy_change_x)
#        self.proxy_slider_y_to_roi_xy = pg.SignalProxy(self._mw.y_SliderWidget.valueChanged,
#                                                       delay=delay_sig, 
#                                                       rateLimit=eventlimit, 
#                                                       slot=self.roi_xy_change_y)
#        self.proxy_slider_x_to_roi_xz = pg.SignalProxy(self._mw.x_SliderWidget.valueChanged, 
#                                                       delay=delay_sig, 
#                                                       rateLimit=eventlimit, 
#                                                       slot=self.roi_xz_change_x)
#        self.proxy_slider_z_to_roi_xz = pg.SignalProxy(self._mw.z_SliderWidget.valueChanged, 
#                                                       delay=delay_sig, 
#                                                       rateLimit=eventlimit, 
#                                                       slot=self.roi_xz_change_z)

        # the normal signal connection for that:
        self._mw.x_SliderWidget.valueChanged.connect(self.roi_xy_change_x)
        self._mw.y_SliderWidget.valueChanged.connect(self.roi_xy_change_y)

        self._mw.x_SliderWidget.valueChanged.connect(self.roi_xz_change_x)
        self._mw.z_SliderWidget.valueChanged.connect(self.roi_xz_change_z)

             
        # Add to all QLineEdit Widget a Double Validator to ensure only a 
        # float input: 
        validator = QtGui.QDoubleValidator()
        validator2 = QtGui.QIntValidator()
        
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
        
        self._sd.clock_frequency_InputWidget.setValidator(validator2)
        self._sd.return_slowness_InputWidget.setValidator(validator2)
        

        # Take the default values from logic:
        self._mw.xy_res_InputWidget.setText(str(self._scanning_logic.xy_resolution))     
        self._mw.z_res_InputWidget.setText(str(self._scanning_logic.z_resolution))
        self._sd.clock_frequency_InputWidget.setText(str(int(self._scanning_logic._clock_frequency)))
        self._sd.return_slowness_InputWidget.setText(str(self._scanning_logic.return_slowness))
        
        # Connect the Slider with an update in the current values of x,y and z.
        # The proxy signal slot:
#        self.proxy_slider_x_to_curr_x = pg.SignalProxy(self._mw.x_SliderWidget.valueChanged, 
#                                                       delay=delay_sig, 
#                                                       rateLimit=eventlimit, 
#                                                       slot=self.update_current_x)
#        self.proxy_slider_y_to_curr_y = pg.SignalProxy(self._mw.y_SliderWidget.valueChanged, 
#                                                       delay=delay_sig, 
#                                                       rateLimit=eventlimit, 
#                                                       slot=self.update_current_y)
#        self.proxy_slider_z_to_curr_z = pg.SignalProxy(self._mw.z_SliderWidget.valueChanged, 
#                                                       delay=delay_sig, 
#                                                       rateLimit=eventlimit, 
#                                                       slot=self.update_current_z)
        # without the proxy:
        self._mw.x_SliderWidget.valueChanged.connect(self.update_current_x)
        self._mw.y_SliderWidget.valueChanged.connect(self.update_current_y)
        self._mw.z_SliderWidget.valueChanged.connect(self.update_current_z)

        # Update the inputed/displayed numbers if return key is hit:

        self._mw.x_current_InputWidget.returnPressed.connect(self.update_x_slider)
        self._mw.x_current_InputWidget.returnPressed.connect(self.update_y_slider)
        self._mw.z_current_InputWidget.returnPressed.connect(self.update_z_slider)
        
        self._mw.xy_res_InputWidget.returnPressed.connect(self.change_xy_resolution)
        self._mw.z_res_InputWidget.returnPressed.connect(self.change_z_resolution)
        
        self._mw.x_min_InputWidget.returnPressed.connect(self.change_x_image_range)
        self._mw.x_max_InputWidget.returnPressed.connect(self.change_x_image_range)
        self._mw.y_min_InputWidget.returnPressed.connect(self.change_y_image_range)
        self._mw.y_max_InputWidget.returnPressed.connect(self.change_y_image_range)
        self._mw.z_min_InputWidget.returnPressed.connect(self.change_z_image_range)
        self._mw.z_max_InputWidget.returnPressed.connect(self.change_z_image_range)

#        self._mw.xy_cb_min_InputWidget.returnPressed.connect(self.refresh_xy_image)
#        self._mw.xy_cb_max_InputWidget.returnPressed.connect(self.refresh_xy_image)
#
#        self._mw.xz_cb_min_InputWidget.returnPressed.connect(self.refresh_xz_image)
#        self._mw.xz_cb_max_InputWidget.returnPressed.connect(self.refresh_xz_image)
        
        # Update the inputed/displayed numbers if the cursor has left the field:

        self._mw.x_current_InputWidget.editingFinished.connect(self.update_x_slider)
        self._mw.y_current_InputWidget.editingFinished.connect(self.update_y_slider)
        self._mw.z_current_InputWidget.editingFinished.connect(self.update_z_slider)

        self._mw.xy_res_InputWidget.editingFinished.connect(self.change_xy_resolution)
        self._mw.z_res_InputWidget.editingFinished.connect(self.change_z_resolution)
        
        self._mw.x_min_InputWidget.editingFinished.connect(self.change_x_image_range)
        self._mw.x_max_InputWidget.editingFinished.connect(self.change_x_image_range)
        self._mw.y_min_InputWidget.editingFinished.connect(self.change_y_image_range)
        self._mw.y_max_InputWidget.editingFinished.connect(self.change_y_image_range)
        self._mw.z_min_InputWidget.editingFinished.connect(self.change_z_image_range)
        self._mw.z_max_InputWidget.editingFinished.connect(self.change_z_image_range) 

        self._mw.xy_cb_min_InputWidget.editingFinished.connect(self.update_xy_cb_range)
        self._mw.xy_cb_max_InputWidget.editingFinished.connect(self.update_xy_cb_range)

        self._mw.xz_cb_min_InputWidget.editingFinished.connect(self.update_xz_cb_range)
        self._mw.xz_cb_max_InputWidget.editingFinished.connect(self.update_xz_cb_range)
        
        
        # Connect the RadioButtons and connect to the events if they are 
        # clicked. Connect also the adjustment of the displayed windows.
        self._mw.ready_StateWidget.toggled.connect(self.ready_clicked)
        
        self._mw.xy_scan_StateWidget.toggled.connect(self.xy_scan_clicked)
        self._mw.xy_scan_StateWidget.toggled.connect(self.adjust_xy_window)
        
        self._mw.xz_scan_StateWidget.toggled.connect(self.xz_scan_clicked)
        self._mw.xz_scan_StateWidget.toggled.connect(self.adjust_xz_window)
        
        self._mw.refocus_StateWidget.toggled.connect(self.refocus_clicked)

        
        self._mw.xy_cb_auto_CheckBox.toggled.connect(self.update_xy_cb_range)
        self._mw.xz_cb_auto_CheckBox.toggled.connect(self.update_xz_cb_range)

        # Connect the emitted signal of an image change from the logic with
        # a refresh of the GUI picture: 
        self._scanning_logic.signal_xy_image_updated.connect(self.refresh_xy_image)
        self._scanning_logic.signal_xz_image_updated.connect(self.refresh_xz_image)
        
        # Connect the signal from the logic with an update of the cursor position
        self._scanning_logic.signal_change_position.connect(self.update_crosshair_position)
        
        # Connect the tracker
        self._optimiser_logic.signal_refocus_finished.connect(self._refocus_finished_wrapper)
        self._optimiser_logic.signal_refocus_started.connect(self.disable_scan_buttons)
        
        # connect settings signals
        self._mw.action_Settings.triggered.connect(self.menue_settings)
        self._sd.accepted.connect(self.update_settings)
        self._sd.rejected.connect(self.reject_settings)
        self._sd.buttonBox.button(QtGui.QDialogButtonBox.Apply).clicked.connect(self.update_settings) 
  
        
        # get the viewbox object to alter the display:
        xy_viewbox = self.xy_image.getViewBox()
        #xy_viewbox.setRange(xRange=[0,100],yRange=[0,100],padding=20)
        #keywords = {'xMin':0.0,'xMax': 100.0,'yMin':0.0,'yMax': 100.0}
        

#        xy_viewbox.setLimits(keyword['limits'][lname][mnmx]s)
        # That is really an ugly solution, but the command above, which is 
        # intended to fix the limits is not working. Therefore I try it like 
        # that.
        xy_viewbox.state['limits']['xLimits'][0] = self._scanning_logic.x_range[0]
        xy_viewbox.state['limits']['xLimits'][1] = self._scanning_logic.x_range[1]
        xy_viewbox.state['limits']['yLimits'][0] = self._scanning_logic.y_range[0]
        xy_viewbox.state['limits']['yLimits'][1] = self._scanning_logic.y_range[1]
  
        # the same for xz viewbox:
  
        xz_viewbox = self.xz_image.getViewBox()
        xz_viewbox.state['limits']['xLimits'][0] = self._scanning_logic.x_range[0]
        xz_viewbox.state['limits']['xLimits'][1] = self._scanning_logic.x_range[1]
        xz_viewbox.state['limits']['yLimits'][0] = self._scanning_logic.z_range[0]
        xz_viewbox.state['limits']['yLimits'][1] = self._scanning_logic.z_range[1]
  
  
        # Show the Main Confocal GUI:
        self._mw.show()
        
        # Now that the ROI is connected to events, set again to initial pos:        
        self.roi_xy.setPos([ini_pos_x_crosshair+0.001, ini_pos_y_crosshair+0.001]) 
        # Now that the ROI is connected to events, set again to initial pos:        
        self.roi_xz.setPos([ini_pos_x_crosshair+0.001, ini_pos_y_crosshair+0.001])          

        # create a color map that goes from dark red to dark blue:

        # Absolute scale relative to the expected data not important. This 
        # should have the same amount of entries (num parameter) as the number
        # of values given in color. 
        pos = np.linspace(0.0, 1.0, num=10)
        
        #colormap1:
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

            
        self.xy_image.setLookupTable(lut)
        self.xz_image.setLookupTable(lut)        
        
        # Play around with a color bar:
        
        self.xy_cb = ColorBar(self.colmap_norm, 100, 100000, label='Counts')#Foo (Hz)')#, [0., 0.5, 1.0])      
        self.xz_cb = ColorBar(self.colmap_norm, 100, 100000, label='Counts')#Foo (Hz)')#, [0., 0.5, 1.0])              
        
        self._mw.xy_cb_ViewWidget.addItem(self.xy_cb)
        self._mw.xz_cb_ViewWidget.addItem(self.xz_cb)
        self._mw.xy_cb_ViewWidget.hideAxis('bottom')
        self._mw.xz_cb_ViewWidget.hideAxis('bottom')
        
        
        self.adjust_aspect_roi_xy()
        self.adjust_aspect_roi_xz()
      
#        print(dir(self.xy_image.getViewBox()))
        self.xy_image.getViewBox().sigRangeChangedManually.connect(self.adjust_aspect_roi_xy)
        self.xz_image.getViewBox().sigRangeChangedManually.connect(self.adjust_aspect_roi_xz)
        #self.xy_image.getViewBox().sigResized.connect(self.adjust_aspect_roi_xy)
        
        #self.xy_image.getViewBox().setXRange(min, max, padding=None, update=True)
        self._mw.ready_StateWidget.click()
        
        
        # Connect the 'File' Menu dialog in confocal with the methods:
        self._mw.actionSave_XY_Scan.triggered.connect(self.save_xy_scan)
        self._mw.actionSave_XZ_Scan.triggered.connect(self.save_xz_scan) 
        
        
        
        
    def update_crosshair_position(self):
        """ Update the GUI position of the crosshair from the logic.
        """
#        print('Update roi from scanner logic.')        
        
        x_pos, y_pos, z_pos = self._scanning_logic.get_position()
        
        roi_x_view = x_pos - self.roi_xy.size()[0]*0.5
        roi_y_view = y_pos - self.roi_xy.size()[1]*0.5
        self.roi_xy.setPos([roi_x_view , roi_y_view])
        
        roi_x_view = x_pos - self.roi_xz.size()[0]*0.5
        roi_y_view = z_pos - self.roi_xz.size()[1]*0.5
        self.roi_xz.setPos([roi_x_view , roi_y_view])
        
        
    def refresh_xy_colorbar(self):
        """ Adjust the xy colorbar.
        
        Currently everytime the update is performed, a new ColorBar object is 
        created and add to the display while the old one is deleted. This must
        be fixed in the class.
        """
        self._mw.xy_cb_ViewWidget.clear()

        # If "Auto" is checked, adjust colour scaling to fit all data.
        # Otherwise, take user-defined values.
        if self._mw.xy_cb_auto_CheckBox.isChecked():
            self.xy_cb = ColorBar(self.colmap_norm, 100, self.xy_image.image.max(), label='Counts')#, [0., 0.5, 1.0])
        else:
            cb_min = float(self._mw.xy_cb_min_InputWidget.text())
            cb_max = float(self._mw.xy_cb_max_InputWidget.text())
            self.xy_cb = ColorBar(self.colmap_norm, 100, cb_max, label='Counts')#, [0., 0.5, 1.0])

        self._mw.xy_cb_ViewWidget.addItem(self.xy_cb)        


    def refresh_xz_colorbar(self):
        """ Adjust the xz colorbar.
        
        Currently everytime the update is performed, a new ColorBar object is 
        created and add to the display while the old one is deleted. This must
        be fixed in the class.
        """
        self._mw.xz_cb_ViewWidget.clear()
        # If "Auto" is checked, adjust colour scaling to fit all data.
        # Otherwise, take user-defined values.
        if self._mw.xz_cb_auto_CheckBox.isChecked():
            self.xz_cb = ColorBar(self.colmap_norm, 100, self.xz_image.image.max(), label='Counts')#, [0., 0.5, 1.0])
        else:
            cb_min = float(self._mw.xz_cb_min_InputWidget.text())
            cb_max = float(self._mw.xz_cb_max_InputWidget.text())
            self.xz_cb = ColorBar(self.colmap_norm, 100, cb_max, label='Counts')#, [0., 0.5, 1.0])

        self._mw.xz_cb_ViewWidget.addItem(self.xz_cb)


    def disable_scan_buttons(self, newstate=False):
        """ Disables the radio buttons for scanning.
        
        @param bool newstate: disabled (False), enabled (True)
        """        
        self._mw.xy_scan_StateWidget.setEnabled(newstate)
        self._mw.xz_scan_StateWidget.setEnabled(newstate)
        self._mw.refocus_StateWidget.setEnabled(newstate)


    def _refocus_finished_wrapper(self):
        if not self._mw.ready_StateWidget.isChecked():
            self._mw.ready_StateWidget.click()
            return
        else:
            self.disable_scan_buttons(newstate=True)
            
    def menue_settings(self):
        ''' This method opens the settings menue
        '''
        self._sd.exec_()
        
    def update_settings(self):
        ''' This method writes the new settings from the gui to the file
        '''        
        self._scanning_logic.set_clock_frequency(int(self._sd.clock_frequency_InputWidget.text()))
        self._scanning_logic.return_slowness = int(self._sd.return_slowness_InputWidget.text())

                
    def reject_settings(self):
        ''' This method keeps the old settings and restores the old settings in the gui
        '''
        self._sd.clock_frequency_InputWidget.setText(str(int(self._scanning_logic._clock_frequency)))
        self._sd.return_slowness_InputWidget.setText(str(self._scanning_logic.return_slowness))


    def ready_clicked(self):
        """ Stopp the scan if the state has switched to ready.
        """            
        if self._scanning_logic.getState() == 'locked':
            self._scanning_logic.stop_scanning()
        if self._optimiser_logic.getState() == 'locked':
            self._optimiser_logic.stop_refocus()
            
        self.disable_scan_buttons(newstate=True)

            
    def xy_scan_clicked(self, enabled):
        """ Manages what happens if the xy scan is started.
        
        @param bool enabled: start scan if that is possible
        """        
        #Firstly stop any scan that might be in progress
        self._scanning_logic.stop_scanning() 
             
        
        #Then if enabled. start a new scan.
        if enabled:
            self._scanning_logic.start_scanning()
            self.disable_scan_buttons()

      
    def xz_scan_clicked(self, enabled):
        """ Manages what happens if the xz scan is started.
        
        @param bool enabled: start scan if that is possible
        """
        self._scanning_logic.stop_scanning()

        if enabled:
            self._scanning_logic.start_scanning(zscan = True)
            self.disable_scan_buttons()
            

    def refocus_clicked(self, enabled):
        """ Manages what happens if the optimizer is started.
        
        @param bool enabled: start optimizer if that is possible
        """        
        self._scanning_logic.stop_scanning()
        if enabled:
            self._optimiser_logic.start_refocus()
            self.disable_scan_buttons()


    def roi_xy_change_x(self,x_pos=None):
        """ Adjust the xy ROI position if the x value has changed.
        
        @param tuple or float x_pos: real value of the current x position 
        
        Since the origin of the region of interest (ROI) is not the crosshair
        point but the lowest left point of the square, you have to shift the
        origin according to that. Therefore the position of the ROI is not 
        the actual position!
        """
#        print('Update roi xy for change in slider x.')
#        if type(x_pos) is tuple:
#            x_pos = x_pos[0]
#        
#        # the slider has always an integer as output, this can be used to 
#        # distinguish a signal comming from the 
#        if x_pos != None and type(x_pos) is int:
#        print('x_pos 1',type(x_pos),x_pos)
        x_pos=x_pos*self.slider_res        
        
        roi_x_view = x_pos - self.roi_xy.size()[0]*0.5
        roi_y_view = self.roi_xy.pos()[1]
        self.roi_xy.setPos([roi_x_view , roi_y_view])
        self._scanning_logic.set_position(x=x_pos)
#        print('x_pos 2',type(x_pos),x_pos)
        
        
    def roi_xy_change_y(self,y_pos=None):
        """ Adjust the xy ROI position if the y value has changed.
        
        @param tuple or float y_pos: real value of the current y value
        
        Since the origin of the region of interest (ROI) is not the crosshair
        point but the lowest left point of the square, you have to shift the
        origin according to that. Therefore the position of the ROI is not 
        the actual position!
        """
#        print('Update roi xy for change in slider y.')
#        if type(y_pos) is tuple:
#            y_pos = y_pos[0]
#        if y_pos != None and type(y_pos) is float:
        y_pos=y_pos*self.slider_res
        
        roi_x_view = self.roi_xy.pos()[0]
        roi_y_view = y_pos - self.roi_xy.size()[1]*0.5
        self.roi_xy.setPos([roi_x_view , roi_y_view])
        self._scanning_logic.set_position(y=y_pos)    

        
    def roi_xz_change_x(self,x_pos=None):
        """ Adjust the xz ROI position if the x value has changed.
        
        @param tuple or float x_pos: real value of the current x value
        
        Since the origin of the region of interest (ROI) is not the crosshair
        point but the lowest left point of the square, you have to shift the
        origin according to that. Therefore the position of the ROI is not 
        the actual position!
        """        
#        if type(x_pos) is tuple:
#            x_pos = x_pos[0]
#        if x_pos != None and type(x_pos) is float:
        x_pos=x_pos*self.slider_res        
        
        roi_x_view = x_pos - self.roi_xz.size()[0]*0.5
        roi_y_view = self.roi_xz.pos()[1]
        self.roi_xz.setPos([roi_x_view , roi_y_view])
        self._scanning_logic.set_position(x=x_pos)        


    def roi_xz_change_z(self,z_pos=None):
        """ Adjust the xz ROI position if the z value has changed.
        
        @param tuple or float z_pos: real value of the current z value
        
        Since the origin of the region of interest (ROI) is not the crosshair
        point but the lowest left point of the square, you have to shift the
        origin according to that. Therefore the position of the ROI is not 
        the actual position!
        """        
#        if type(z_pos) is tuple:
#            z_pos = z_pos[0]
#        if z_pos != None and type(z_pos) is float:
        z_pos = self._scanning_logic.z_range[0] + z_pos*self.slider_res         
        
        roi_x_view = self.roi_xz.pos()[0]
        roi_y_view = z_pos - self.roi_xz.size()[1]*0.5
        self.roi_xz.setPos([roi_x_view , roi_y_view])
        self._scanning_logic.set_position(z=z_pos)         
        
        
    def slider_x_adjust(self,roi):
        """ Adjust the x slider if a change happens.
        
        @param object roi: a pyqtgraph.ROI object of the scan.
        """
#        print('Update slider x.')
        self._mw.x_SliderWidget.setValue( int( (roi.pos()[0]+ 0.5*roi.size()[0])/self.slider_res) )


    def slider_y_adjust(self,roi):
        """ Adjust the y slider if a change happens.
        
        @param object roi: a pyqtgraph.ROI object of the scan.
        """
#        print('Update slider y.')
        self._mw.y_SliderWidget.setValue( int( (roi.pos()[1]+ 0.5*roi.size()[1])/self.slider_res) ) 


    def slider_z_adjust(self,roi):
        """ Adjust the z slider if a change happens.
        
        @param object roi: a pyqtgraph.ROI object of the scan.
        """
        self._mw.z_SliderWidget.setValue(int( ( roi.pos()[1] + 0.5*roi.size()[1]  - self._scanning_logic.z_range[0] )/self.slider_res) ) 
        
        
    def update_current_x(self,x_pos):
        """ Update the displayed x-value.
        
        @param float x_pos: the current value of the x position        
        """
#        print('Update current x.')
        # Convert x_pos to number of points for the slider:
        self._mw.x_current_InputWidget.setText('{0:.5}'.format(x_pos*self.slider_res))

        
    def update_current_y(self,y_pos):
        """ Update the displayed y-value.
        
        @param float y_pos: the current value of the y position        
        """
#        print('Update current y.')
        # Convert x_pos to number of points for the slider:
        self._mw.y_current_InputWidget.setText('{0:.5}'.format(y_pos*self.slider_res))        


    def update_current_z(self,z_pos):
        """ Update the displayed z-value.
        
        @param float z_pos: the current value of the z position        
        """
        # Convert x_pos to number of points for the slider:
        self._mw.z_current_InputWidget.setText('{0:.5}'.format(self._scanning_logic.z_range[0] + z_pos*self.slider_res))


    def update_x_slider(self):
        """ Update the x slider with the new entered value of x.
        """
#        print('Update x slider for change in current x.')
        self._mw.x_SliderWidget.setValue( int(float(self._mw.x_current_InputWidget.text())/self.slider_res)   )


    def update_y_slider(self):
        """ Update the y slider with the new entered value of y.
        """
#        print('Update y slider for change in current y.')
        self._mw.y_SliderWidget.setValue(  int(float(self._mw.y_current_InputWidget.text())/self.slider_res)    )


    def update_z_slider(self):
        """ Update the z slider with the new entered value of z.
        """        
        self._mw.z_SliderWidget.setValue( int((float(self._mw.z_current_InputWidget.text()) - self._scanning_logic.z_range[0])/self.slider_res ))


    def change_xy_resolution(self):
        """ Update the xy resolution in the logic according to the GUI.
        """
        self._scanning_logic.xy_resolution = float(self._mw.xy_res_InputWidget.text())


    def change_z_resolution(self):
        """ Update the z resolution in the logic according to the GUI.
        """        
        self._scanning_logic.z_resolution = float(self._mw.z_res_InputWidget.text())


    def change_x_image_range(self):
        """ Adjust the image range for x in the logic.
        """
        self._scanning_logic.image_x_range = [float(self._mw.x_min_InputWidget.text()), 
                                              float(self._mw.x_max_InputWidget.text())]


    def change_y_image_range(self):
        """ Adjust the image range for y in the logic.
        """
        self._scanning_logic.image_y_range = [float(self._mw.y_min_InputWidget.text()), 
                                              float(self._mw.y_max_InputWidget.text())]


    def change_z_image_range(self):
        """ Adjust the image range for z in the logic. """
        self._scanning_logic.image_z_range = [float(self._mw.z_min_InputWidget.text()), 
                                              float(self._mw.z_max_InputWidget.text())]

    def update_xy_cb_range(self):
        self.refresh_xy_colorbar()
        self.refresh_xy_image()

    def update_xz_cb_range(self):
        self.refresh_xz_colorbar()
        self.refresh_xz_image()
        
        
    def refresh_xy_image(self):
        """ Update the current XY image from the logic. 

        Everytime the scanner is scanning a line in xy the 
        image is rebuild and updated in the GUI.        
        """
        self.adjust_xy_window()
            
        self.xy_image.getViewBox().enableAutoRange()
        self.put_cursor_in_xy_scan()
        self.adjust_aspect_roi_xy()
        
#        self.xy_image.getViewBox().setXRange(view_x_min, view_x_max, padding=None, update=True)            
#        self.xy_image.getViewBox().setYRange(view_y_min, view_y_max, padding=None, update=True) 
        
        # If "Auto" is checked, adjust colour scaling to fit all data.
        # Otherwise, take user-defined values.
        if self._mw.xy_cb_auto_CheckBox.isChecked():
            self.xy_image.setImage(image=self._scanning_logic.xy_image[:,:,3].transpose(),autoLevels=True)
            self.refresh_xy_colorbar()
        else:
            cb_min = float(self._mw.xy_cb_min_InputWidget.text())
            cb_max = float(self._mw.xy_cb_max_InputWidget.text())
            self.xy_image.setImage(image=self._scanning_logic.xy_image[:,:,3].transpose(),levels=(cb_min,cb_max) )

            
        if self._scanning_logic.getState() != 'locked':
            self._mw.ready_StateWidget.click()

    def refresh_xz_image(self):
        """ Update the current XZ image from the logic. 

        Everytime the scanner is scanning a line in xz the 
        image is rebuild and updated in the GUI.        
        """
        self.adjust_xz_window()
            
            
        self.xz_image.getViewBox().enableAutoRange()
        self.put_cursor_in_xz_scan()
        self.adjust_aspect_roi_xy()              

        # If "Auto" is checked, adjust colour scaling to fit all data.
        # Otherwise, take user-defined values.
        if self._mw.xz_cb_auto_CheckBox.isChecked():
            self.xz_image.setImage(image=self._scanning_logic.xz_image[:,:,3].transpose(),autoLevels=True)
            self.refresh_xz_colorbar()
        else:
            cb_min = float(self._mw.xz_cb_min_InputWidget.text())
            cb_max = float(self._mw.xz_cb_max_InputWidget.text())
            self.xz_image.setImage(image=self._scanning_logic.xz_image[:,:,3].transpose(),levels=(cb_min,cb_max) )


        if self._scanning_logic.getState() != 'locked':
            self._mw.ready_StateWidget.click()
        
    def adjust_xy_window(self):
        
        view_x_min = float(self._mw.x_min_InputWidget.text())
        view_x_max = float(self._mw.x_max_InputWidget.text())-view_x_min
        view_y_min = float(self._mw.y_min_InputWidget.text())
        view_y_max = float(self._mw.y_max_InputWidget.text())-view_y_min  
        self.xy_image.setRect(QtCore.QRectF(view_x_min, view_y_min, view_x_max, view_y_max))                
        self.xy_image.getViewBox().enableAutoRange()
        xy_viewbox = self.xy_image.getViewBox()
        xy_viewbox.state['limits']['xLimits'][0] = float(self._mw.x_min_InputWidget.text())
        xy_viewbox.state['limits']['xLimits'][1] = float(self._mw.x_max_InputWidget.text())
        xy_viewbox.state['limits']['yLimits'][0] = float(self._mw.y_min_InputWidget.text())
        xy_viewbox.state['limits']['yLimits'][1] = float(self._mw.y_max_InputWidget.text())
        xy_viewbox.updateViewRange()


    def adjust_xz_window(self):
        
        view_x_min = float(self._mw.x_min_InputWidget.text())
        view_x_max = float(self._mw.x_max_InputWidget.text())-view_x_min
        view_z_min = float(self._mw.z_min_InputWidget.text())
        view_z_max = float(self._mw.z_max_InputWidget.text())-view_z_min  
        self.xz_image.setRect(QtCore.QRectF(view_x_min, view_z_min, view_x_max, view_z_max))           
        self.xz_image.getViewBox().enableAutoRange()
        xz_viewbox = self.xz_image.getViewBox()
        xz_viewbox.state['limits']['xLimits'][0] = float(self._mw.x_min_InputWidget.text())
        xz_viewbox.state['limits']['xLimits'][1] = float(self._mw.x_max_InputWidget.text())
        xz_viewbox.state['limits']['yLimits'][0] = float(self._mw.z_min_InputWidget.text())
        xz_viewbox.state['limits']['yLimits'][1] = float(self._mw.z_max_InputWidget.text())
        xz_viewbox.updateViewRange()


    def put_cursor_in_xy_scan(self):
        view_x_min = float(self._mw.x_min_InputWidget.text())
        view_x_max = float(self._mw.x_max_InputWidget.text())
        view_y_min = float(self._mw.y_min_InputWidget.text())
        view_y_max = float(self._mw.y_max_InputWidget.text())
        
        x_value = self.roi_xy.pos()[0]
        y_value = self.roi_xy.pos()[1]
        cross_pos = self.roi_xy.pos()+ self.roi_xy.size()*0.5



        if (view_x_min > cross_pos[0]):
            x_value = view_x_min+self.roi_xy.size()[0]*0.5
            
        if (view_x_max < cross_pos[0]):
            x_value = view_x_max-self.roi_xy.size()[0]*0.5
            
        if (view_y_min > cross_pos[1]):
            y_value = view_y_min+self.roi_xy.size()[1]*0.5
            
        if (view_y_max < cross_pos[1]):
            y_value = view_y_max-self.roi_xy.size()[1]*0.5
         
        self.roi_xy.setPos([x_value,y_value], update=True)
            
    def put_cursor_in_xz_scan(self):
        view_x_min = float(self._mw.x_min_InputWidget.text())
        view_x_max = float(self._mw.x_max_InputWidget.text())#-view_x_min
        view_z_min = float(self._mw.z_min_InputWidget.text())
        view_z_max = float(self._mw.z_max_InputWidget.text())#-view_z_min  
        
        x_value = self.roi_xz.pos()[0]
        z_value = self.roi_xz.pos()[1]
        cross_pos = self.roi_xz.pos()+ self.roi_xz.size()*0.5
        
        if (view_x_min > cross_pos[0]):
            x_value = view_x_min+self.roi_xz.size()[0]*0.5
            
        if (view_x_max < cross_pos[0]):
            x_value = view_x_max-self.roi_xz.size()[0]*0.5
            
        if (view_z_min > cross_pos[1]):
            z_value = view_z_min+self.roi_xz.size()[1]*0.5
            
        if (view_z_max < cross_pos[1]):
            z_value = view_z_max-self.roi_xz.size()[1]*0.5
            
        self.roi_xz.setPos([x_value,z_value], update=True)

      
    def adjust_aspect_roi_xy(self,viewbox=None):
        """ Keep the aspect ratio of the ROI also during the zoom the same. 
        
        @param object viewbox: pyqtgraph.ViewBox object, which contains the 
                               view information about the display.
        """
        viewbox = self.xy_image.getViewBox()
        current_x_view_range = viewbox.viewRange()[0][1] - viewbox.viewRange()[0][0]
        current_y_view_range = viewbox.viewRange()[1][1] - viewbox.viewRange()[1][0]

        size_x_roi = current_x_view_range/20
        size_y_roi = current_y_view_range/20
        pos = self.roi_xy.pos()
        self.roi_xy.setSize([size_x_roi,size_y_roi],update=False)
        self.roi_xy.setPos(pos,update=True)

    
    def adjust_aspect_roi_xz(self,viewbox=None):
        """ Keep the aspect ratio of the ROI also during the zoom the same. 
        
        @param object viewbox: pyqtgraph.ViewBox object, which contains the 
                               view information about the display.
        
        """
        viewbox = self.xz_image.getViewBox()
        current_x_view_range = viewbox.viewRange()[0][1] - viewbox.viewRange()[0][0]
        current_z_view_range = viewbox.viewRange()[1][1] - viewbox.viewRange()[1][0]

        size_x_roi = current_x_view_range/20
        size_z_roi = current_z_view_range/20
        self.roi_xz.setSize([size_x_roi,size_z_roi])

    def save_xy_scan(self):
        """ Run the save routine from the logic to save the xy confocal pic."""
        self._scanning_logic.save_xy_data()
        
    def save_xz_scan(self):
        """ Run the save routine from the logic to save the xy confocal pic."""      
        self._scanning_logic.save_xz_data()
        
        
