# -*- coding: utf-8 -*-

"""
This file contains the QuDi GUI module base class.

QuDi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

QuDi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with QuDi. If not, see <http://www.gnu.org/licenses/>.

Copyright (C) 2015 Florian S. Frank florian.frank@uni-ulm.de
Copyright (C) 2015 Alexander Stark alexander.stark@uni-ulm.de
"""

#from PyQt4 import QtCore, QtGui
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph as pg
import pyqtgraph.exporters
import numpy as np
import copy
import time

from collections import OrderedDict
from gui.GUIBase import GUIBase
from gui.Confocal.ConfocalGuiUI import Ui_MainWindow
from gui.Confocal.ConfocalSettingsUI import Ui_SettingsDialog
from gui.Optimiser.OptimiserSettingsUI import Ui_SettingsDialog as Ui_OptimiserSettingsDialog


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

    def refresh_colorbar(self, cb_min, cb_max, width = None, height = None, xMin = None, yMin = None):
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
        if xMin is None:
            p.drawRect(pg.QtCore.QRectF(0, cb_min, width, cb_max-cb_min))
        else:
            # If this picture whants to be set in a plot, which is going to be 
            # saved:
            p.drawRect(pg.QtCore.QRectF(xMin, yMin, width, height)) 
        p.end()

        vb = self.getViewBox()
        # check whether a viewbox is already created for this object. If yes,
        # then it should be adjusted according to the full screen.        
        if vb is not None:
            vb.updateAutoRange()
            vb.enableAutoRange()
        
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
    """ Create the Mainwindow based on the corresponding *.ui file. """
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.setupUi(self)
        
        
class ConfocalSettingDialog(QtGui.QDialog,Ui_SettingsDialog):
    """ Create the SettingsDialog window, based on the corresponding *.ui file."""
    def __init__(self):
        QtGui.QDialog.__init__(self)
        self.setupUi(self)
        
class OptimiserSettingDialog(QtGui.QDialog,Ui_OptimiserSettingsDialog):
    def __init__(self):
        QtGui.QDialog.__init__(self)
        self.setupUi(self)
        

class ConfocalGui(GUIBase):
    """ Main Confocal Class for xy and depth scans.
    """
    _modclass = 'ConfocalGui'
    _modtype = 'gui'
        
    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        c_dict = {'onactivate': self.initUI}
        super().__init__(manager, name, config, c_dict)
        
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
        
        self.connector['in']['savelogic'] = OrderedDict()
        self.connector['in']['savelogic']['class'] = 'SaveLogic'
        self.connector['in']['savelogic']['object'] = None

        self.logMsg('The following configuration was found.', 
                    msgType='status')
                            
        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]), 
                        msgType='status')  
        
        self.fixed_aspect_ratio_xy = config['fixed_aspect_ratio_xy']
        self.fixed_aspect_ratio_depth = config['fixed_aspect_ratio_depth']
        self.slider_stepsize = config['slider_stepsize']
        self.image_x_padding = config['image_x_padding']
        self.image_y_padding = config['image_y_padding']
        self.image_z_padding = config['image_z_padding']

    def initUI(self, e=None):
        """ Initializes all needed UI files and establishes the connectors.
        
        This method executes the all the inits for the differnt GUIs and passes
        the event argument from fysom to the methods."""
        
        # Getting an access to all connectors:
        self._scanning_logic = self.connector['in']['confocallogic1']['object']
        self._save_logic = self.connector['in']['savelogic']['object']
        self._optimiser_logic = self.connector['in']['optimiserlogic1']['object']
        self._save_logic = self.connector['in']['savelogic']['object']        
        
        self._hardware_state = True
        
        self.initMainUI(e)      # initialize the main GUI
        self.initSettingsUI(e)  # initialize the settings GUI
        self.initOptimiserSettingsUI(e) # initialize the optimiser settings GUI

    def initMainUI(self, e=None):
        """ Definition, configuration and initialisation of the confocal GUI.
          
        @param object e: Event class object from Fysom.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look in
                         the Base Class). This object contains the passed event
                         the state before the event happens and the destination
                         of the state which should be reached after the event
                         has happen.

        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules. 
        Moreover it sets default values.
        """
