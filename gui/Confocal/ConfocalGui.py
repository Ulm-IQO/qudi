# -*- coding: utf-8 -*-



#from PyQt4 import QtCore, QtGui
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph as pg
import numpy as np

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




class ColorBar(pg.GraphicsObject):
 
    def __init__(self, cmap, width, height, ticks=None, tick_labels=None, label=None):
        pg.GraphicsObject.__init__(self)
 
        # handle args
        label = label or ''
        w, h = width, height
        stops, colors = cmap.getStops('float')
        smn, spp = stops.min(), stops.ptp()
        stops = (stops - stops.min())/stops.ptp()
        if ticks is None:
            ticks = np.r_[0.0:1.0:5j, 1.0] * spp + smn
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
        # paint underlying mask
        p.setPen(pg.QtGui.QColor(0, 0, 0, 255))
        p.setBrush(pg.QtGui.QColor(0, 0, 0, 200))
        p.drawRoundedRect(*(self.zone + (9.0, 9.0)))
        
        # paint colorbar
        p.drawPicture(0, 0, self.pic)
        
    def boundingRect(self):
        return pg.QtCore.QRectF(self.pic.boundingRect())



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
    
          @param object extroi: external roi
        """
        if self.angle == 0:
            self.setValue(extroi.pos()[1] + extroi.size()[1] * 0.5 )
        if self.angle == 90:
            self.setValue(extroi.pos()[0] + extroi.size()[0] * 0.5 )



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
        
        self.connector['in']['trackerlogic1'] = OrderedDict()
        self.connector['in']['trackerlogic1']['class'] = 'TrackerLogic'
        self.connector['in']['trackerlogic1']['object'] = None

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
        
        self._tracker_logic = self.connector['in']['trackerlogic1']['object']
        print("Tracking logic is", self._tracker_logic)
        
        # Use the inherited class 'Ui_ConfocalGuiTemplate' to create now the 
        # GUI element:
        self._mw = ConfocalMainWindow()
        
        # Get the image for the display from the logic: 
        arr01 = self._scanning_logic.xy_image[:,:,3].transpose()
        arr02 = self._scanning_logic.xz_image[:,:,3].transpose()

        # Set initial position for the crosshair, default is the middle of the
        # screen:
        ini_pos_x_crosshair = len(arr01)/2
        ini_pos_y_crosshair = len(arr01)/2
        ini_pos_z_crosshair = len(arr02)/2
        
        # Load the image in the display:
        self.xy_image = pg.ImageItem(arr01)
        self.xy_image.setRect(QtCore.QRectF(0, 0, 100, 100))
        self.xz_image = pg.ImageItem(arr02)
        self.xz_image.setRect(QtCore.QRectF(0, 0, 100, 100))


        # Add the display item to the xy and xz VieWidget, which was defined in
        # the UI file.
        self._mw.xy_ViewWidget.addItem(self.xy_image)
        self._mw.xz_ViewWidget.addItem(self.xz_image)
        
    
        
        # Create Region of Interest for xy image:
        self.roi_xy = CrossROI([ini_pos_x_crosshair, ini_pos_y_crosshair], [len(arr01), len(arr01)], pen={'color': "00F", 'width': 1},removable=True )
        # self.roi_xy = CrossROI([100, 100], [10, 10], pen={'color': "00F", 'width': 1},removable=True )
        
        # Add to the xy Image Widget
        self._mw.xy_ViewWidget.addItem(self.roi_xy)
        
        # create horizontal and vertical line in xy image
        self.hline_xy = CrossLine(pos=self.roi_xy.pos()+self.roi_xy.size()*0.5, angle= 0, pen={'color': "00F", 'width': 1} )
        self.vline_xy = CrossLine(pos=self.roi_xy.pos()+self.roi_xy.size()*0.5, angle=90, pen={'color': "00F", 'width': 1} )

        # connect the change of a region with the adjustment of the crosshair:
        self.roi_xy.sigRegionChanged.connect(self.hline_xy.adjust)
        self.roi_xy.sigRegionChanged.connect(self.vline_xy.adjust)
        

        self.roi_xy.sigRegionChanged.connect(self.slider_x_adjust)
        self.roi_xy.sigRegionChanged.connect(self.slider_y_adjust)


        # add the configured crosshair to the xy Widget
        self._mw.xy_ViewWidget.addItem(self.hline_xy)
        self._mw.xy_ViewWidget.addItem(self.vline_xy)
        
        # Some additional settings for the xy ViewWidget
        self._mw.xy_ViewWidget.setMouseEnabled(x=False,y=False)
        self._mw.xy_ViewWidget.enableAutoRange()
#        self._mw.xy_ViewWidget.setAspectLocked(lock=True, ratio=1) 

        # create Region of Interest for xz image:
        self.roi_xz = CrossROI([ini_pos_x_crosshair, ini_pos_z_crosshair], [len(arr02)/10, len(arr02)/10], pen={'color': "00F", 'width': 1},removable=True )

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
        #self._mw.xz_ViewWidget.disableAutoRange()
        #self._mw.xz_ViewWidget.setAspectLocked(lock=True, ratio=1)        
        
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
        
        # Connect the Slider with an update in the current values of x,y and z.
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
        
        # Declare for which fields changes are applied if the cursor is leaving
        # the field:

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
        
        
        
        
        # Connect the RadioButtons and connect to the event if they are touched:
        
        self._mw.ready_StateWidget.toggled.connect(self.ready_clicked)
        self._mw.xy_scan_StateWidget.toggled.connect(self.xy_scan_clicked)
        self._mw.xz_scan_StateWidget.toggled.connect(self.xz_scan_clicked)
        self._mw.refocus_StateWidget.toggled.connect(self.refocus_clicked)


        self._scanning_logic.signal_image_updated.connect(self.refresh_image)
        self._scanning_logic.signal_change_position.connect(self.update_gui)
        self._tracker_logic.signal_refocus_finished.connect(self._mw.ready_StateWidget.click)
        #self._scanning_logic.signal_scan_lines_next.connect(self.refresh_image)
        print('Main Confocal Windows shown:')
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
        color = np.array([[127,  0,  0,255], [255, 26,  0,255], [255,129,  0,255],
                          [254,237,  0,255], [160,255, 86,255], [ 66,255,149,255],
                          [  0,204,255,255], [  0, 88,255,255], [  0,  0,241,255],
                          [  0,  0,132,255]], dtype=np.ubyte)
                          
        colmap = pg.ColorMap(pos, color)
        
        self.colmap_norm = pg.ColorMap(pos, color/255)
        
        # get the LookUpTable (LUT), first two params should match the position
        # scale extremes passed to ColorMap(). 
        # I believe last one just has to be >= the difference between the min and max level set later
        lut = colmap.getLookupTable(0, 1, 10)

            
        self.xy_image.setLookupTable(lut)
        self.xz_image.setLookupTable(lut)        
        
        # Play around with a color bar:
        
        self.xy_cb = ColorBar(self.colmap_norm, 10, self.xy_image.image.max(), label='Counts')#Foo (Hz)')#, [0., 0.5, 1.0])        
        self.xz_cb = ColorBar(self.colmap_norm, 10, self.xz_image.image.max(), label='Counts')#Foo (Hz)')#, [0., 0.5, 1.0])              
        
        self._mw.xy_cb_ViewWidget.addItem(self.xy_cb)
        self._mw.xz_cb_ViewWidget.addItem(self.xz_cb)
        self._mw.xy_cb_ViewWidget.hideAxis('bottom')
        self._mw.xz_cb_ViewWidget.hideAxis('bottom')
        
    def update_gui(self):
        
        x_pos = self._scanning_logic._current_x
        y_pos = self._scanning_logic._current_y
        z_pos = self._scanning_logic._current_z
        
        roi_x_view = x_pos - self.roi_xy.size()[0]*0.5
        roi_y_view = y_pos - self.roi_xy.size()[1]*0.5
        self.roi_xy.setPos([roi_x_view , roi_y_view])
        
        roi_x_view = x_pos - self.roi_xz.size()[0]*0.5
        roi_y_view = z_pos - self.roi_xz.size()[1]*0.5
        self.roi_xz.setPos([roi_x_view , roi_y_view])
        
        
    def refresh_xy_colorbar(self):
        self.xy_cb = ColorBar(self.colmap_norm, 10, self.xy_image.image.max(), label='Counts')#Foo (Hz)')#, [0., 0.5, 1.0])
        self._mw.xy_cb_ViewWidget.addItem(self.xy_cb)        

     
    def refresh_xz_colorbar(self):
        self.xz_cb = ColorBar(self.colmap_norm, 10, self.xz_image.image.max(), label='Counts')#Foo (Hz)')#, [0., 0.5, 1.0])
        self._mw.xz_cb_ViewWidget.addItem(self.xz_cb)        
        
    def ready_clicked(self):
        pass

            
    def xy_scan_clicked(self, enabled):
        self._scanning_logic.stop_scanning()
        if enabled:
            self._scanning_logic.start_scanning()
            
    def xz_scan_clicked(self, enabled):
        self._scanning_logic.stop_scanning()
        if enabled:
            self._scanning_logic.start_scanning(zscan = True)
            

    def refocus_clicked(self, enabled):
        self._scanning_logic.stop_scanning()
        if enabled:
             self._tracker_logic.start_refocus()
   
    def roi_xy_change_x(self,x_pos):
        # Since the origin of the region of interest (ROI) is not the crosshair
        # point but the lowest left point of the square, you have to shift the
        # origin according to that. Therefore the position of the ROI is not 
        # the actual position!
    
        roi_x_view = x_pos - self.roi_xy.size()[0]*0.5
        roi_y_view = self.roi_xy.pos()[1]
        self.roi_xy.setPos([roi_x_view , roi_y_view])
        self._scanning_logic.set_position(x=x_pos)
        
    def roi_xy_change_y(self,y_pos):
        roi_x_view = self.roi_xy.pos()[0]
        roi_y_view = y_pos - self.roi_xy.size()[1]*0.5
        self.roi_xy.setPos([roi_x_view , roi_y_view])
        self._scanning_logic.set_position(y=y_pos)    

        
    def roi_xz_change_x(self,x_pos):
        
        roi_x_view = x_pos - self.roi_xz.size()[0]*0.5
        roi_y_view = self.roi_xz.pos()[1]
        self.roi_xz.setPos([roi_x_view , roi_y_view])
        self._scanning_logic.set_position(x=x_pos)        

    def roi_xz_change_z(self,z_pos):
        

        roi_x_view = self.roi_xz.pos()[0]
        roi_y_view = z_pos - self.roi_xz.size()[1]*0.5
        self.roi_xz.setPos([roi_x_view , roi_y_view])
        self._scanning_logic.set_position(z=z_pos)         
        
        
    def slider_x_adjust(self,roi):
        self._mw.x_SliderWidget.setValue(roi.pos()[0]+ 0.5*roi.size()[0]) 
        
    def slider_y_adjust(self,roi):
        self._mw.y_SliderWidget.setValue(roi.pos()[1]+ 0.5*roi.size()[1]) 

    def slider_z_adjust(self,roi):
        self._mw.z_SliderWidget.setValue(roi.pos()[1]+ 0.5*roi.size()[1]) 
        
        
    def update_current_x(self,text):
        self._mw.x_current_InputWidget.setText(str(text))
        print(self.xy_image.boundingRect())
        #print(dir(self.xy_image))boundingRegion
        
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
        
    def change_xy_resolution(self):
        self._scanning_logic.xy_resolution = float(self._mw.xy_res_InputWidget.text())
        
    def change_z_resolution(self):
        self._scanning_logic.z_resolution = float(self._mw.z_res_InputWidget.text())
    
    def change_x_image_range(self):
        self._scanning_logic.image_x_range = [float(self._mw.x_min_InputWidget.text()), float(self._mw.x_max_InputWidget.text())]
        
    def change_y_image_range(self):
        self._scanning_logic.image_y_range = [float(self._mw.y_min_InputWidget.text()), float(self._mw.y_max_InputWidget.text())]
        
    def change_z_image_range(self):
        self._scanning_logic.image_z_range = [float(self._mw.z_min_InputWidget.text()), float(self._mw.z_max_InputWidget.text())]
        
        
        
    def refresh_image(self):
        if self._mw.xy_scan_StateWidget.isChecked():
            self.xy_image.getViewBox().enableAutoRange()            
            view_x_min = float(self._mw.x_min_InputWidget.text())
            view_x_max = float(self._mw.x_max_InputWidget.text())-view_x_min
            view_y_min = float(self._mw.y_min_InputWidget.text())
            view_y_max = float(self._mw.y_max_InputWidget.text())-view_y_min   
            self.xy_image.setRect(QtCore.QRectF(view_x_min, view_y_min, view_x_max, view_y_max))
            
            self.xy_image.setImage(image=self._scanning_logic.xy_image[:,:,3].transpose(),autoLevels=True)
            self.refresh_xy_colorbar()
            
        elif self._mw.xz_scan_StateWidget.isChecked():
            self.xz_image.getViewBox().enableAutoRange()            
            view_x_min = float(self._mw.x_min_InputWidget.text())
            view_x_max = float(self._mw.x_max_InputWidget.text())-view_x_min
            view_z_min = float(self._mw.z_min_InputWidget.text())
            view_z_max = float(self._mw.z_max_InputWidget.text())-view_z_min  
            self.xz_image.setRect(QtCore.QRectF(view_x_min, view_z_min, view_x_max, view_z_max))    
            self.xz_image.setImage(image=self._scanning_logic.xz_image[:,:,3].transpose(),autoLevels=True)
            self.refresh_xz_colorbar()


        if self._scanning_logic.getState() != 'locked':
            self._mw.ready_StateWidget.click()
            self.put_cursor_in_xy_scan()
            self.put_cursor_in_xz_scan()
        
    def put_cursor_in_xy_scan(self):
        view_x_min = float(self._mw.x_min_InputWidget.text())
        view_x_max = float(self._mw.x_max_InputWidget.text())-view_x_min
        view_y_min = float(self._mw.y_min_InputWidget.text())
        view_y_max = float(self._mw.y_max_InputWidget.text())-view_y_min  
        
        cross_pos = self.roi_xy.pos()+ self.roi_xy.size()*0.5
        
        if (view_x_min > cross_pos[0]):
            self.roi_xy_change_x(view_x_min+self.roi_xy.size()[0]*0.5)
            
        if (view_x_max < cross_pos[0]):
            self.roi_xy_change_x(view_x_max-self.roi_xy.size()[0]*0.5)
            
        if (view_y_min > cross_pos[1]):
            self.roi_xy_change_y(view_y_min+self.roi_xy.size()[1]*0.5)
            
        if (view_y_max < cross_pos[1]):
            self.roi_xy_change_y(view_y_max-self.roi_xy.size()[1]*0.5)
            
            
    def put_cursor_in_xz_scan(self):
        view_x_min = float(self._mw.x_min_InputWidget.text())
        view_x_max = float(self._mw.x_max_InputWidget.text())-view_x_min
        view_z_min = float(self._mw.z_min_InputWidget.text())
        view_z_max = float(self._mw.z_max_InputWidget.text())-view_z_min  
        
        cross_pos = self.roi_xz.pos()+ self.roi_xz.size()*0.5
        
        if (view_x_min > cross_pos[0]):
            self.roi_xz_change_x(view_x_min+self.roi_xz.size()[0]*0.5)
            
        if (view_x_max < cross_pos[0]):
            self.roi_xz_change_x(view_x_max-self.roi_xz.size()[0]*0.5)
            
        if (view_z_min > cross_pos[1]):
            self.roi_xz_change_z(view_z_min+self.roi_xz.size()[1]*0.5)
            
        if (view_z_max < cross_pos[1]):
            self.roi_xz_change_z(view_z_max-self.roi_xz.size()[1]*0.5)
            
    def adjust_aspect_roi_xy():
        pass
    
    def adjust_aspect_roi_xz():
        pass
        
        