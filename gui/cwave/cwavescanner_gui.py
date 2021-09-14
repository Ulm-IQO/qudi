
import numpy as np
import os
import pyqtgraph as pg
import time

from core.connector import Connector
from gui.colordefs import QudiPalettePale as palette
from gui.guibase import GUIBase
from gui.guiutils import ColorBar
from gui.colordefs import ColorScaleInferno
from qtpy import QtGui
from qtpy import QtCore
from qtpy import QtWidgets
from qtpy import uic
def wavelength_to_freq(wavelength):
    aa = 299792458.0 * 1e9 * np.ones(wavelength.shape[0])
    freqs = np.divide(aa, wavelength, out=np.zeros_like(aa), where=wavelength!=0)
    return freqs

class ScannerWindow(QtWidgets.QMainWindow):
    """ Create the Main Window based on the *.ui file. """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'cwavescanner.ui')

        # Load it
        super(ScannerWindow, self).__init__()
        uic.loadUi(ui_file, self)
        self.show()

class CwaveScanGui(GUIBase):
    """

    """
    # declare connectors
    cwavelogic = Connector(interface='CwaveLogic')
    savelogic = Connector(interface='SaveLogic')
    
    sig_adj_thick_etalon = QtCore.Signal(int)
    sig_adj_opo = QtCore.Signal(int)
    sig_set_refcav = QtCore.Signal(float)
    
    sig_connect_cwave = QtCore.Signal()
    sig_set_shutter_state = QtCore.Signal(str, bool)
    sig_optimize_cwave = QtCore.Signal(str)
    sig_change_lock_mode = QtCore.Signal(str, str)
    sig_start_sweep = QtCore.Signal()
    sig_stop_sweep = QtCore.Signal()
    sig_set_zpl_sweep_params = QtCore.Signal(float, float, int)
    sig_update_zpl_search_params = QtCore.Signal(float, float, float)
    sig_save_measurement = QtCore.Signal()
    sig_regulation_mode = QtCore.Signal(bool)
    
    sig_refresh_sweep_zpl = QtCore.Signal()
    
    sig_refresh_zpl_search = QtCore.Signal()
    sig_reset_zpl_search = QtCore.Signal()

    def on_deactivate(self):
        """ Reverse steps of activation

        @return int: error code (0:OK, -1:error)
        """
        #turn off the regulation 
        self.regulate_wavelength(mode_manual = False)
        self._mw.close()
        return 0
    def on_activate(self):
        """ 

        """
        self._cwavescan_logic = self.cwavelogic()
        self._savelogic = self.savelogic()

        self._mw = ScannerWindow()     
        #! Get the images from the logic
        self.set_up_images()
        self.set_up_cwave_control_panel()
        self.set_up_scanner_panel()
        
        #turn off the regulation 
        self.regulate_wavelength(mode_manual = False)

        self._mw.refresh_pushButton.clicked.connect(self.refresh_wlm)
        self._cwavescan_logic.sig_update_gui.connect(self.update_gui)

        #! set initial values
        # self._mw.wl1DoubleSpinBox.setValue(self._cwavescan_logic.scan_range[0])
        # self._mw.wl2DoubleSpinBox.setValue(self._cwavescan_logic.scan_range[1])
  
        self._mw.show()
    def set_up_images(self):
        self.search_image = None
        self.scan_image = pg.PlotDataItem(self._cwavescan_logic.plot_x,
        self._cwavescan_logic.plot_y,symbol='o', symbolSize=2, pen={'color': 0.6, 'width': 1})
        self._mw.scan_ViewWidget.addItem(self.scan_image)
        self._mw.scan_ViewWidget.showGrid(x=True, y=True, alpha=0.8)
                # Plot labels.
        self._pw = self._mw.scan_ViewWidget
        self._pw.setLabel('left', 'Fluorescence', units='counts/s')
        self._pw.setLabel('bottom', 'wavelength', units='nm')

        self.scan_matrix_image = pg.ImageItem(self._cwavescan_logic.scan_matrix,axisOrder='row-major')
        self.scan_matrix_image.setRect(QtCore.QRectF(10, 0,10,10))
        
        self.wavemeter_image = pg.PlotDataItem(self._cwavescan_logic.plot_y_wlm,
        self._cwavescan_logic.plot_x_wlm,
        pen="w", symbol=None)
        self._mw.wavelength_ViewWidget.addItem(self.wavemeter_image)
        
        self.shgPD_image = pg.PlotDataItem(self._cwavescan_logic.plot_x_shg_pd,self._cwavescan_logic.plot_y_shg_pd)
        self.opoPD_image = pg.PlotDataItem(self._cwavescan_logic.plot_x_opo_pd,self._cwavescan_logic.plot_y_opo_pd)
        self.scan_fit_image = pg.PlotDataItem(self._cwavescan_logic.fit_x,self._cwavescan_logic.fit_y,pen=QtGui.QPen(QtGui.QColor(255, 255, 255, 255)))
        # Add the display item to the xy and xz VieWidget, which was defined in
        # the UI file.
        
        
        self._plot_item = self._mw.wavelength_ViewWidget.plotItem
        ## create a new ViewBox, link the right axis to its coordinate system
        self._top_axis = pg.ViewBox()
        self._plot_item.showAxis('top')
        self._plot_item.scene().addItem(self._top_axis)
        self._plot_item.getAxis('top').linkToView(self._top_axis)
        self._top_axis.setYLink(self._plot_item)
        self._top_axis.invertX(b=True)
        self._plot_item.setLabel('left', 'Time', units='s')
        # self._plot_item.setLabel('right', 'Number of Points', units='#')
        self._plot_item.setLabel('top', 'Wavelength', units='nm')
        self._plot_item.setLabel('bottom', 'Relative Frequency', units='Hz')
        self._mw.shgPD_ViewWidget.addItem(self.shgPD_image)
        self._mw.shgPD_ViewWidget.showGrid(x=True, y=True, alpha=0.8)
        self._mw.opoPD_ViewWidget.addItem(self.opoPD_image)
        self._mw.opoPD_ViewWidget.showGrid(x=True, y=True, alpha=0.8)
        
        # self.lr = pg.LinearRegionItem([0, 100], bounds=[0, 100])#, pen=pg.mkPen({'color': "E8C4F7", alpha=0.3}))
        # self.lr.setZValue(0)
        # self._mw.scan_ViewWidget.addItem(self.lr)
        # self.lr.sigRegionChangeFinished.connect(self.regionChanged)
        # self.lr.sigRegionChanged.connect(self.displayRegion)
        # self.freq_pos = pg.InfiniteLine(0, movable=True, pen=pg.mkPen({'color': "E8C4F7", 'width': 2}), bounds=[0,100])
        # self._mw.scan_ViewWidget.addItem(self.freq_pos)
        # self.freq_pos.setZValue(100)
        # self.freq_pos.sigPositionChangeFinished.connect(self.freqChanged)
        # self.freq_pos.sigDragged.connect(self.displayFreq)    
        self._mw.scan_matrix_ViewWidget.addItem(self.scan_matrix_image)
        #! Get the colorscales at set LUT
        my_colors = ColorScaleInferno()
        self.scan_matrix_image.setLookupTable(my_colors.lut)
        # Configuration of the Colorbar
        self.scan_cb = ColorBar(my_colors.cmap_normed, 100, 0, 100000)
        #adding colorbar to ViewWidget
        self._mw.scan_cb_ViewWidget.addItem(self.scan_cb)
        self._mw.scan_cb_ViewWidget.hideAxis('bottom')
        self._mw.scan_cb_ViewWidget.hideAxis('left')
        self._mw.scan_cb_ViewWidget.setLabel('right', 'Fluorescence', units='c/s')
        # Connect the buttons and inputs for colorbar
        self._mw.scan_cb_manual_RadioButton.clicked.connect(self.refresh_matrix)
        self._mw.scan_cb_centiles_RadioButton.clicked.connect(self.refresh_matrix)
        self._mw.scan_cb_max_InputWidget.valueChanged.connect(self.refresh_matrix)
        self._mw.scan_cb_min_InputWidget.valueChanged.connect(self.refresh_matrix)
        self._mw.scan_cb_high_centile_InputWidget.valueChanged.connect(self.refresh_matrix)
        self._mw.scan_cb_low_centile_InputWidget.valueChanged.connect(self.refresh_matrix) 
    def set_up_cwave_control_panel(self):
        self._mw.pushButton_connectCwave.clicked.connect(self.changeCwaveState)
        for shutter in self._cwavescan_logic.shutters.keys():
            eval(f"self._mw.checkBox_{shutter}.stateChanged.connect(self.flip_shutter)")
         
        self._mw.pushButtonOpt_opt_stop.clicked.connect(self.optimizing)
        self._mw.pushButtonOpt_opt_tempshg.clicked.connect(self.optimizing)
        self._mw.pushButtonOpt_regeta_catch.clicked.connect(self.optimizing)

        self._mw.eta_lock_checkBox.clicked.connect(self.change_lock_mode)
        self._mw.opo_lock_checkBox.clicked.connect(self.change_lock_mode)
        self._mw.thick_eta_spinBox.editingFinished.connect(self.adjust_thick_etalon)
        self._mw.opo_lambda_spinBox.editingFinished.connect(self.adjust_opo_lambda)
        self._mw.ref_cav_doubleSpinBox.editingFinished.connect(self.update_setpoint)

        #? Connect signals
        self.sig_set_shutter_state.connect(self._cwavescan_logic.change_shutter_state)
        self.sig_optimize_cwave.connect(self._cwavescan_logic.optimize_cwave)
        self.sig_connect_cwave.connect(self._cwavescan_logic.connection_cwave)
        self.sig_change_lock_mode.connect(self._cwavescan_logic.change_lock_mode)
        self.sig_adj_thick_etalon.connect(self._cwavescan_logic.adj_thick_etalon)
        self.sig_adj_opo.connect(self._cwavescan_logic.adj_opo_lambda)
    def set_up_scanner_panel(self):
        self.sig_start_sweep.connect(self._cwavescan_logic.start_sweep)
        self.sig_stop_sweep.connect(self._cwavescan_logic.stop_sweep)
        self.sig_set_refcav.connect(self._cwavescan_logic.refcav_setpoint)
        self.sig_save_measurement.connect(self._cwavescan_logic.save_data)
        self.sig_refresh_sweep_zpl.connect(self._cwavescan_logic.refresh_sweep_zpl)
        self._mw.refresh_zpl_sweep_pushButton.clicked.connect(self.refresh_sweep_zpl)
        self._mw.sweepCenterDoubleSpinBox.editingFinished.connect(self.update_zpl_sweep_params)
        self._mw.sweepSpeedSpinBox.editingFinished.connect(self.update_zpl_sweep_params)
        self._mw.sweepAmplitudeDoubleSpinBox.editingFinished.connect(self.update_zpl_sweep_params)
        self.sig_regulation_mode.connect(self._cwavescan_logic.regulate_wavelength)
        self._mw.regulate_checkBox.toggled.connect(self.regulate_wavelength)
        #run_stop_sweeping
        self._mw.sweep_checkBox.toggled.connect(self.run_stop_sweep)
        # self._mw.action_run_stop.triggered.connect(self.run_stop)
        self._mw.action_Save.triggered.connect(self.save_data)
        self._mw.action_search_zpl.triggered.connect(self.open_zpl_search)
        self.sig_update_zpl_search_params.connect(self._cwavescan_logic.update_zpl_search_params)
        self.sig_refresh_zpl_search.connect(self._cwavescan_logic.refresh_search_zpl)
        self.sig_reset_zpl_search.connect(self._cwavescan_logic.reset_search_zpl)
        self.open_zpl_search()   
        self._zplw.close()
    def open_zpl_search(self):
        self._zplw = SearchZPL() 
        self._zplw.show()
        self._zplw.sig_stop_zpl_search.connect(self._cwavescan_logic.stop_zpl_search)
        self._zplw.refresh_pushButton.clicked.connect(self.refresh_search_zpl)
        self._zplw.reset_pushButton.clicked.connect(self.reset_search_zpl)
        self._zplw.binWidthdoubleSpinBox.editingFinished.connect(self.update_zpl_search_params)
        #!TBD 
        # self._zplw.reset_pushButton
        self._zplw.wl1DoubleSpinBox.editingFinished.connect(self.update_zpl_search_params)
        self._zplw.wl2DoubleSpinBox.editingFinished.connect(self.update_zpl_search_params) 
        self.update_zpl_search_params()
        self._zplw.search_image = pg.PlotDataItem(self._cwavescan_logic.plot_xs, 
        self._cwavescan_logic.plot_ys, 
        symbol='o', 
        symbolSize=4,
        pen={'color': 0.6, 'width': 1})
        self._zplw.err = pg.ErrorBarItem(x=self._cwavescan_logic.plot_xs, y=self._cwavescan_logic.plot_ys,
         height = self._cwavescan_logic.deviance_ys,  
         beam=self.wl_beam)
        self._zplw.search_ViewWidget.addItem(self._zplw.search_image)
        self._zplw.search_ViewWidget.addItem(self._zplw.err)
    def update_zpl_search_params(self):
        w1 = self._zplw.wl1DoubleSpinBox.value()
        w2 = self._zplw.wl2DoubleSpinBox.value()
        binWidth = self._zplw.binWidthdoubleSpinBox.value()
        self.wl_beam = binWidth
        self.sig_update_zpl_search_params.emit(w1, w2, binWidth)
    def update_zpl_sweep_params(self):
        amplitude = self._mw.sweepAmplitudeDoubleSpinBox.value()
        if amplitude > 0.01:
            amplitude = 0.01
            self._mw.sweepAmplitudeDoubleSpinBox.setValue(amplitude)
        center_wl = self._mw.sweepCenterDoubleSpinBox.value()
        if np.abs(self._cwavescan_logic.wavelength - center_wl) > 0.02:
            center_wl = self._cwavescan_logic.wavelength
            self._mw.sweepCenterDoubleSpinBox.setValue(center_wl)
        sweep_speed = self._mw.sweepSpeedSpinBox.value()
        self.sig_set_zpl_sweep_params.emit(amplitude, center_wl,sweep_speed)
    def reset_search_zpl(self):
        self.sig_reset_zpl_search.emit()
    def refresh_search_zpl(self):
        self.sig_refresh_zpl_search.emit()
    def refresh_sweep_zpl(self):
        self.sig_refresh_sweep_zpl.emit()
    def refresh_wlm(self):
        self._cwavescan_logic.plot_y_wlm = np.array([])
        self.refresh_plots()
    def regulate_wavelength(self, mode_manual = None):
        if mode_manual is not None:
            mode = mode_manual
            self._mw.regulate_checkBox.setChecked(mode_manual)
        else:
            mode = self.sender().isChecked()
        self.sig_regulation_mode.emit(mode)   
    def displayRegion(self):
        reg = self.lr.getRegion()
        #self._mw.startDoubleSpinBox.setValue(np.round(reg[0], 2))
        #self._mw.stopDoubleSpinBox.setValue(np.round(reg[1], 2))
    def regionChanged(self):
        region = self.lr.getRegion()
        r1 = 0#self._mw.startDoubleSpinBox.value()
        r2 = 0#self._mw.stopDoubleSpinBox.value()
        self.lr.setRegion([r1, r2])
        # self.sigChangeRange.emit([
        #     r1,
        #     r2
        # ])
        # print(region)
    def show(self):
        """Make window visible and put it above all other windows. """
        self._mw.show()
        self._mw.activateWindow()
        self._mw.raise_()
    def run_stop_sweep(self, is_checked):
        """ Manages what happens if scan is started/stopped """
        # self._mw.action_run_stop.setEnabled(False)
        if self._mw.sweep_checkBox.isChecked():
            self._mw.regulate_checkBox.setChecked(False)
            self._mw.regulate_checkBox.setEnabled(False)
            self.sig_start_sweep.emit()
        else:
            print("stopiing")
            self._cwavescan_logic.stopRequested = True
            self._mw.regulate_checkBox.setEnabled(True)
            self._mw.regulate_checkBox.setChecked(True)
            self.regulate_wavelength(mode_manual = False)
            self.sig_stop_sweep.emit()
    def refresh_plots(self):
        """ Refresh the xy-plot image """
        self.scan_image.setData(self._cwavescan_logic.plot_x, self._cwavescan_logic.plot_y)
        self.shgPD_image.setData(self._cwavescan_logic.plot_x_shg_pd, self._cwavescan_logic.plot_y_shg_pd[-len(self._cwavescan_logic.plot_x_shg_pd):])
        self.opoPD_image.setData(self._cwavescan_logic.plot_x_opo_pd, self._cwavescan_logic.plot_y_opo_pd[-len(self._cwavescan_logic.plot_x_opo_pd):])
        wlm_y = self._cwavescan_logic.plot_y_wlm
        wlm_y = wavelength_to_freq(wlm_y)
        if len(wlm_y) > 0:
            self.wavemeter_image.setData(wlm_y - wlm_y[-1], np.linspace(0, len(wlm_y), len(wlm_y)))

        #Refresh search:
        if self._zplw.search_image is not None:
            self._zplw.search_image.setData(self._cwavescan_logic.plot_xs, self._cwavescan_logic.plot_ys)
            self._zplw.err.setData(x=self._cwavescan_logic.plot_xs,
            y = self._cwavescan_logic.plot_ys,
            height = self._cwavescan_logic.deviance_ys,
            beam=self.wl_beam)
    @QtCore.Slot()
    def update_gui(self):
        self.refresh_plots()
        self.refresh_matrix()
        self.refresh_scan_colorbar()
        self.update_cwave_panel()
    def save_data(self):
        """ Save the sum plot, the scan marix plot and the scan data """
        filetag = self._mw.save_tag_LineEdit.text()
        cb_range = self.get_matrix_cb_range()

        # Percentile range is None, unless the percentile scaling is selected in GUI.
        pcile_range = None
        if self._mw.scan_cb_centiles_RadioButton.isChecked():
            low_centile = self._mw.scan_cb_low_centile_InputWidget.value()
            high_centile = self._mw.scan_cb_high_centile_InputWidget.value()
            pcile_range = [low_centile, high_centile]

        self.sig_save_measurement.emit(filetag, cb_range, pcile_range)
    @QtCore.Slot()
    def adjust_thick_etalon(self):
        delta_eta = int(self._mw.thick_eta_spinBox.value())
        if delta_eta > 0 :
            self.regulate_wavelength(mode_manual = False)

        self.sig_adj_thick_etalon.emit(delta_eta) 
    @QtCore.Slot()
    def adjust_opo_lambda(self):
        delta_lam = int(self._mw.opo_lambda_spinBox.value())
        if delta_lam > 0 :
            self.regulate_wavelength(mode_manual = False)
        self.sig_adj_opo.emit(delta_lam) 
    @QtCore.Slot()
    def update_setpoint(self):
        self.sig_set_refcav.emit(self._mw.ref_cav_doubleSpinBox.value())
    @QtCore.Slot()
    def change_lock_mode(self, _param=None, _mode=None):
        sender = self.sender()
        if "_lock_checkBox" in sender.objectName():
                _param = sender.objectName().split('_lock_checkBox')[0].strip()
                _mode = 'control' if sender.isChecked() else 'manual'
                print(_param, _mode)
                self.sig_change_lock_mode.emit(_param, _mode)
    @QtCore.Slot()
    def optimizing(self):
        sender = self.sender()
        if "pushButtonOpt_" in sender.objectName():
            opt_param = sender.objectName().split('pushButtonOpt_')[-1].strip()
            self.sig_optimize_cwave.emit(opt_param)
        else:
            print("Wrong button for this function!")
    @QtCore.Slot()
    def flip_shutter(self):
        sender = self.sender()
        state = sender.isChecked()
        if "checkBox_shtter" in sender.objectName():
            _shutter = sender.objectName().split('checkBox_')[-1].strip()
            self.sig_set_shutter_state.emit(_shutter, state)
        elif "checkBox_laser_en" in sender.objectName():
            _pump = sender.objectName().split('checkBox_')[-1].strip()
            self.sig_set_shutter_state.emit(_pump, state)
        else:
            print("Wrong button for this function!")
    @QtCore.Slot()
    def update_cwave_panel(self):
        """ Logic told us to update our button states, so set the buttons accordingly. """
        #! connect button 
        if self._cwavescan_logic.cwstate == 0:
            self._mw.pushButton_connectCwave.setText('Connect')
            self._mw.radioButton_connectCwave.setChecked(False)
        else:
            self._mw.pushButton_connectCwave.setText('Disconnect')
            self._mw.radioButton_connectCwave.setChecked(True)
        

        #! shutters:
        for shutter, state in self._cwavescan_logic.shutters.items():
            eval(f"self._mw.checkBox_{shutter}.setChecked({state})")
        #! states:
        for param, state in self._cwavescan_logic.status_cwave.items():
            eval(f"self._mw.radioButton_{param}.setChecked({state})")

        #! wavelength
        #TODO: read wavelength from the wavelengthmeter
        wlm = self._cwavescan_logic.wavelength
        wlm = wlm if wlm is not None else 0
        self._mw.label_wavelength.setText(f"{wlm}")
        self._mw.sweepCenterDoubleSpinBox.setValue(np.round(wlm, 3))
        #! photodiodes  
        self._mw.label_laserPD.setText(f"{self._cwavescan_logic.laserPD}")
        self._mw.label_opoPD.setText(f"{self._cwavescan_logic.opoPD}")
        self._mw.label_shgPD.setText(f"{self._cwavescan_logic.shgPD}")
        if self._cwavescan_logic.reg_modes is not None:
            self._mw.eta_lock_checkBox.setEnabled(True)
            self._mw.opo_lock_checkBox.setEnabled(True)
            self._mw.eta_lock_checkBox.setChecked(True if self._cwavescan_logic.reg_modes['eta'] == 2 else False)
            self._mw.opo_lock_checkBox.setChecked(True if self._cwavescan_logic.reg_modes['opo'] == 2 else False)
        else:
            self._mw.eta_lock_checkBox.setEnabled(False)
            self._mw.opo_lock_checkBox.setEnabled(False)
    @QtCore.Slot()
    def changeCwaveState(self):
        # print(self._cwavescan_logic.cwstate)
        self.sig_connect_cwave.emit()
    def get_matrix_cb_range(self):
        """
        Determines the cb_min and cb_max values for the matrix plot
        """
        matrix_image = self.scan_matrix_image.image

        # If "Manual" is checked or the image is empty (all zeros), then take manual cb range.
        # Otherwise, calculate cb range from percentiles.
        if self._mw.scan_cb_manual_RadioButton.isChecked() or np.max(matrix_image) < 0.1:
            cb_min = self._mw.scan_cb_min_InputWidget.value()
            cb_max = self._mw.scan_cb_max_InputWidget.value()
        else:
            # Exclude any zeros (which are typically due to unfinished scan)
            matrix_image_nonzero = matrix_image[np.nonzero(matrix_image)]

            # Read centile range
            low_centile = self._mw.scan_cb_low_centile_InputWidget.value()
            high_centile = self._mw.scan_cb_high_centile_InputWidget.value()

            cb_min = np.percentile(matrix_image_nonzero, low_centile)
            cb_max = np.percentile(matrix_image_nonzero, high_centile)

        cb_range = [cb_min, cb_max]
        return cb_range
    def refresh_scan_colorbar(self):
        """ Update the colorbar to a new scaling."""

        # If "Centiles" is checked, adjust colour scaling automatically to centiles.
        # Otherwise, take user-defined values.
        if self._mw.scan_cb_centiles_RadioButton.isChecked():
            low_centile = self._mw.scan_cb_low_centile_InputWidget.value()
            high_centile = self._mw.scan_cb_high_centile_InputWidget.value()

            cb_min = np.percentile(self.scan_matrix_image.image, low_centile)
            cb_max = np.percentile(self.scan_matrix_image.image, high_centile)
        else:
            cb_min = self._mw.scan_cb_min_InputWidget.value()
            cb_max = self._mw.scan_cb_max_InputWidget.value()

        self.scan_cb.refresh_colorbar(cb_min, cb_max)
        self._mw.scan_cb_ViewWidget.update()


    def refresh_matrix(self):
        """ Refresh the xy-matrix image """
        self.scan_matrix_image.setImage(self._cwavescan_logic.scan_matrix, axisOrder='row-major')
        scan_image_data = self._cwavescan_logic.scan_matrix
        self.scan_matrix_image.setRect(QtCore.QRectF(10,0,10,scan_image_data.shape[1]))
        self.refresh_scan_colorbar()

        # If "Centiles" is checked, adjust colour scaling automatically to centiles.
        # Otherwise, take user-defined values.
        if self._mw.scan_cb_centiles_RadioButton.isChecked():
            low_centile = self._mw.scan_cb_low_centile_InputWidget.value()
            high_centile = self._mw.scan_cb_high_centile_InputWidget.value()

            cb_min = np.percentile(scan_image_data, low_centile)
            cb_max = np.percentile(scan_image_data, high_centile)
        else:
            cb_min = self._mw.scan_cb_min_InputWidget.value()
            cb_max = self._mw.scan_cb_max_InputWidget.value()

        # Now update image with new color scale, and update colorbar
        self.scan_matrix_image.setImage(
            image=scan_image_data,
            levels=(cb_min, cb_max),
            axisOrder='row-major')

        self.refresh_scan_colorbar()