#FIXME: can we delete all the commented stuff in this method? I have deleted 
#       all commented stuff which I do not need. The rest of them I will later
#       integrate in the code. --Alex
# FIXME: Save in the png or svg images also the colorbar
        
        self._mw = ConfocalMainWindow()
        
        
        #####################
        # Configuring the dock widgets
        #####################

        # All our gui elements are dockable, and so there should be no "central" widget.
        self._mw.centralwidget.hide()
        self._mw.setDockNestingEnabled(True)

        #####################
        # Adding view toggle actions to menu
        #####################

        self._mw.scan_control_dockWidget.toggleViewAction().setShortcut("Ctrl+R")
        self._mw.menuView.addAction(self._mw.scan_control_dockWidget.toggleViewAction() )
        self._mw.xy_scan_dockWidget.toggleViewAction().setShortcut("Ctrl+E")
        self._mw.menuView.addAction(self._mw.xy_scan_dockWidget.toggleViewAction() )
        self._mw.depth_scan_dockWidget.toggleViewAction().setShortcut("Ctrl+D")
        self._mw.menuView.addAction(self._mw.depth_scan_dockWidget.toggleViewAction() )
        self._mw.optimizer_dockWidget.toggleViewAction().setShortcut("Ctrl+O")
        self._mw.menuView.addAction(self._mw.optimizer_dockWidget.toggleViewAction() )

        
        # Get the image for the display from the logic. Transpose the received
        # matrix to get the proper scan. The graphig widget displays vector-
        # wise the lines and the lines are normally columns, but in our 
        # measurement we scan rows per row. That's why it has to be transposed.
        arr01 = self._scanning_logic.xy_image[:,:,3].transpose()
        arr02 = self._scanning_logic.depth_image[:,:,3].transpose()

        # Set initial position for the crosshair, default is the middle of the
        # screen:
        ini_pos_x_crosshair = len(arr01)/2
        ini_pos_y_crosshair = len(arr01)/2
        ini_pos_z_crosshair = len(arr02)/2
        
        # Load the images for xy and depth in the display:
        self.xy_image = pg.ImageItem(arr01)
        self.depth_image = pg.ImageItem(arr02)

        #######################################################################
        ###               Configuration of the optimiser tab                ###
        #######################################################################
        
        # Load the image for the optimiser tab                                    
        self.xy_refocus_image = pg.ImageItem(self._optimiser_logic.xy_refocus_image[:,:,3].transpose())
        self.xy_refocus_image.setRect(QtCore.QRectF(self._optimiser_logic._trackpoint_x - 0.5 * self._optimiser_logic.refocus_XY_size,
                                                    self._optimiser_logic._trackpoint_y - 0.5 * self._optimiser_logic.refocus_XY_size,
                                                    self._optimiser_logic.refocus_XY_size, self._optimiser_logic.refocus_XY_size))               
        self.depth_refocus_image = pg.ScatterPlotItem(self._optimiser_logic._zimage_Z_values,
                                                self._optimiser_logic.z_refocus_line, 
                                                symbol='o')
        self.depth_refocus_fit_image = pg.PlotDataItem(self._optimiser_logic._fit_zimage_Z_values,
                                                    self._optimiser_logic.z_fit_data, 
                                                    pen=QtGui.QPen(QtGui.QColor(255,0,255,255)))
                                                    
        # Add the display item to the xy and depth VieWidget, which was defined in
        # the UI file.
        self._mw.xy_refocus_ViewWidget_2.addItem(self.xy_refocus_image)
        self._mw.depth_refocus_ViewWidget_2.addItem(self.depth_refocus_image)

        # Labelling axes
        self._mw.xy_refocus_ViewWidget_2.setLabel( 'bottom', 'X position', units='µm' )
        self._mw.xy_refocus_ViewWidget_2.setLabel( 'left', 'Y position', units='µm' )

        self._mw.depth_refocus_ViewWidget_2.addItem(self.depth_refocus_fit_image)

        self._mw.depth_refocus_ViewWidget_2.setLabel( 'bottom', 'Z position', units='µm' )
        self._mw.depth_refocus_ViewWidget_2.setLabel( 'left', 'Fluorescence', units='c/s' )
        
        #Add crosshair to the xy refocus scan
        self.vLine = pg.InfiniteLine(pen=QtGui.QPen(QtGui.QColor(255,0,255,255), 0.02), pos=50, angle=90, movable=False)
        self.hLine = pg.InfiniteLine(pen=QtGui.QPen(QtGui.QColor(255,0,255,255), 0.02), pos=50, angle=0, movable=False)
        self._mw.xy_refocus_ViewWidget_2.addItem(self.vLine, ignoreBounds=True)
        self._mw.xy_refocus_ViewWidget_2.addItem(self.hLine, ignoreBounds=True)
        
        
        # Set the state button as ready button as default setting.
        self._mw.ready_StateWidget.click()

        # Add the display item to the xy and depth ViewWidget, which was defined 
        # in the UI file:
        self._mw.xy_ViewWidget.addItem(self.xy_image)
        self._mw.depth_ViewWidget.addItem(self.depth_image)
        
        # Label the axes:
        self._mw.xy_ViewWidget.setLabel( 'bottom', 'X position', units='µm' )
        self._mw.xy_ViewWidget.setLabel( 'left', 'Y position', units='µm' )
        self._mw.depth_ViewWidget.setLabel( 'bottom', 'X position', units='µm' )
        self._mw.depth_ViewWidget.setLabel( 'left', 'Z position', units='µm' )
    
        # Create Region of Interest for xy image and add to xy Image Widget:
        self.roi_xy = CrossROI([ini_pos_x_crosshair-len(arr01)/40, ini_pos_y_crosshair-len(arr01)/40], 
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

        # Create Region of Interest for depth image and add to xy Image Widget:
        self.roi_depth = CrossROI([ini_pos_x_crosshair-len(arr02)/20, 
                                ini_pos_z_crosshair-len(arr02)/20], 
                               [len(arr02)/20, len(arr02)/20], 
                               pen={'color': "F0F", 'width': 1},
                               removable=True )
        self._mw.depth_ViewWidget.addItem(self.roi_depth)

        # create horizontal and vertical line as a crosshair in depth image:
        self.hline_depth = CrossLine(pos=self.roi_depth.pos()+self.roi_depth.size()*0.5, 
                                  angle=0, pen={'color': "F0F", 'width': 1} )
        self.vline_depth = CrossLine(pos=self.roi_depth.pos()+self.roi_depth.size()*0.5, 
                                  angle=90, pen={'color': "F0F", 'width': 1} )

        # connect the change of a region with the adjustment of the crosshair:
        self.roi_depth.sigRegionChanged.connect(self.hline_depth.adjust)
        self.roi_depth.sigRegionChanged.connect(self.vline_depth.adjust)
        
        # connect the change of a region with the adjustment of the sliders:
        self.roi_depth.sigRegionChanged.connect(self.update_x_slider)
        self.roi_depth.sigRegionChanged.connect(self.update_z_slider)        
        
        # add the configured crosshair to the depth Widget:
        self._mw.depth_ViewWidget.addItem(self.hline_depth)
        self._mw.depth_ViewWidget.addItem(self.vline_depth)
        
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
        
        # Just to be sure, set also the possible maximal values for the spin
        # boxes of the current values:
        self._mw.x_current_InputWidget.setRange(self._scanning_logic.x_range[0], 
                                                self._scanning_logic.x_range[1])
        self._mw.y_current_InputWidget.setRange(self._scanning_logic.y_range[0], 
                                                self._scanning_logic.y_range[1])
        self._mw.z_current_InputWidget.setRange(self._scanning_logic.z_range[0], 
                                                self._scanning_logic.z_range[1])

        # Predefine the maximal and minimal image range as the default values
        # for the display of the range:
        self._mw.x_min_InputWidget.setValue(self._scanning_logic.image_x_range[0])
        self._mw.x_max_InputWidget.setValue(self._scanning_logic.image_x_range[1])
        self._mw.y_min_InputWidget.setValue(self._scanning_logic.image_y_range[0])
        self._mw.y_max_InputWidget.setValue(self._scanning_logic.image_y_range[1])
        self._mw.z_min_InputWidget.setValue(self._scanning_logic.image_z_range[0])
        self._mw.z_max_InputWidget.setValue(self._scanning_logic.image_z_range[1]) 

        # Connect the change of the slider with the adjustment of the ROI: 
        self._mw.x_SliderWidget.valueChanged.connect(self.update_roi_xy_change_x)
        self._mw.y_SliderWidget.valueChanged.connect(self.update_roi_xy_change_y)

        self._mw.x_SliderWidget.valueChanged.connect(self.update_roi_depth_change_x)
        self._mw.z_SliderWidget.valueChanged.connect(self.update_roi_depth_change_z)

        # Take the default values from logic:
        self._mw.xy_res_InputWidget.setValue(self._scanning_logic.xy_resolution)     
        self._mw.z_res_InputWidget.setValue(self._scanning_logic.z_resolution)
        
        # Connect the Slider with an update in the current values of x,y and z.
        self._mw.x_SliderWidget.valueChanged.connect(self.update_current_x)
        self._mw.y_SliderWidget.valueChanged.connect(self.update_current_y)
        self._mw.z_SliderWidget.valueChanged.connect(self.update_current_z)

        
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

        
        # Connect the change of the viewed area to an adjustment of the ROI:
        self.xy_image.getViewBox().sigRangeChanged.connect(self.adjust_aspect_roi_xy)
        self.depth_image.getViewBox().sigRangeChanged.connect(self.adjust_aspect_roi_depth)
        
        # Connect the RadioButtons to the events if they are clicked. Connect
        # also the adjustment of the displayed windows.
        self._mw.ready_StateWidget.toggled.connect(self.ready_clicked)
        
        self._mw.xy_scan_StateWidget.toggled.connect(self.xy_scan_clicked)
        self._mw.continue_xy_scan_StateWidget.toggled.connect(self.continue_xy_scan_clicked)
        self._mw.depth_scan_StateWidget.toggled.connect(self.depth_scan_clicked)
        
        self._mw.refocus_StateWidget.toggled.connect(self.refocus_clicked)


        # Connect the buttons and inputs for the xy colorbar
        self._mw.xy_cb_manual_RadioButton.clicked.connect(self.update_xy_cb_range)
        self._mw.xy_cb_centiles_RadioButton.clicked.connect(self.update_xy_cb_range)

        self._mw.xy_cb_min_InputWidget.valueChanged.connect( self.shortcut_to_xy_cb_manual )
        self._mw.xy_cb_max_InputWidget.valueChanged.connect( self.shortcut_to_xy_cb_manual )
        self._mw.xy_cb_low_centile_InputWidget.valueChanged.connect( self.shortcut_to_xy_cb_centiles )
        self._mw.xy_cb_high_centile_InputWidget.valueChanged.connect( self.shortcut_to_xy_cb_centiles )

        # Connect the buttons and inputs for the depth colorbars
            #RadioButtons in Main tab
        self._mw.depth_cb_manual_RadioButton.clicked.connect(self.toggle_depth_cb_mode)
        self._mw.depth_cb_centiles_RadioButton.clicked.connect(self.toggle_depth_cb_mode)

            #input edits in Main tab
        self._mw.depth_cb_min_InputWidget.valueChanged.connect( self.shortcut_to_depth_cb_manual )
        self._mw.depth_cb_max_InputWidget.valueChanged.connect( self.shortcut_to_depth_cb_manual )
        self._mw.depth_cb_low_centile_InputWidget.valueChanged.connect( self.shortcut_to_depth_cb_centiles )
        self._mw.depth_cb_high_centile_InputWidget.valueChanged.connect( self.shortcut_to_depth_cb_centiles )


        # Connect the emitted signal of an image change from the logic with
        # a refresh of the GUI picture: 
        self._scanning_logic.signal_xy_image_updated.connect(self.refresh_xy_image)
        self._scanning_logic.signal_depth_image_updated.connect(self.refresh_depth_image)
        self._optimiser_logic.signal_image_updated.connect(self.refresh_refocus_image)
        self._scanning_logic.sigImageXYInitialized.connect(self.adjust_xy_window)
        self._scanning_logic.sigImageDepthInitialized.connect(self.adjust_depth_window) 
        
        # Connect the signal from the logic with an update of the cursor position
        self._scanning_logic.signal_change_position.connect(self.update_crosshair_position)
        
        # Connect the tracker
        self._optimiser_logic.signal_refocus_finished.connect(self._refocus_finished_wrapper)
        self._optimiser_logic.signal_refocus_started.connect(self.disable_scan_buttons)

        # Connect the 'File' Menu dialog and the Settings window in confocal
        # with the methods:        
        self._mw.action_Settings.triggered.connect(self.menue_settings)
        self._mw.action_optimiser_settings.triggered.connect(self.menue_optimiser_settings)
        self._mw.actionSave_XY_Scan.triggered.connect(self.save_xy_scan_data)
        self._mw.actionSave_Depth_Scan.triggered.connect(self.save_depth_scan_data) 
        self._mw.actionSave_XY_Image_Data.triggered.connect(self.save_xy_scan_image) 
        self._mw.actionSave_Depth_Image_Data.triggered.connect(self.save_depth_scan_image) 

        # create a color map that goes from dark red to dark blue:
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
                               
        color_new = np.array([ [  0,  0,132,255], [  0,  0,241,255], [  0, 88,255,255],
                               [  0,204,255,255], [ 66,255,149,255], [160,255, 86,255],
                               [254,237,  0,255], [255,129,  0,255], [255, 26,  0,255]
                               ], dtype=np.ubyte)
                               
        color_new_inv = np.array([ [255, 26,  0,255], [255,129,  0,255], [254,237,  0,255],
                               [160,255, 86,255], [ 66,255,149,255], [  0,204,255,255],
                               [  0, 88,255,255], [  0,  0,241,255], [  0,  0,132,255]
                               ], dtype=np.ubyte)
                               
        pos_2 = np.linspace(0.0, 1.0, num=len(color_new))
                               
        colmap = pg.ColorMap(pos_2, color_new)
        
        self.colmap_norm = pg.ColorMap(pos, color_new_inv/255)
        
        # get the LookUpTable (LUT), first two params should match the position
        # scale extremes passed to ColorMap(). 
        # Return an RGB(A) lookup table (ndarray). Insert starting and stopping
        # value and the number of points in the returned lookup table:
        lut = colmap.getLookupTable(0, 1, 2000)
            
        self.xy_image.setLookupTable(lut)
        self.depth_image.setLookupTable(lut)
        self.xy_refocus_image.setLookupTable(lut)        
        
        # Create colorbars and add them at the desired place in the GUI. Add
        # also units to the colorbar.
        
        self.xy_cb = ColorBar(self.colmap_norm, width=100, cb_min = 0, 
                              cb_max = 100)      
        self.depth_cb = ColorBar(self.colmap_norm, width=100, cb_min = 0, 
                              cb_max = 100)
        self._mw.xy_cb_ViewWidget.addItem(self.xy_cb)
        self._mw.xy_cb_ViewWidget.hideAxis('bottom')
        self._mw.xy_cb_ViewWidget.setLabel( 'left', 'Fluorescence', units='c/s' )
        self._mw.xy_cb_ViewWidget.setMouseEnabled(x=False,y=False)
        
        self._mw.depth_cb_ViewWidget.addItem(self.depth_cb)
        self._mw.depth_cb_ViewWidget.hideAxis('bottom')
        self._mw.depth_cb_ViewWidget.setLabel( 'left', 'Fluorescence', units='c/s' )
        self._mw.depth_cb_ViewWidget.setMouseEnabled(x=False,y=False)
        
        
        # Now that the ROI for xy and depth is connected to events, update the
        # default position and initialize the position of the crosshair and
        # all other components:
        self.adjust_aspect_roi_xy()
        self.adjust_aspect_roi_depth()
        self._mw.ready_StateWidget.click()
        self.update_crosshair_position()
        self.adjust_xy_window()
        self.adjust_depth_window()

        self.show()

    def initSettingsUI(self, e=None):
        """ Definition, configuration and initialisation of the settings GUI.
          
        @param class e: event class from Fysom


        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules. 
        Moreover it sets default values if not existed in the logic modules.
        """
        
        # Create the Settings window
        self._sd = ConfocalSettingDialog()
        # Connect the action of the settings window with the code:
        self._sd.accepted.connect(self.update_settings)
        self._sd.rejected.connect(self.keep_former_settings)
        self._sd.buttonBox.button(QtGui.QDialogButtonBox.Apply).clicked.connect(self.update_settings)
        self._sd.hardware_switch.clicked.connect(self.switch_hardware) 
        
        # write the configuration to the settings window of the GUI. 
        self.keep_former_settings()
        
    def initOptimiserSettingsUI(self, e=None):
        """ Definition, configuration and initialisation of the optimiser settings GUI.
          
        @param class e: event class from Fysom


        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules. 
        Moreover it sets default values if not existed in the logic modules.
        """
        
        # Create the Settings window
        self._osd = OptimiserSettingDialog()
        # Connect the action of the settings window with the code:
        self._osd.accepted.connect(self.update_optimiser_settings)
        self._osd.rejected.connect(self.keep_former_optimiser_settings)
        self._osd.buttonBox.button(QtGui.QDialogButtonBox.Apply).clicked.connect(self.update_optimiser_settings)
        
        # write the configuration to the settings window of the GUI. 
        self.keep_former_optimiser_settings()
        
    def show(self):
        """Make window visible and put it above all other windows. """
        # Show the Main Confocal GUI:
        self._mw.show()
        self._mw.activateWindow()
        self._mw.raise_()
        
    def update_crosshair_position(self):
        """ Update the GUI position of the crosshair from the logic. """       
        
        x_pos, y_pos, z_pos = self._scanning_logic.get_position()

        roi_x_view = x_pos - self.roi_xy.size()[0]*0.5
        roi_y_view = y_pos - self.roi_xy.size()[1]*0.5
        self.roi_xy.setPos([roi_x_view , roi_y_view])
        
        roi_x_view = x_pos - self.roi_depth.size()[0]*0.5
        roi_y_view = z_pos - self.roi_depth.size()[1]*0.5
        self.roi_depth.setPos([roi_x_view , roi_y_view])

        
    def refresh_xy_colorbar(self):
        """ Adjust the xy colorbar.
        
        Calls the refresh method from colorbar, which takes either the lowest 
        and higherst value in the image or predefined ranges. Note that you can 
        invert the colorbar if the lower border is bigger then the higher one.
        """
        # If "Centiles" is checked, adjust colour scaling automatically to centiles.
        # Otherwise, take user-defined values.
        if self._mw.xy_cb_centiles_RadioButton.isChecked():
            low_centile = self._mw.xy_cb_low_centile_InputWidget.value()
            high_centile = self._mw.xy_cb_high_centile_InputWidget.value() 

            cb_min = np.percentile( self.xy_image.image, low_centile ) 
            cb_max = np.percentile( self.xy_image.image, high_centile ) 

        else:
            cb_min = self._mw.xy_cb_min_InputWidget.value()
            cb_max = self._mw.xy_cb_max_InputWidget.value()

#        self.xy_cb.refresh_colorbar(cb_min,cb_max)    
        self._mw.xy_cb_ViewWidget.update()       

    def refresh_depth_colorbar(self):
        """ Adjust the depth colorbar.
        
        Calls the refresh method from colorbar, which takes either the lowest 
        and higherst value in the image or predefined ranges. Note that you can 
        invert the colorbar if the lower border is bigger then the higher one.
        """

        # If "Auto" is checked, adjust colour scaling to fit all data.
        # Otherwise, take user-defined values.
        if self._mw.depth_cb_centiles_RadioButton.isChecked():
            low_centile = self._mw.depth_cb_low_centile_InputWidget.value()
            high_centile = self._mw.depth_cb_high_centile_InputWidget.value() 

            cb_min = np.percentile( self.depth_image.image, low_centile ) 
            cb_max = np.percentile( self.depth_image.image, high_centile ) 

        else:
            cb_min = self._mw.depth_cb_min_InputWidget.value()
            cb_max = self._mw.depth_cb_max_InputWidget.value()

        self.depth_cb.refresh_colorbar(cb_min,cb_max)


    def disable_scan_buttons(self, newstate=False):
        """ Disables the radio buttons for scanning.
        
        @param bool newstate: disabled (False), enabled (True)
        """        
        self._mw.xy_scan_StateWidget.setEnabled(newstate)
        self._mw.depth_scan_StateWidget.setEnabled(newstate)
        self._mw.refocus_StateWidget.setEnabled(newstate)
        self._mw.continue_xy_scan_StateWidget.setEnabled(newstate)


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
        self._scanning_logic.set_clock_frequency(self._sd.clock_frequency_InputWidget.value())
        self._scanning_logic.return_slowness = self._sd.return_slowness_InputWidget.value()
        self.fixed_aspect_ratio_xy = self._sd.fixed_aspect_xy_checkBox.isChecked()
        self.fixed_aspect_ratio_depth = self._sd.fixed_aspect_depth_checkBox.isChecked()
        self.slider_stepsize = self._sd.slider_stepwidth_InputWidget.value()
#        self.image_x_padding = self._sd.x_padding_InputWidget.value()
#        self.image_y_padding = self._sd.y_padding_InputWidget.value()
#        self.image_z_padding = self._sd.z_padding_InputWidget.value()
        
    def keep_former_settings(self):
        """ Keep the old settings and restores them in the gui. """
        self._sd.clock_frequency_InputWidget.setValue(int(self._scanning_logic._clock_frequency))
        self._sd.return_slowness_InputWidget.setValue(int(self._scanning_logic.return_slowness))
        self._sd.fixed_aspect_xy_checkBox.setChecked(self.fixed_aspect_ratio_xy)
        self._sd.fixed_aspect_depth_checkBox.setChecked(self.fixed_aspect_ratio_depth)
#        self._sd.x_padding_InputWidget.setValue(self.image_x_padding)
#        self._sd.y_padding_InputWidget.setValue(self.image_y_padding)
#        self._sd.z_padding_InputWidget.setValue(self.image_z_padding)
        
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
                        
    def menue_optimiser_settings(self):
        """ This method opens the settings menue. """
        self._osd.exec_()
        
    def update_optimiser_settings(self):
        """ Write new settings from the gui to the file. """        
        self._optimiser_logic.refocus_XY_size = float(self._osd.xy_refocusrange_InputWidget.text())
        self._optimiser_logic.refocus_XY_step = float(self._osd.xy_refocusstepsize_InputWidget.text())
        self._optimiser_logic.refocus_Z_size = float(self._osd.z_refocusrange_InputWidget.text())
        self._optimiser_logic.refocus_Z_step = float(self._osd.z_refocusstepsize_InputWidget.text())
        self._optimiser_logic.set_clock_frequency(self._osd.count_freq_InputWidget.text())
        self._optimiser_logic.return_slowness = float(self._osd.return_slow_InputWidget.text())
        
    def keep_former_optimiser_settings(self):
        """ Keep the old settings and restores them in the gui. """
        self._osd.xy_refocusrange_InputWidget.setText(str(self._optimiser_logic.refocus_XY_size))
        self._osd.xy_refocusstepsize_InputWidget.setText(str(self._optimiser_logic.refocus_XY_step))
        self._osd.z_refocusrange_InputWidget.setText(str(self._optimiser_logic.refocus_Z_size))
        self._osd.z_refocusstepsize_InputWidget.setText(str(self._optimiser_logic.refocus_Z_step))
        self._osd.count_freq_InputWidget.setText(str(self._optimiser_logic._clock_frequency))
        self._osd.return_slow_InputWidget.setText(str(self._optimiser_logic.return_slowness))


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
      
    def continue_xy_scan_clicked(self, enabled):
        """ Manages what happens if the xy scan is continued.
        
        @param bool enabled: continue scan if that is possible
        """        
        #Firstly stop any scan that might be in progress
        self._scanning_logic.stop_scanning() 
             
        #Then if enabled. start a new scan.
        if enabled:
            self._scanning_logic.continue_scanning()
            self.disable_scan_buttons()      
      
    def depth_scan_clicked(self, enabled):
        """ Manages what happens if the depth scan is started.
        
        @param bool enabled: start scan if that is possible
        """
        #Firstly stop any scan that might be in progress
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
            self.logMsg('Catchup of the Recursion error in update_roi_xy_change_x', 
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
            self.logMsg('Catchup of the Recursion error in update_roi_xy_change_y', 
                        msgType='warning')
            pass
        
    def update_roi_depth_change_x(self,x_pos):
        """ Adjust the depth ROI position if the x value has changed.
        
        @param float x_pos: real value of the current x value
        
        Since the origin of the region of interest (ROI) is not the crosshair
        point but the lowest left point of the square, you have to shift the
        origin according to that. Therefore the position of the ROI is not 
        the actual position!
        """        

        x_pos = self._scanning_logic.x_range[0] + x_pos*self.slider_res  
        
        try:
            roi_x_view = x_pos - self.roi_depth.size()[0]*0.5
            roi_y_view = self.roi_depth.pos()[1]
            
            self.roi_depth.setPos([roi_x_view , roi_y_view])
            self._scanning_logic.set_position(x=x_pos)        
        except:
            self.logMsg('Catchup of the Recursion error in update_roi_depth_change_x', 
                        msgType='warning')
            pass

    def update_roi_depth_change_z(self,z_pos):
        """ Adjust the depth ROI position if the z value has changed.
        
        @param float z_pos: real value of the current z value
        
        Since the origin of the region of interest (ROI) is not the crosshair
        point but the lowest left point of the square, you have to shift the
        origin according to that. Therefore the position of the ROI is not 
        the actual position!
        """        

        z_pos = self._scanning_logic.z_range[0] + z_pos*self.slider_res         
        
        try:
            roi_x_view = self.roi_depth.pos()[0]
            roi_y_view = z_pos - self.roi_depth.size()[1]*0.5
            
            self.roi_depth.setPos([roi_x_view , roi_y_view])
            self._scanning_logic.set_position(z=z_pos)
        except:
            self.logMsg('Catchup of the Recursion error in update_roi_depth_change_z', 
                        msgType='warning')
            pass
        
    def update_current_x(self,x_pos):
        """ Update the displayed x-value.
        
        @param float x_pos: the current value of the x position        
        """
        # Convert x_pos to number of points for the slider:
        self._mw.x_current_InputWidget.setValue(self._scanning_logic.x_range[0] + x_pos*self.slider_res)

        
    def update_current_y(self,y_pos):
        """ Update the displayed y-value.
        
        @param float y_pos: the current value of the y position        
        """
        # Convert x_pos to number of points for the slider:
        self._mw.y_current_InputWidget.setValue(self._scanning_logic.y_range[0]  + y_pos*self.slider_res)    


    def update_current_z(self,z_pos):
        """ Update the displayed z-value.
        
        @param float z_pos: the current value of the z position        
        """
        # Convert x_pos to number of points for the slider:
        self._mw.z_current_InputWidget.setValue(self._scanning_logic.z_range[0] + z_pos*self.slider_res)


    def update_x_slider(self,roi=None):
        """ Update the x slider if a change happens.
        
        @param object roi: optional, a pyqtgraph.ROI object of the scan which 
                           is passed if the ROI is changed.
        """
        if roi is None:
            self._mw.x_SliderWidget.setValue( int(self._mw.x_current_InputWidget.value()/self.slider_res)   )
        else:
            self._mw.x_SliderWidget.setValue( int( (roi.pos()[0]+ 0.5*roi.size()[0]- self._scanning_logic.x_range[0])/self.slider_res) )
        
    def update_y_slider(self,roi=None):
        """ Update the y slider if a change happens.
        
        @param object roi: optional, a pyqtgraph.ROI object of the scan which 
                           is passed if the ROI is changed.
        """
        if roi is None:
            self._mw.y_SliderWidget.setValue( int(self._mw.y_current_InputWidget.value()/self.slider_res)    )
        else:
            self._mw.y_SliderWidget.setValue( int( (roi.pos()[1]+ 0.5*roi.size()[1]- self._scanning_logic.y_range[0])/self.slider_res) ) 

    def update_z_slider(self,roi=None):
        """ Update the z slider if a change happens.
        
        @param object roi: optional, a pyqtgraph.ROI object of the scan which 
                           is passed if the ROI is changed.
        """ 
        if roi is None:
            self._mw.z_SliderWidget.setValue( int(( self._mw.z_current_InputWidget.value() - self._scanning_logic.z_range[0])/self.slider_res ))
        else:
            self._mw.z_SliderWidget.setValue(int( ( roi.pos()[1] + 0.5*roi.size()[1]  - self._scanning_logic.z_range[0] )/self.slider_res) ) 
            
    def change_xy_resolution(self):
        """ Update the xy resolution in the logic according to the GUI.
        """
        self._scanning_logic.xy_resolution = self._mw.xy_res_InputWidget.value()

    def change_z_resolution(self):
        """ Update the z resolution in the logic according to the GUI.
        """        
        self._scanning_logic.z_resolution = self._mw.z_res_InputWidget.value()

    def change_x_image_range(self):
        """ Adjust the image range for x in the logic.
        """
        self._scanning_logic.image_x_range = [self._mw.x_min_InputWidget.value(), 
                                              self._mw.x_max_InputWidget.value()]

    def change_y_image_range(self):
        """ Adjust the image range for y in the logic.
        """
        self._scanning_logic.image_y_range = [self._mw.y_min_InputWidget.value(), 
                                              self._mw.y_max_InputWidget.value()]

    def change_z_image_range(self):
        """ Adjust the image range for z in the logic. """
        self._scanning_logic.image_z_range = [self._mw.z_min_InputWidget.value(), 
                                              self._mw.z_max_InputWidget.value()]

    def shortcut_to_xy_cb_manual(self):
        self._mw.xy_cb_manual_RadioButton.setChecked(True)
        self.update_xy_cb_range()

    def shortcut_to_xy_cb_centiles(self):
        self._mw.xy_cb_centiles_RadioButton.setChecked(True)
        self.update_xy_cb_range()
    
    def shortcut_to_depth_cb_manual(self):
        
        # Change cb mode
        self._mw.depth_cb_manual_RadioButton.setChecked(True)
        self.update_depth_cb_range()

    def shortcut_to_depth_cb_centiles(self):
        # Change cb mode
        self._mw.depth_cb_centiles_RadioButton.setChecked(True)
        self.update_depth_cb_range()
    
    def update_xy_cb_range(self):
        self.refresh_xy_colorbar()
        self.refresh_xy_image()

    def toggle_depth_cb_mode(self):

        self.update_depth_cb_range()


    def update_depth_cb_range(self):
        self.refresh_depth_colorbar()
        self.refresh_depth_image()
        
        
        
    def refresh_xy_image(self):
        """ Update the current XY image from the logic. 

        Everytime the scanner is scanning a line in xy the 
        image is rebuild and updated in the GUI.        
        """
          
        self.xy_image.getViewBox().updateAutoRange()
        self.adjust_aspect_roi_xy()

        xy_image_data = self._scanning_logic.xy_image[:,:,3].transpose()
        
        # If "Centiles" is checked, adjust colour scaling automatically to centiles.
        # Otherwise, take user-defined values.
        if self._mw.xy_cb_centiles_RadioButton.isChecked():
            low_centile = self._mw.xy_cb_low_centile_InputWidget.value()
            high_centile = self._mw.xy_cb_high_centile_InputWidget.value() 

            cb_min = np.percentile( xy_image_data, low_centile ) 
            cb_max = np.percentile( xy_image_data, high_centile ) 

        else:
            cb_min = self._mw.xy_cb_min_InputWidget.value()
            cb_max = self._mw.xy_cb_max_InputWidget.value()

        # Now update image with new color scale, and update colorbar
        self.xy_image.setImage(image=xy_image_data, levels=(cb_min, cb_max) )
        self.refresh_xy_colorbar()

        # Unlock state widget if scan is finished
        if self._scanning_logic.getState() != 'locked':
            self._mw.ready_StateWidget.click()

    def refresh_depth_image(self):
        """ Update the current Depth image from the logic. 

        Everytime the scanner is scanning a line in depth the 
        image is rebuild and updated in the GUI.        
        """
    
        self.depth_image.getViewBox().enableAutoRange()
        self.adjust_aspect_roi_depth()

        depth_image_data = self._scanning_logic.depth_image[:,:,3].transpose()
        
        # If "Centiles" is checked, adjust colour scaling automatically to centiles.
        # Otherwise, take user-defined values.
        if self._mw.depth_cb_centiles_RadioButton.isChecked():
            low_centile = self._mw.depth_cb_low_centile_InputWidget.value()
            high_centile = self._mw.depth_cb_high_centile_InputWidget.value() 

            cb_min = np.percentile( depth_image_data, low_centile ) 
            cb_max = np.percentile( depth_image_data, high_centile ) 

        else:
            cb_min = self._mw.depth_cb_min_InputWidget.value()
            cb_max = self._mw.depth_cb_max_InputWidget.value()

        # Now update image with new color scale, and update colorbar
        self.depth_image.setImage(image=depth_image_data, levels=(cb_min, cb_max) )
        self.refresh_depth_colorbar()

        # Unlock state widget if scan is finished
        if self._scanning_logic.getState() != 'locked':
            self._mw.ready_StateWidget.click()
            
    def refresh_refocus_image(self):
        """Refreshes the xy image, the crosshair and the colorbar. """
        self.xy_refocus_image.setImage(image=self._optimiser_logic.xy_refocus_image[:,:,3].transpose())
        self.xy_refocus_image.setRect(QtCore.QRectF(self._optimiser_logic._trackpoint_x - 0.5 * self._optimiser_logic.refocus_XY_size , self._optimiser_logic._trackpoint_y - 0.5 * self._optimiser_logic.refocus_XY_size , self._optimiser_logic.refocus_XY_size, self._optimiser_logic.refocus_XY_size))               
        self.vLine.setValue(self._optimiser_logic.refocus_x)
        self.hLine.setValue(self._optimiser_logic.refocus_y)
        self.depth_refocus_image.setData(self._optimiser_logic._zimage_Z_values,self._optimiser_logic.z_refocus_line)
        self.depth_refocus_fit_image.setData(self._optimiser_logic._fit_zimage_Z_values,self._optimiser_logic.z_fit_data)
#        self.refresh_xy_colorbar()
        self._mw.refocus_position_label.setText('({0:.3f}, {1:.3f}, {2:.3f})'.format(self._optimiser_logic.refocus_x, self._optimiser_logic.refocus_y, self._optimiser_logic.refocus_z))
        
        
    def adjust_xy_window(self):
        """ Fit the visible window in the xy scan to full view.
        
        Be careful in using that method, since it uses the input values for
        the ranges to adjust x and y. Make sure that in the process of the depth scan
        no method is calling adjust_depth_window, otherwise it will adjust for you
        a window which does not correspond to the scan! 
        """
        # It is extremly crucial that before adjusting the window view and 
        # limits, to make an update of the current image. Otherwise the
        # adjustment will just be made for the previous image.
        self.refresh_xy_image()
         
        xy_viewbox = self.xy_image.getViewBox()      
        
        xMin = self._scanning_logic.image_x_range[0]
        xMax = self._scanning_logic.image_x_range[1]
        yMin = self._scanning_logic.image_y_range[0]
        yMax = self._scanning_logic.image_y_range[1]
        
        if self.fixed_aspect_ratio_xy:
            # Reset the limit settings so that the method 'setAspectLocked'
            # works properly. It has to be done in a manual way since no method
            # exists yet to reset the set limits:
            xy_viewbox.state['limits']['xLimits'] = [None, None]
            xy_viewbox.state['limits']['yLimits'] = [None, None]
            xy_viewbox.state['limits']['xRange']  = [None, None]
            xy_viewbox.state['limits']['yRange']  = [None, None]
            
            xy_viewbox.setAspectLocked(lock=True, ratio = 1.0)
            xy_viewbox.updateViewRange()
            
        else:
            xy_viewbox.setLimits(xMin = xMin - (xMax-xMin)*self.image_x_padding,
                                 xMax = xMax + (xMax-xMin)*self.image_x_padding, 
                                 yMin = yMin - (yMax-yMin)*self.image_y_padding,
                                 yMax = yMax + (yMax-yMin)*self.image_y_padding)                                                 
                                                
        self.xy_image.setRect(QtCore.QRectF(xMin, yMin, xMax - xMin, yMax - yMin))
        
        self.put_cursor_in_xy_scan()
        self.adjust_aspect_roi_xy()
        
        xy_viewbox.updateAutoRange()
        xy_viewbox.updateViewRange()
        
    def adjust_depth_window(self):
        """ Fit the visible window in the depth scan to full view.
        
        Be careful in using that method, since it uses the input values for
        the ranges to adjust x and z. Make sure that in the process of the depth scan
        no method is calling adjust_xy_window, otherwise it will adjust for you
        a window which does not correspond to the scan! 
        """
        # It is extremly crutial that before adjusting the window view and 
        # limits, to make an update of the current image. Otherwise the
        # adjustment will just be made for the previous image.
        self.refresh_depth_image()
         
        depth_viewbox = self.depth_image.getViewBox()      
        
        xMin = self._scanning_logic.image_x_range[0]
        xMax = self._scanning_logic.image_x_range[1]
        zMin = self._scanning_logic.image_z_range[0]
        zMax = self._scanning_logic.image_z_range[1]        


        if self.fixed_aspect_ratio_depth:
            # Reset the limit settings so that the method 'setAspectLocked'
            # works properly. It has to be done in a manual way since no method
            # exists yet to reset the set limits:
            depth_viewbox.state['limits']['xLimits'] = [None, None]
            depth_viewbox.state['limits']['yLimits'] = [None, None]
            depth_viewbox.state['limits']['xRange']  = [None, None]
            depth_viewbox.state['limits']['yRange']  = [None, None]
            
            depth_viewbox.setAspectLocked(lock=True, ratio = 1.0)
            depth_viewbox.updateViewRange()
            
        else:
            depth_viewbox.setLimits(xMin = xMin - xMin*self.image_x_padding,
                                 xMax = xMax + xMax*self.image_x_padding, 
                                 yMin = zMin - zMin*self.image_z_padding,
                                 yMax = zMax + zMax*self.image_z_padding)         
        
        self.depth_image.setRect(QtCore.QRectF(xMin, zMin, xMax - xMin, zMax - zMin))
        
        self.put_cursor_in_depth_scan()
        self.adjust_aspect_roi_depth() 
        
        depth_viewbox.updateAutoRange()
        depth_viewbox.updateViewRange()

    def put_cursor_in_xy_scan(self):
        """Put the xy crosshair back if it is outside of the visible range. """
        
        view_x_min = self._scanning_logic.image_x_range[0]
        view_x_max = self._scanning_logic.image_x_range[1]
        view_y_min = self._scanning_logic.image_y_range[0]
        view_y_max = self._scanning_logic.image_y_range[1]
        
        x_value = self.roi_xy.pos()[0]
        y_value = self.roi_xy.pos()[1]
        cross_pos = self.roi_xy.pos()+ self.roi_xy.size()*0.5
        
        if (view_x_min > cross_pos[0]):
            x_value = view_x_min+self.roi_xy.size()[0]
            
        if (view_x_max < cross_pos[0]):
            x_value = view_x_max-self.roi_xy.size()[0]
            
        if (view_y_min > cross_pos[1]):
            y_value = view_y_min+self.roi_xy.size()[1]
            
        if (view_y_max < cross_pos[1]):
            y_value = view_y_max-self.roi_xy.size()[1]
         
        self.roi_xy.setPos([x_value,y_value], update=True)
            
    def put_cursor_in_depth_scan(self):
        """Put the depth crosshair back if it is outside of the visible range. """
        
        view_x_min = self._scanning_logic.image_x_range[0]
        view_x_max = self._scanning_logic.image_x_range[1]
        view_z_min = self._scanning_logic.image_z_range[0]
        view_z_max = self._scanning_logic.image_z_range[1]
        
        x_value = self.roi_depth.pos()[0]
        z_value = self.roi_depth.pos()[1]
        cross_pos = self.roi_depth.pos()+ self.roi_depth.size()*0.5
        
        if (view_x_min > cross_pos[0]):
            x_value = view_x_min+self.roi_depth.size()[0]
            
        if (view_x_max < cross_pos[0]):
            x_value = view_x_max-self.roi_depth.size()[0]
            
        if (view_z_min > cross_pos[1]):
            z_value = view_z_min+self.roi_depth.size()[1]
            
        if (view_z_max < cross_pos[1]):
            z_value = view_z_max-self.roi_depth.size()[1]
            
        self.roi_depth.setPos([x_value,z_value], update=True)

      
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
        
#        if self.fixed_aspect_ratio_xy:
#            if new_size_x_roi > new_size_y_roi:
#                new_size_y_roi = new_size_x_roi
#            else:
#                new_size_x_roi = new_size_y_roi
        old_size_x_roi = self.roi_xy.size()[0] 
        old_size_y_roi = self.roi_xy.size()[1]

        diff_size_x_roi = (old_size_x_roi - new_size_x_roi)*0.5
        diff_size_y_roi = (old_size_y_roi - new_size_y_roi)*0.5
        
        # Here it is really necessary not to update, otherwise you will
        # calculate the position of the roi in a wrong way.
        self.roi_xy.setSize([new_size_x_roi,new_size_y_roi], update=False)
        pos = self.roi_xy.pos()
        self.roi_xy.setPos([pos[0]+diff_size_x_roi,pos[1]+diff_size_y_roi], update=True)

    
    def adjust_aspect_roi_depth(self,viewbox=None):
        """ Keep the aspect ratio of the ROI also during the zoom the same. 
        
        @param object viewbox: pyqtgraph.ViewBox object, which contains the 
                               view information about the display.
        
        """
        viewbox = self.depth_image.getViewBox()
        current_x_view_range = viewbox.viewRange()[0][1] - viewbox.viewRange()[0][0]
        current_z_view_range = viewbox.viewRange()[1][1] - viewbox.viewRange()[1][0]
        
        new_size_x_roi = current_x_view_range/20
        new_size_z_roi = current_z_view_range/20
        
        if self.fixed_aspect_ratio_depth:
            if new_size_x_roi > new_size_z_roi:
                new_size_z_roi = new_size_x_roi
            else:
                new_size_x_roi = new_size_z_roi
        
        old_size_x_roi = self.roi_depth.size()[0] 
        old_size_z_roi = self.roi_depth.size()[1]

        diff_size_x_roi = (old_size_x_roi - new_size_x_roi)*0.5
        diff_size_z_roi = (old_size_z_roi - new_size_z_roi)*0.5
        
        # Here it is really necessary not to update, otherwise you will
        # calculate the position of the roi in a wrong way.
        self.roi_depth.setSize([new_size_x_roi,new_size_z_roi], update=False)
        pos = self.roi_depth.pos()
        self.roi_depth.setPos([pos[0]+diff_size_x_roi,pos[1]+diff_size_z_roi], update=True)

    def save_xy_scan_data(self):
        """ Run the save routine from the logic to save the xy confocal pic."""
        self._scanning_logic.save_xy_data()
        
    def save_xy_scan_image(self):
        """ Save the image and according to that the data. """
        
        filepath = self._save_logic.get_path_for_module(module_name='Confocal')        
        filename = filepath + time.strftime('\\%Y-%m-%d_%Hh%Mm%Ss_confocal_xy_image') 
        
        self._mw.xy_ViewWidget.plotItem.removeItem(self.roi_xy)
        self._mw.xy_ViewWidget.plotItem.removeItem(self.hline_xy)
        self._mw.xy_ViewWidget.plotItem.removeItem(self.vline_xy)
        
#        self._mw.xy_cb_ViewWidget.removeItem(self.xy_cb)
#        self._mw.xy_ViewWidget.addItem(self.xy_cb) 
#        
#        
#        cb_min = self._mw.xy_cb_min_InputWidget.value()
#        cb_max = self._mw.xy_cb_max_InputWidget.value()
#        
#        curr_x_min = self._scanning_logic.image_x_range[0]
#        curr_x_max = self._scanning_logic.image_x_range[1]
#        curr_y_min = self._scanning_logic.image_y_range[0]
#        curr_y_max = self._scanning_logic.image_y_range[1]
#        # 2% of the image width should be the width of the colorbar:
#        width_cb = (curr_x_max - curr_x_min)*0.02
#        x_min_cb = (curr_x_max -curr_x_min)*0.02 + curr_x_max
#        
#        self.xy_cb.refresh_colorbar(cb_min,cb_max,width = width_cb , height=curr_y_max-curr_y_min , xMin=x_min_cb ,yMin= curr_y_min)
        exporter = pg.exporters.SVGExporter(self._mw.xy_ViewWidget.plotItem)
        exporter.export(filename+'.svg')    
        
        if self._sd.savePNG_checkBox.isChecked():
            exporter = pg.exporters.ImageExporter(self._mw.xy_ViewWidget.plotItem)
            exporter.export(filename+'.png')
            
        if self._sd.save_purePNG_checkBox.isChecked():
            self.xy_image.save(filename+'_raw.png') 
        
#        self._mw.xy_ViewWidget.removeItem(self.xy_cb)
#        self._mw.xy_cb_ViewWidget.addItem(self.xy_cb)
#        self.refresh_xy_colorbar() 
        self._mw.xy_ViewWidget.plotItem.addItem(self.roi_xy)
        self._mw.xy_ViewWidget.plotItem.addItem(self.hline_xy)
        self._mw.xy_ViewWidget.plotItem.addItem(self.vline_xy)
        
        self.save_xy_scan_data()
        
    def save_depth_scan_data(self):
        """ Run the save routine from the logic to save the xy confocal pic."""      
        self._scanning_logic.save_depth_data()
            
    def save_depth_scan_image(self):
        """ Save the image and according to that the data. """
        
        filepath = self._save_logic.get_path_for_module(module_name='Confocal')        
        filename = filepath + time.strftime('\\%Y-%m-%d_%Hh%Mm%Ss_confocal_depth_image') 

        self._mw.depth_ViewWidget.plotItem.removeItem(self.roi_depth)
        self._mw.depth_ViewWidget.plotItem.removeItem(self.hline_depth)
        self._mw.depth_ViewWidget.plotItem.removeItem(self.vline_depth)

        exporter = pg.exporters.SVGExporter(self._mw.depth_ViewWidget.plotItem)
        exporter.export(filename+'.svg')
        
        if self._sd.savePNG_checkBox.isChecked():
            exporter = pg.exporters.ImageExporter(self._mw.depth_ViewWidget.plotItem)
            exporter.export(filename+'.png')
        
        if self._sd.save_purePNG_checkBox.isChecked():
            self.depth_image.save(filename+'_raw.png') 
        
        self._mw.depth_ViewWidget.plotItem.addItem(self.roi_depth)
        self._mw.depth_ViewWidget.plotItem.addItem(self.hline_depth)
        self._mw.depth_ViewWidget.plotItem.addItem(self.vline_depth)
        
        self.save_depth_scan_data()
        
    def switch_hardware(self):
        """ Switches the hardware state. """
#        if self._hardware_state:
#            self._hardware_state=False
#            self._sd.hardware_switch.setText('Switch on Hardware')
        self._scanning_logic.switch_hardware(to_on=False)
#        else:
#            self._hardware_state=True
#            self._sd.hardware_switch.setText('Switch off Hardware')
#            self._scanning_logic.switch_hardware(to_on=True)
