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
        
    @param object pyqtgraph.ColorMap cmap: a defined colormap
    @param float width: width of the colorbar in x direction, starting from
                        the origin.
    @param numpy.array ticks: optional, definition of the relative ticks marks
    """    
    def __init__(self, cmap, width, cb_min, cb_max):

        pg.GraphicsObject.__init__(self)
         
        # handle the passed arguments:
        self.stops, self.colors = cmap.getStops('float')
        self.stops = (self.stops - self.stops.min())/self.stops.ptp()
        self.width = width
 
        # Constructs an empty picture which can be altered by QPainter 
        # commands. The picture is a serialization of painter commands to an IO
        # device in a platform-independent format.
        self.pic = pg.QtGui.QPicture()
        
        self.refresh_colorbar(cb_min, cb_max) 

    def refresh_colorbar(self, cb_min, cb_max, width = None):
        """ Refresh the appearance of the colorbar for a changed count range.
        
        @param float cb_min: The minimal count value should be passed here.
        @param float cb_max: The maximal count value should be passed here.
        @param float width: optional, with that you can change the width of the
                            colorbar in the display.
        """
        
        if width is None:
            width = self.width
        else:
            self.width = width
                
#       FIXME: Until now, if you want to refresh the colorbar, a new QPainter
#              object has been created, but I think that it is not necassary.
#              I have to figure out how to use the created object properly. 
        p = pg.QtGui.QPainter(self.pic)
        p.drawRect(self.boundingRect())
        p.setPen(pg.mkPen('k'))
        grad = pg.QtGui.QLinearGradient(width/2.0, cb_min*1.0, width/2.0, cb_max*1.0)
        for stop, color in zip(self.stops, self.colors):
            grad.setColorAt(1.0 - stop, pg.QtGui.QColor(*[255*c for c in color]))
        p.setBrush(pg.QtGui.QBrush(grad))
        p.drawRect(pg.QtCore.QRectF(0, cb_min, width, cb_max-cb_min))        
        p.end()

        vb = self.getViewBox()
        # check whether a viewbox is already created for this object. If yes,
        # then it should be adjusted according to the full screen.        
        if vb is not None:
            vb.updateAutoRange()        
        
    def paint(self, p, *args):
        """ Overwrite the paint method from GraphicsObject.     

        @param object p: a pyqtgraph.QtGui.QPainter object, which is used to 
                         set the color of the pen.        
        
        Since this colorbar object is in the end a GraphicsObject, it will
        drop an implementation error, since you have to write your own paint
        function for the created GraphicsObject.
        """        
        # paint colorbar
        p.drawPicture(0, 0, self.pic)


    def boundingRect(self):
        """ Overwrite the paint method from GraphicsObject.
        
        Get the position, width and hight of the displayed object.
        """
        return pg.QtCore.QRectF(self.pic.boundingRect())



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
        Base.__init__(self, manager, name, config, c_dict)
        
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
        
        self.fixed_aspect_ratio_xy = config['fixed_aspect_ratio_xy']
        self.fixed_aspect_ratio_xz = config['fixed_aspect_ratio_xz']
        self.slider_stepsize = config['slider_stepsize']
        self.image_x_padding = config['image_x_padding']
        self.image_y_padding = config['image_y_padding']
        self.image_z_padding = config['image_z_padding']

    def initUI(self, e=None):
        """ Definition, configuration and initialisation of the confocal GUI.
          
        @param class e: event class from Fysom


        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules. 
        Moreover it sets default values.
        """
#FIXME: can we delete all the commented stuff in this method? I have deleted 
#       all commented stuff which I do not need. The rest of them I will later
#       integrate in the code. --Alex
# FIXME: Make the format display of the current values adjustable.
# FIXME: Make the xy scan and the xz scan saveable either as png or svg.

        
        
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
        
        # Load the images for xy and xz in the display:
        self.xy_image = pg.ImageItem(arr01)
        self.xz_image = pg.ImageItem(arr02)

                                            
        #######################################################################
        ###               Configuration of the optimiser tab                ###
        #######################################################################
        
        # Load the image for the optimiser tab                                    
        self.xy_refocus_image = pg.ImageItem(self._optimiser_logic.xy_refocus_image[:,:,3].transpose())
        self.xy_refocus_image.setRect(QtCore.QRectF(self._optimiser_logic._trackpoint_x - 0.5 * self._optimiser_logic.refocus_XY_size,
                                                    self._optimiser_logic._trackpoint_y - 0.5 * self._optimiser_logic.refocus_XY_size,
                                                    self._optimiser_logic.refocus_XY_size, self._optimiser_logic.refocus_XY_size))               
        self.xz_refocus_image = pg.ScatterPlotItem(self._optimiser_logic._zimage_Z_values,
                                                self._optimiser_logic.z_refocus_line, 
                                                symbol='o')
        self.xz_refocus_fit_image = pg.PlotDataItem(self._optimiser_logic._fit_zimage_Z_values,
                                                    self._optimiser_logic.z_fit_data, 
                                                    pen=QtGui.QPen(QtGui.QColor(255,0,255,255)))
                                                    
        # Add the display item to the xy and xz VieWidget, which was defined in
        # the UI file.
        self._mw.xy_refocus_ViewWidget_2.addItem(self.xy_refocus_image)
        self._mw.xz_refocus_ViewWidget_2.addItem(self.xz_refocus_image)
        self._mw.xz_refocus_ViewWidget_2.addItem(self.xz_refocus_fit_image)
        
        #Add crosshair to the xy refocus scan
        self.vLine = pg.InfiniteLine(pen=QtGui.QPen(QtGui.QColor(255,0,255,255), 0.02), pos=50, angle=90, movable=False)
        self.hLine = pg.InfiniteLine(pen=QtGui.QPen(QtGui.QColor(255,0,255,255), 0.02), pos=50, angle=0, movable=False)
        self._mw.xy_refocus_ViewWidget_2.addItem(self.vLine, ignoreBounds=True)
        self._mw.xy_refocus_ViewWidget_2.addItem(self.hLine, ignoreBounds=True)
        
        
        # Set the state button as ready button as default setting.
        self._mw.ready_StateWidget.click()

        # The main windows of the xy scan is a PlotWidget object, which itself
        # inherits all functions from PlotItem. And PlotItem provides the
        # ViewBox object, which can change the appearance of the displayed xy
        # image:
        # self._mw.xy_ViewWidget.plotItem

        # Add the display item to the xy and xz ViewWidget, which was defined 
        # in the UI file:
        self._mw.xy_ViewWidget.addItem(self.xy_image)
        self._mw.xz_ViewWidget_2.addItem(self.xz_image)
        
        # Label the axes
        
        self._mw.xy_ViewWidget.setLabel( 'bottom', 'X position', units='micron' )
        self._mw.xy_ViewWidget.setLabel( 'left', 'Y position', units='micron' )
        self._mw.xz_ViewWidget_2.setLabel( 'bottom', 'X position', units='micron' )
        self._mw.xz_ViewWidget_2.setLabel( 'left', 'Z position', units='micron' )
    
        # Create Region of Interest for xy image and add to xy Image Widget:
        self.roi_xy = CrossROI([ini_pos_x_crosshair, ini_pos_y_crosshair], 
                               [len(arr01)/20, len(arr01)/20], 
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
        self.roi_xy.sigRegionChanged.connect(self.update_x_slider)
        self.roi_xy.sigRegionChanged.connect(self.update_y_slider)

        # add the configured crosshair to the xy Widget
        self._mw.xy_ViewWidget.addItem(self.hline_xy)
        self._mw.xy_ViewWidget.addItem(self.vline_xy)
        
        # Some additional settings for the xy ViewWidget
        #self._mw.xy_ViewWidget.setMouseEnabled(x=False,y=False)
       # self._mw.xz_ViewWidget_2.disableAutoRange()
        #self._mw.xy_ViewWidget.setAspectLocked(lock=True, ratio=1)

        # Create Region of Interest for xz image and add to xy Image Widget:
        self.roi_xz = CrossROI([ini_pos_x_crosshair, ini_pos_z_crosshair], 
                               [len(arr02)/20, len(arr02)/20], 
                               pen={'color': "F0F", 'width': 1},
                               removable=True )
        self._mw.xz_ViewWidget_2.addItem(self.roi_xz)

        # create horizontal and vertical line as a crosshair in xz image:
        self.hline_xz = CrossLine(pos=self.roi_xz.pos()+self.roi_xz.size()*0.5, 
                                  angle=0, pen={'color': "F0F", 'width': 1} )
        self.vline_xz = CrossLine(pos=self.roi_xz.pos()+self.roi_xz.size()*0.5, 
                                  angle=90, pen={'color': "F0F", 'width': 1} )

        # connect the change of a region with the adjustment of the crosshair:
        self.roi_xz.sigRegionChanged.connect(self.hline_xz.adjust)
        self.roi_xz.sigRegionChanged.connect(self.vline_xz.adjust)
        
        # connect the change of a region with the adjustment of the sliders:
        self.roi_xz.sigRegionChanged.connect(self.update_x_slider)
        self.roi_xz.sigRegionChanged.connect(self.update_z_slider)        
        
        # add the configured crosshair to the xz Widget:
        self._mw.xz_ViewWidget_2.addItem(self.hline_xz)
        self._mw.xz_ViewWidget_2.addItem(self.vline_xz)

        # Some additional settings for the xz ViewWidget
        #self._mw.xz_ViewWidget_2.setMouseEnabled(x=False,y=False)
        #self._mw.xz_ViewWidget_2.disableAutoRange()
        #self._mw.xz_ViewWidget_2.setAspectLocked(lock=True, ratio=1)               
        
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
        self._mw.x_SliderWidget.valueChanged.connect(self.update_roi_xy_change_x)
        self._mw.y_SliderWidget.valueChanged.connect(self.update_roi_xy_change_y)

        self._mw.x_SliderWidget.valueChanged.connect(self.update_roi_xz_change_x)
        self._mw.z_SliderWidget.valueChanged.connect(self.update_roi_xz_change_z)

             
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
        #self._sd.slider_stepwidth_InputWidget.setValidator(validator)

        # Take the default values from logic:
        self._mw.xy_res_InputWidget.setText(str(self._scanning_logic.xy_resolution))     
        self._mw.z_res_InputWidget.setText(str(self._scanning_logic.z_resolution))
        
        # write the configuration to the settings window of the GUI. 
        self.keep_former_settings()       
        
        # Connect the Slider with an update in the current values of x,y and z.
        self._mw.x_SliderWidget.valueChanged.connect(self.update_current_x)
        self._mw.y_SliderWidget.valueChanged.connect(self.update_current_y)
        self._mw.z_SliderWidget.valueChanged.connect(self.update_current_z)

        # Update the inputed/displayed numbers if return key is hit:
        self._mw.xy_cb_min_InputWidget.returnPressed.connect(self.shortcut_to_xy_cb_manual)
        self._mw.xy_cb_max_InputWidget.returnPressed.connect(self.shortcut_to_xy_cb_manual)

        self._mw.xz_cb_min_InputWidget.returnPressed.connect(self.shortcut_to_xz_cb_manual)
        self._mw.xz_cb_max_InputWidget.returnPressed.connect(self.shortcut_to_xz_cb_manual)
        
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
        
        
#         Connect the RadioButtons and connect to the events if they are 
#         clicked. Connect also the adjustment of the displayed windows.
        self._mw.ready_StateWidget.toggled.connect(self.ready_clicked)
        
        self._mw.xy_scan_StateWidget.toggled.connect(self.xy_scan_clicked)
#        self._mw.xy_scan_StateWidget.toggled.connect(self.adjust_xy_window)
        self._mw.xz_scan_StateWidget.toggled.connect(self.xz_scan_clicked)
#        self._mw.xz_scan_StateWidget.toggled.connect(self.adjust_xz_window)
        
        self._mw.refocus_StateWidget.toggled.connect(self.refocus_clicked)

        self._mw.xy_cb_auto_CheckBox.toggled.connect(self.update_xy_cb_range)
        self._mw.xz_cb_auto_CheckBox.toggled.connect(self.update_xz_cb_range)

        # Connect the emitted signal of an image change from the logic with
        # a refresh of the GUI picture: 
        self._scanning_logic.signal_xy_image_updated.connect(self.refresh_xy_image)
        self._scanning_logic.signal_xz_image_updated.connect(self.refresh_xz_image)
        self._optimiser_logic.signal_image_updated.connect(self.refresh_refocus_image)
        self._scanning_logic.sigImageXYInitialized.connect(self.adjust_xy_window)
        self._scanning_logic.sigImageXZInitialized.connect(self.adjust_xz_window) 
        
        
        # Connect the signal from the logic with an update of the cursor position
        self._scanning_logic.signal_change_position.connect(self.update_crosshair_position)
        
        # Connect the tracker
        self._optimiser_logic.signal_refocus_finished.connect(self._refocus_finished_wrapper)
        self._optimiser_logic.signal_refocus_started.connect(self.disable_scan_buttons)
        
        # connect settings signals
        self._mw.action_Settings.triggered.connect(self.menue_settings)
        self._sd.accepted.connect(self.update_settings)
        self._sd.rejected.connect(self.keep_former_settings)
        self._sd.buttonBox.button(QtGui.QDialogButtonBox.Apply).clicked.connect(self.update_settings)

        # create a color map that goes from dark red to dark blue:
        
        #colormap1:
        color = np.array([[127,  0,  0,255], [255, 26,  0,255], [255,129,  0,255],
                          [254,237,  0,255], [160,255, 86,255], [ 66,255,149,255],
                          [  0,204,255,255], [  0, 88,255,255], [  0,  0,241,255],
                          [  0,  0,132,255]], dtype=np.ubyte)
        # Absolute scale relative to the expected data not important. This 
        # should have the same amount of entries (num parameter) as the number
        # of values given in color. 
        pos = np.linspace(0.0, 1.0, num=len(color))
        
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
        self.xy_refocus_image.setLookupTable(lut)        
        
        # Create colorbars and add them at the desired place in the GUI. Add
        # also units to the colorbar.
        
        self.xy_cb = ColorBar(self.colmap_norm, width=100, cb_min = 0, 
                              cb_max = 100)      
        self.xz_cb = ColorBar(self.colmap_norm, width=100, cb_min = 0, 
                              cb_max = 100)
        self._mw.xy_cb_ViewWidget.addItem(self.xy_cb)
        self._mw.xy_cb_ViewWidget.hideAxis('bottom')
        #self._mw.xy_cb_ViewWidget.hideAxis('left')
        self._mw.xy_cb_ViewWidget.setLabel( 'left', 'Fluorescence', units='c/s' )
        self._mw.xy_cb_ViewWidget.setMouseEnabled(x=False,y=False)
        
        self._mw.xz_cb_ViewWidget_2.addItem(self.xz_cb)
        self._mw.xz_cb_ViewWidget_2.hideAxis('bottom')
        #self._mw.xz_cb_ViewWidget_2.hideAxis('left')
        self._mw.xz_cb_ViewWidget_2.setLabel( 'left', 'Fluorescence', units='c/s' )
        self._mw.xz_cb_ViewWidget_2.setMouseEnabled(x=False,y=False)
        
        
        self.adjust_aspect_roi_xy()
        self.adjust_aspect_roi_xz()
      
        self.xy_image.getViewBox().sigRangeChangedManually.connect(self.adjust_aspect_roi_xy)
        self.xz_image.getViewBox().sigRangeChangedManually.connect(self.adjust_aspect_roi_xz)
        
        #self.xy_image.getViewBox().setXRange(min, max, padding=None, update=True)
        self._mw.ready_StateWidget.click()
        
        # Connect the 'File' Menu dialog in confocal with the methods:
        self._mw.actionSave_XY_Scan.triggered.connect(self.save_xy_scan)
        self._mw.actionSave_XZ_Scan.triggered.connect(self.save_xz_scan) 
        
        # Now that the ROI for xy and xz is connected to events, update the
        # default position:   
        self.update_crosshair_position()
        self.adjust_xy_window()
        self.adjust_xz_window()

        # Show the Main Confocal GUI:
        self._mw.show()
        
        
        
    def update_crosshair_position(self):
        """ Update the GUI position of the crosshair from the logic. """       
        
        x_pos, y_pos, z_pos = self._scanning_logic.get_position()
        
        roi_x_view = x_pos - self.roi_xy.size()[0]*0.5
        roi_y_view = y_pos - self.roi_xy.size()[1]*0.5
        self.roi_xy.setPos([roi_x_view , roi_y_view])
        
        roi_x_view = x_pos - self.roi_xz.size()[0]*0.5
        roi_y_view = z_pos - self.roi_xz.size()[1]*0.5
        self.roi_xz.setPos([roi_x_view , roi_y_view])
        
        
    def refresh_xy_colorbar(self):
        """ Adjust the xy colorbar.
        
        Calls the refresh method from colorbar, which takes either the lowest 
        and higherst value in the image or predefined ranges. Note that you can 
        invert the colorbar if the lower border is bigger then the higher one.
        """
        
        # If "Auto" is checked, adjust colour scaling to fit all data.
        # Otherwise, take user-defined values.
        if self._mw.xy_cb_auto_CheckBox.isChecked():
            cb_min = self.xy_image.image.min()
            cb_max = self.xy_image.image.max()
        else:
            cb_min = float(self._mw.xy_cb_min_InputWidget.text())
            cb_max = float(self._mw.xy_cb_max_InputWidget.text())
            
        self.xy_cb.refresh_colorbar(cb_min,cb_max)    
        self._mw.xy_cb_ViewWidget.update()       

    def refresh_xz_colorbar(self):
        """ Adjust the xz colorbar.
        
        Calls the refresh method from colorbar, which takes either the lowest 
        and higherst value in the image or predefined ranges. Note that you can 
        invert the colorbar if the lower border is bigger then the higher one.
        """

        # If "Auto" is checked, adjust colour scaling to fit all data.
        # Otherwise, take user-defined values.
        if self._mw.xz_cb_auto_CheckBox.isChecked():
            cb_min = self.xz_image.image.min()
            cb_max = self.xz_image.image.max()
        else:
            cb_min = float(self._mw.xz_cb_min_InputWidget.text())
            cb_max = float(self._mw.xz_cb_max_InputWidget.text())

        self.xz_cb.refresh_colorbar(cb_min,cb_max)
        self._mw.xz_cb_ViewWidget_2.addItem(self.xz_cb)


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
        """ This method opens the settings menue. """
        self._sd.exec_()
        
    def update_settings(self):
        """ Write new settings from the gui to the file. """        
        self._scanning_logic.set_clock_frequency(int(self._sd.clock_frequency_InputWidget.text()))
        self._scanning_logic.return_slowness = int(self._sd.return_slowness_InputWidget.text())
        self.fixed_aspect_ratio_xy = self._sd.fixed_aspect_xy_checkBox.isChecked()
        self.fixed_aspect_ratio_xz = self._sd.fixed_aspect_xz_checkBox.isChecked()
        self.slider_stepsize = float(self._sd.slider_stepwidth_InputWidget.value())
        self.image_x_padding = self._sd.x_padding_InputWidget.value()
        self.image_y_padding = self._sd.y_padding_InputWidget.value()
        self.image_z_padding = self._sd.z_padding_InputWidget.value()
        
    def keep_former_settings(self):
        """ Keep the old settings and restores them in the gui. """
        self._sd.clock_frequency_InputWidget.setText(str(int(self._scanning_logic._clock_frequency)))
        self._sd.return_slowness_InputWidget.setText(str(self._scanning_logic.return_slowness))
        self._sd.fixed_aspect_xy_checkBox.setChecked(self.fixed_aspect_ratio_xy)
        self._sd.fixed_aspect_xz_checkBox.setChecked(self.fixed_aspect_ratio_xz)
        self._sd.x_padding_InputWidget.setValue(self.image_x_padding)
        self._sd.y_padding_InputWidget.setValue(self.image_y_padding)
        self._sd.z_padding_InputWidget.setValue(self.image_z_padding)
        
        # the smallest stepsize cannot be smaller then the resolution of the 
        # sliders.
        if self.slider_stepsize < self.slider_res:
            self._mw.x_SliderWidget.setSingleStep = 1
            self._mw.y_SliderWidget.setSingleStep = 1
            self._mw.x_SliderWidget.setSingleStep = 1
        else:
            self._mw.x_SliderWidget.setSingleStep = self.slider_stepsize/self.slider_res
            self._mw.y_SliderWidget.setSingleStep = self.slider_stepsize/self.slider_res
            self._mw.x_SliderWidget.setSingleStep = self.slider_stepsize/self.slider_res

    def ready_clicked(self):
        """ Stopp the scan if the state has switched to ready. """            
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


    def update_roi_xy_change_x(self,x_pos):
        """ Adjust the xy ROI position if the x value has changed.
        
        @param float x_pos: real value of the current x position 
        
        Since the origin of the region of interest (ROI) is not the crosshair
        point but the lowest left point of the square, you have to shift the
        origin according to that. Therefore the position of the ROI is not 
        the actual position!
        """

        x_pos = self._scanning_logic.x_range[0] + x_pos*self.slider_res  
      
        try:  
            roi_x_view = x_pos - self.roi_xy.size()[0]*0.5
            roi_y_view = self.roi_xy.pos()[1]
            
            self.roi_xy.setPos([roi_x_view , roi_y_view])
            self._scanning_logic.set_position(x=x_pos)   
        except:
            self.logMsg('Recursion error in update_roi_xy_change_x', 
                        msgType='warning')
            pass
        
    def update_roi_xy_change_y(self,y_pos):
        """ Adjust the xy ROI position if the y value has changed.
        
        @param float y_pos: real value of the current y value
        
        Since the origin of the region of interest (ROI) is not the crosshair
        point but the lowest left point of the square, you have to shift the
        origin according to that. Therefore the position of the ROI is not 
        the actual position!
        """

        y_pos = self._scanning_logic.y_range[0] + y_pos*self.slider_res  
        
        try:
            roi_x_view = self.roi_xy.pos()[0]
            roi_y_view = y_pos - self.roi_xy.size()[1]*0.5
            
            self.roi_xy.setPos([roi_x_view , roi_y_view])
            self._scanning_logic.set_position(y=y_pos)    
        except:
            self.logMsg('Recursion error in update_roi_xy_change_y', 
                        msgType='warning')
            pass
        
    def update_roi_xz_change_x(self,x_pos):
        """ Adjust the xz ROI position if the x value has changed.
        
        @param float x_pos: real value of the current x value
        
        Since the origin of the region of interest (ROI) is not the crosshair
        point but the lowest left point of the square, you have to shift the
        origin according to that. Therefore the position of the ROI is not 
        the actual position!
        """        

        x_pos = self._scanning_logic.x_range[0] + x_pos*self.slider_res  
        
        try:
            roi_x_view = x_pos - self.roi_xz.size()[0]*0.5
            roi_y_view = self.roi_xz.pos()[1]
            
            self.roi_xz.setPos([roi_x_view , roi_y_view])
            self._scanning_logic.set_position(x=x_pos)        
        except:
            self.logMsg('Recursion error in update_roi_xz_change_x', 
                        msgType='warning')
            pass

    def update_roi_xz_change_z(self,z_pos):
        """ Adjust the xz ROI position if the z value has changed.
        
        @param float z_pos: real value of the current z value
        
        Since the origin of the region of interest (ROI) is not the crosshair
        point but the lowest left point of the square, you have to shift the
        origin according to that. Therefore the position of the ROI is not 
        the actual position!
        """        

        z_pos = self._scanning_logic.z_range[0] + z_pos*self.slider_res         
        
        try:
            roi_x_view = self.roi_xz.pos()[0]
            roi_y_view = z_pos - self.roi_xz.size()[1]*0.5
            
            self.roi_xz.setPos([roi_x_view , roi_y_view])
            self._scanning_logic.set_position(z=z_pos)
        except:
            self.logMsg('Recursion error in update_roi_xz_change_z', 
                        msgType='warning')
            pass
        
    def update_current_x(self,x_pos):
        """ Update the displayed x-value.
        
        @param float x_pos: the current value of the x position        
        """
        # Convert x_pos to number of points for the slider:
        self._mw.x_current_InputWidget.setText('{0:.5}'.format(self._scanning_logic.x_range[0] + x_pos*self.slider_res))

        
    def update_current_y(self,y_pos):
        """ Update the displayed y-value.
        
        @param float y_pos: the current value of the y position        
        """
        # Convert x_pos to number of points for the slider:
        self._mw.y_current_InputWidget.setText('{0:.5}'.format(self._scanning_logic.y_range[0]  + y_pos*self.slider_res))        


    def update_current_z(self,z_pos):
        """ Update the displayed z-value.
        
        @param float z_pos: the current value of the z position        
        """
        # Convert x_pos to number of points for the slider:
        self._mw.z_current_InputWidget.setText('{0:.5}'.format(self._scanning_logic.z_range[0] + z_pos*self.slider_res))


    def update_x_slider(self,roi=None):
        """ Update the x slider if a change happens.
        
        @param object roi: optional, a pyqtgraph.ROI object of the scan which 
                           is passed if the ROI is changed.
        """
        if roi is None:
            self._mw.x_SliderWidget.setValue( int(float(self._mw.x_current_InputWidget.text())/self.slider_res)   )
        else:
            self._mw.x_SliderWidget.setValue( int( (roi.pos()[0]+ 0.5*roi.size()[0]- self._scanning_logic.x_range[0])/self.slider_res) )
        
    def update_y_slider(self,roi=None):
        """ Update the y slider if a change happens.
        
        @param object roi: optional, a pyqtgraph.ROI object of the scan which 
                           is passed if the ROI is changed.
        """
        if roi is None:
            self._mw.y_SliderWidget.setValue( int(float(self._mw.y_current_InputWidget.text())/self.slider_res)    )
        else:
            self._mw.y_SliderWidget.setValue( int( (roi.pos()[1]+ 0.5*roi.size()[1]- self._scanning_logic.y_range[0])/self.slider_res) ) 

    def update_z_slider(self,roi=None):
        """ Update the z slider if a change happens.
        
        @param object roi: optional, a pyqtgraph.ROI object of the scan which 
                           is passed if the ROI is changed.
        """ 
        if roi is None:
            self._mw.z_SliderWidget.setValue( int((float(self._mw.z_current_InputWidget.text()) - self._scanning_logic.z_range[0])/self.slider_res ))
        else:
            self._mw.z_SliderWidget.setValue(int( ( roi.pos()[1] + 0.5*roi.size()[1]  - self._scanning_logic.z_range[0] )/self.slider_res) ) 
            
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

    def shortcut_to_xy_cb_manual(self):
        self._mw.xy_cb_auto_CheckBox.setChecked(False)
        self.update_xy_cb_range()
    
    def shortcut_to_xz_cb_manual(self):
        self._mw.xz_cb_auto_CheckBox.setChecked(False)
        self.update_xz_cb_range()
    
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
          
        self.xy_image.getViewBox().updateAutoRange()
        self.adjust_aspect_roi_xy()
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
            self.refresh_xy_colorbar()
  
        if self._scanning_logic.getState() != 'locked':
            self._mw.ready_StateWidget.click()

    def refresh_xz_image(self):
        """ Update the current XZ image from the logic. 

        Everytime the scanner is scanning a line in xz the 
        image is rebuild and updated in the GUI.        
        """
    
        self.xz_image.getViewBox().updateAutoRange()
        self.adjust_aspect_roi_xz()
        self.put_cursor_in_xz_scan()
        self.adjust_aspect_roi_xz()            
        
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
            
    def refresh_refocus_image(self):
        """Refreshes the xy image, the crosshair and the colorbar. """
        self.xy_refocus_image.setImage(image=self._optimiser_logic.xy_refocus_image[:,:,3].transpose())
        self.xy_refocus_image.setRect(QtCore.QRectF(self._optimiser_logic._trackpoint_x - 0.5 * self._optimiser_logic.refocus_XY_size , self._optimiser_logic._trackpoint_y - 0.5 * self._optimiser_logic.refocus_XY_size , self._optimiser_logic.refocus_XY_size, self._optimiser_logic.refocus_XY_size))               
        self.vLine.setValue(self._optimiser_logic.refocus_x)
        self.hLine.setValue(self._optimiser_logic.refocus_y)
        self.xz_refocus_image.setData(self._optimiser_logic._zimage_Z_values,self._optimiser_logic.z_refocus_line)
        self.xz_refocus_fit_image.setData(self._optimiser_logic._fit_zimage_Z_values,self._optimiser_logic.z_fit_data)
#        self.refresh_xy_colorbar()
        self._mw.x_refocus_position_ViewWidget_2.setText('{0:.3f}'.format(self._optimiser_logic.refocus_x))
        self._mw.y_refocus_position_ViewWidget_2.setText('{0:.3f}'.format(self._optimiser_logic.refocus_y))
        self._mw.z_refocus_position_ViewWidget_2.setText('{0:.3f}'.format(self._optimiser_logic.refocus_z))
        
        
    def adjust_xy_window(self):
        """ Fit the visible window in the xy scan to full view.
        
        Be careful in using that method, since it uses the input values for
        the ranges to adjust x and y. Make sure that in the process of the xz scan
        no method is calling adjust_xz_window, otherwise it will adjust for you
        a window which does not correspond to the scan! 
        """
        # It is extremly crutial that before adjusting the window view and 
        # limits, to make an update of the current image. Otherwise the
        # adjustment will just be made for the previous image.
        self.refresh_xy_image()
         
        xy_viewbox = self.xy_image.getViewBox()      
        
        xMin = self._scanning_logic.image_x_range[0]
        xMax = self._scanning_logic.image_x_range[1]
        yMin = self._scanning_logic.image_y_range[0]
        yMax = self._scanning_logic.image_y_range[1]
        
        if self.fixed_aspect_ratio_xy:
            xy_viewbox.state['limits']['xLimits'] =[None, None]
            xy_viewbox.state['limits']['yLimits'] =[None, None]
            xy_viewbox.state['limits']['xRange'] =[None, None]
            xy_viewbox.state['limits']['yRange'] =[None, None]
            
            xy_viewbox.setAspectLocked(lock=True, ratio = 1.0)
            xy_viewbox.updateViewRange()
            
        else:
            
            xy_viewbox.setLimits(xMin = xMin - xMin*self.image_x_padding,
                                 xMax = xMax + xMax*self.image_x_padding, 
                                 yMin = yMin - yMin*self.image_y_padding,
                                 yMax = yMax + yMax*self.image_y_padding, )                                                 
                                                
        self.xy_image.setRect(QtCore.QRectF(xMin, yMin, xMax - xMin, yMax - yMin))
        xy_viewbox.updateAutoRange()
        xy_viewbox.updateViewRange()
        
    def adjust_xz_window(self):
        """ Fit the visible window in the xz scan to full view.
        
        Be careful in using that method, since it uses the input values for
        the ranges to adjust x and z. Make sure that in the process of the xz scan
        no method is calling adjust_xy_window, otherwise it will adjust for you
        a window which does not correspond to the scan! 
        """
        # It is extremly crutial that before adjusting the window view and 
        # limits, to make an update of the current image. Otherwise the
        # adjustment will just be made for the previous image.
        self.refresh_xz_image()
         
        xz_viewbox = self.xz_image.getViewBox()      
        
        xMin = self._scanning_logic.image_x_range[0]
        xMax = self._scanning_logic.image_x_range[1]
        zMin = self._scanning_logic.image_z_range[0]
        zMax = self._scanning_logic.image_z_range[1]        


        if self.fixed_aspect_ratio_xz:
            # Reset the limit settings so that the method 'setAspectLocked'
            # works properly.
            xz_viewbox.state['limits']['xLimits'] =[None, None]
            xz_viewbox.state['limits']['yLimits'] =[None, None]
            xz_viewbox.state['limits']['xRange'] =[None, None]
            xz_viewbox.state['limits']['yRange'] =[None, None]
            
            xz_viewbox.setAspectLocked(lock=True, ratio = 1.0)
            xz_viewbox.updateViewRange()
            
        else:
            
            xz_viewbox.setLimits(xMin = xMin - xMin*self.image_x_padding,
                                 xMax = xMax + xMax*self.image_x_padding, 
                                 yMin = zMin - zMin*self.image_z_padding,
                                 yMax = zMax + zMax*self.image_z_padding, )         
        
        self.xy_image.setRect(QtCore.QRectF(xMin, zMin, xMax - xMin, zMax - zMin))
        xz_viewbox.updateAutoRange()
        xz_viewbox.updateViewRange()

    def put_cursor_in_xy_scan(self):
        """Put the xy crosshair back if it is outside of the visible range. """
        
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
        """Put the xz crosshair back if it is outside of the visible range. """
        
        view_x_min = float(self._mw.x_min_InputWidget.text())
        view_x_max = float(self._mw.x_max_InputWidget.text())
        view_z_min = float(self._mw.z_min_InputWidget.text())
        view_z_max = float(self._mw.z_max_InputWidget.text()) 
        
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

      
    def adjust_aspect_roi_xy(self):
        """ Keep the aspect ratio of the ROI also during the zoom the same. 
        
        @param object viewbox: pyqtgraph.ViewBox object, which contains the 
                               view information about the display.
        """
        viewbox = self.xy_image.getViewBox()
        current_x_view_range = viewbox.viewRange()[0][1] - viewbox.viewRange()[0][0]
        current_y_view_range = viewbox.viewRange()[1][1] - viewbox.viewRange()[1][0]
        
        new_size_x_roi = current_x_view_range/20
        new_size_y_roi = current_y_view_range/20
        
        old_size_x_roi = self.roi_xy.size()[0] 
        old_size_y_roi = self.roi_xy.size()[1]

        diff_size_x_roi = (old_size_x_roi - new_size_x_roi)*0.5
        diff_size_y_roi = (old_size_y_roi - new_size_y_roi)*0.5
        
        # Here it is really necessary not to update, otherwise you will
        # calculate the position of the roi in a wrong way.
        self.roi_xy.setSize([new_size_x_roi,new_size_y_roi], update=False)
        pos = self.roi_xy.pos()
        self.roi_xy.setPos([pos[0]+diff_size_x_roi,pos[1]+diff_size_y_roi], update=True)

    
    def adjust_aspect_roi_xz(self,viewbox=None):
        """ Keep the aspect ratio of the ROI also during the zoom the same. 
        
        @param object viewbox: pyqtgraph.ViewBox object, which contains the 
                               view information about the display.
        
        """
        viewbox = self.xz_image.getViewBox()
        current_x_view_range = viewbox.viewRange()[0][1] - viewbox.viewRange()[0][0]
        current_z_view_range = viewbox.viewRange()[1][1] - viewbox.viewRange()[1][0]
        
        new_size_x_roi = current_x_view_range/20
        new_size_z_roi = current_z_view_range/20
        
        old_size_x_roi = self.roi_xz.size()[0] 
        old_size_z_roi = self.roi_xz.size()[1]

        diff_size_x_roi = (old_size_x_roi - new_size_x_roi)*0.5
        diff_size_z_roi = (old_size_z_roi - new_size_z_roi)*0.5
        
        # Here it is really necessary not to update, otherwise you will
        # calculate the position of the roi in a wrong way.
        self.roi_xz.setSize([new_size_x_roi,new_size_z_roi], update=False)
        pos = self.roi_xz.pos()
        self.roi_xz.setPos([pos[0]+diff_size_x_roi,pos[1]+diff_size_z_roi], update=True)

    def save_xy_scan(self):
        """ Run the save routine from the logic to save the xy confocal pic."""
        self._scanning_logic.save_xy_data()
        
    def save_xz_scan(self):
        """ Run the save routine from the logic to save the xy confocal pic."""      
        self._scanning_logic.save_xz_data()
        
        
