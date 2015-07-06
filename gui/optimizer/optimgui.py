# -*- coding: utf-8 -*-
"""
Created on Mon Apr 27 17:54:58 2015

@author: user-admin  FIXME this should be a more meaningful name.
"""

from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph as pg
import numpy as np

from collections import OrderedDict
from gui.guibase import GUIBase
from gui.optimizer.ui_optimgui import Ui_MainWindow
from gui.optimizer.ui_optim_settings import Ui_SettingsDialog
from gui.guiutils import ColorBar


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


class OptimizerMainWindow(QtGui.QMainWindow,Ui_MainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.setupUi(self)

class OptimizerSettingDialog(QtGui.QDialog,Ui_SettingsDialog):
    def __init__(self):
        QtGui.QDialog.__init__(self)
        self.setupUi(self)


class OptimizerGui(GUIBase):
    """
    This is the GUI Class for Optimizer
    """
    _modclass = 'OptimizerGui'
    _modtype = 'gui'

    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        c_dict = {'onactivate': self.initUI}
        super().__init__(
                    manager,
                    name,
                    config,
                    c_dict)

        ## declare connectors
        self.connector['in']['optimizerlogic1'] = OrderedDict()
        self.connector['in']['optimizerlogic1']['class'] = 'OptimizerLogic'
        self.connector['in']['optimizerlogic1']['object'] = None

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

        self._optimizer_logic = self.connector['in']['optimizerlogic1']['object']
#        print("Optimizer logic is", self._optimizer_logic)

#        self._save_logic = self.connector['in']['savelogic']['object']
#        print("Save logic is", self._save_logic)

        # Use the inherited class 'Ui_OptimizerGuiTemplate' to create now the
        # GUI element:
        self._mw = OptimizerMainWindow()
        self._sw = OptimizerSettingDialog()

        # Get the image for the display from the logic:
        arr01 = self._optimizer_logic.xy_refocus_image[:,:,3].transpose()
        arr02 = self._optimizer_logic.z_refocus_line


        # Load the image in the display:
        self.xy_refocus_image = pg.ImageItem(arr01)
        self.xy_refocus_image.setRect(
            QtCore.QRectF(
                self._optimizer_logic._trackpoint_x - 0.5 * self._optimizer_logic.refocus_XY_size,
                self._optimizer_logic._trackpoint_y - 0.5 * self._optimizer_logic.refocus_XY_size,
                self._optimizer_logic.refocus_XY_size, self._optimizer_logic.refocus_XY_size
            ))
        self.xz_refocus_image = pg.ScatterPlotItem(self._optimizer_logic._zimage_Z_values,
                                                arr02,
                                                symbol='o')
        self.xz_refocus_fit_image = pg.PlotDataItem(self._optimizer_logic._fit_zimage_Z_values,
                                                    self._optimizer_logic.z_fit_data,
                                                    pen=QtGui.QPen(QtGui.QColor(255,0,255,255)))

        # Add the display item to the xy and xz VieWidget defined in
        # the UI file.
        self._mw.xy_refocus_ViewWidget.addItem(self.xy_refocus_image)
        self._mw.xz_refocus_ViewWidget.addItem(self.xz_refocus_image)
        self._mw.xz_refocus_ViewWidget.addItem(self.xz_refocus_fit_image)

        # Add labels and set aspect ratio
        self._mw.xy_refocus_ViewWidget.setLabel( 'bottom', 'X position', units='µm' )
        self._mw.xy_refocus_ViewWidget.setLabel( 'left', 'Y position', units='µm' )
        self._mw.xy_refocus_ViewWidget.setAspectLocked( lock=True, ratio=1.0 )

        self._mw.xz_refocus_ViewWidget.setLabel('bottom', 'Z position', units='µm')
        self._mw.xz_refocus_ViewWidget.setLabel('left', 'Fluorescence', units='c/s')

        #Add crosshair to the xy refocus scan
        self.vLine = pg.InfiniteLine(pen=QtGui.QPen(QtGui.QColor(255,0,255,255), 0.02), pos=50, angle=90, movable=False)
        self.hLine = pg.InfiniteLine(pen=QtGui.QPen(QtGui.QColor(255,0,255,255), 0.02), pos=50, angle=0, movable=False)
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
        self.xy_cb = ColorBar(self.colmap_norm, 100, 0, 100000)

        self._mw.xy_refocus_cb_ViewWidget.addItem(self.xy_cb)
        self._mw.xy_refocus_cb_ViewWidget.hideAxis('bottom')
        self._mw.xy_refocus_cb_ViewWidget.hideAxis('left')
        self._mw.xy_refocus_cb_ViewWidget.setLabel('right', 'Fluorescence', units='c/s')

        # Connect to default values:
        self.reject_settings()

        # Connect signals
        self._optimizer_logic.signal_image_updated.connect(self.refresh_image)
        self._optimizer_logic.signal_refocus_finished.connect(self.enable_button)
        self._optimizer_logic.signal_refocus_started.connect(self.disable_button)
        self._mw.action_Settings.triggered.connect(self.menue_settings)
        self._mw.optimiseButton.clicked.connect(self.refocus_clicked)
        self._sw.accepted.connect(self.update_settings)
        self._sw.rejected.connect(self.reject_settings)
        self._sw.buttonBox.button(QtGui.QDialogButtonBox.Apply).clicked.connect(self.update_settings)

#        print('Main Optimizer Windows shown:')
        self._mw.show()

    def show(self):
        """Make window visible and put it above all other windows."""

        QtGui.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

    def update_settings(self):
        """ Write the new settings from the gui to the file."""

        self._optimizer_logic.refocus_XY_size = self._sw.xy_refocusrange_DoubleSpinBox.value()
        self._optimizer_logic.refocus_XY_step = self._sw.xy_refocusstepsize_DoubleSpinBox.value()
        self._optimizer_logic.refocus_Z_size = self._sw.z_refocusrange_DoubleSpinBox.value()
        self._optimizer_logic.refocus_Z_step = self._sw.z_refocusstepsize_DoubleSpinBox.value()
        self._optimizer_logic.set_clock_frequency(self._sw.count_freq_SpinBox.value())
        self._optimizer_logic.return_slowness = self._sw.return_slow_SpinBox.value()

    def reject_settings(self):
        """ Keep the old settings and restores the old settings in the gui. """

        self._sw.xy_refocusrange_DoubleSpinBox.setValue(self._optimizer_logic.refocus_XY_size)
        self._sw.xy_refocusstepsize_DoubleSpinBox.setValue(self._optimizer_logic.refocus_XY_step)
        self._sw.z_refocusrange_DoubleSpinBox.setValue(self._optimizer_logic.refocus_Z_size)
        self._sw.z_refocusstepsize_DoubleSpinBox.setValue(self._optimizer_logic.refocus_Z_step)
        self._sw.count_freq_SpinBox.setValue(self._optimizer_logic._clock_frequency)
        self._sw.return_slow_SpinBox.setValue(self._optimizer_logic.return_slowness)

    def refresh_xy_colorbar(self):
        """ Deletes the old colorbar and replace it with an updated one. """

        self._mw.xy_refocus_cb_ViewWidget.clear()
        self.xy_cb = ColorBar(self.colmap_norm, 100, self.xy_refocus_image.image.min(), self.xy_refocus_image.image.max())
        self._mw.xy_refocus_cb_ViewWidget.addItem(self.xy_cb)

    def menue_settings(self):
        """ This method opens the settings menue."""
        self._sw.exec_()


    def refresh_image(self):
        """ Refresh the xy image, the crosshair and the colorbar."""

        self.xy_refocus_image.setImage(image=self._optimizer_logic.xy_refocus_image[:,:,3].transpose())
        self.xy_refocus_image.setRect(
            QtCore.QRectF(
                self._optimizer_logic._trackpoint_x - 0.5 * self._optimizer_logic.refocus_XY_size,
                self._optimizer_logic._trackpoint_y - 0.5 * self._optimizer_logic.refocus_XY_size,
                self._optimizer_logic.refocus_XY_size, self._optimizer_logic.refocus_XY_size
            ))
        self.vLine.setValue(self._optimizer_logic.refocus_x)
        self.hLine.setValue(self._optimizer_logic.refocus_y)
        self.xz_refocus_image.setData(self._optimizer_logic._zimage_Z_values,self._optimizer_logic.z_refocus_line)
        self.xz_refocus_fit_image.setData(self._optimizer_logic._fit_zimage_Z_values,self._optimizer_logic.z_fit_data)
        self.refresh_xy_colorbar()
        self._mw.optimal_coordinates.setText('({0:.3f}, {1:.3f}, {2:.3f})'.format(self._optimizer_logic.refocus_x, self._optimizer_logic.refocus_y, self._optimizer_logic.refocus_z))

    def refocus_clicked(self):
        """ Manages what happens if the optimizer is started."""
        self._optimizer_logic.start_refocus()
        self.disable_button()

    def disable_button(self):
        self._mw.optimiseButton.setEnabled(False)

    def enable_button(self):
        self._mw.optimiseButton.setEnabled(True)
