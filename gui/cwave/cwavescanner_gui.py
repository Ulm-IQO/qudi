
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



class ScannerWindow(QtWidgets.QMainWindow):
    """ Create the Main Window based on the *.ui file. """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'cwave.ui')

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

    sigStopScan = QtCore.Signal()
    sigChangeSetpoint = QtCore.Signal(float)
    sigChangeRange = QtCore.Signal(list)
    sigChangeBinsNumber = QtCore.Signal(int)
    sigSaveMeasurement = QtCore.Signal(str, list, list)
    sigScanMode = QtCore.Signal(str)
    sigCwave = QtCore.Signal()
    sigChangeScanwith = QtCore.Signal()
    sigWavelength = QtCore.Signal()
    sigSetShutter = QtCore.Signal(str, bool)
    sigOptimize = QtCore.Signal(str)
    sigUpdateLaserStatus = QtCore.Signal()
    sigStartScan = QtCore.Signal()
    def on_deactivate(self):
        """ Reverse steps of activation

        @return int: error code (0:OK, -1:error)
        """
        self._mw.close()
        return 0

    def on_activate(self):
        """ 

        """
        self._cwavescan_logic = self.cwavelogic()

        self._savelogic = self.savelogic()

        # Use the inherited class 'Ui_VoltagescannerGuiUI' to create now the
        # GUI element:
        self._mw = ScannerWindow()

        # Add save file tag input box
        self._mw.save_tag_LineEdit = QtWidgets.QLineEdit(self._mw)
        self._mw.save_tag_LineEdit.setMaximumWidth(500)
        self._mw.save_tag_LineEdit.setMinimumWidth(200)
        self._mw.save_tag_LineEdit.setToolTip('Enter a nametag which will be\n'
                                              'added to the filename.')
        self._mw.toolBar.addWidget(self._mw.save_tag_LineEdit)
        
        #! Get the image from the logic
        self.scan_matrix_image = pg.ImageItem(
            self._cwavescan_logic.scan_matrix,
            axisOrder='row-major')

        self.scan_matrix_image.setRect(
            QtCore.QRectF(
                self._cwavescan_logic.scan_range[0],
                0,
                self._cwavescan_logic.scan_range[1] - self._cwavescan_logic.scan_range[0],
                self._cwavescan_logic.number_of_repeats)
        )

        self.scan_image = pg.PlotDataItem(
            self._cwavescan_logic.plot_x,
            self._cwavescan_logic.plot_y)

        self.shgPD_image = pg.PlotDataItem(
            self._cwavescan_logic.plot_x_shg_pd,
            self._cwavescan_logic.plot_y_shg_pd)

        self.opoPD_image = pg.PlotDataItem(
            self._cwavescan_logic.plot_x_opo_pd,
            self._cwavescan_logic.plot_y_opo_pd)

        self.wavemeter_image = pg.PlotDataItem(
            self._cwavescan_logic.plot_x_wlm,
            self._cwavescan_logic.plot_y_wlm)

        self.scan_fit_image = pg.PlotDataItem(
            self._cwavescan_logic.fit_x,
            self._cwavescan_logic.fit_y,
            pen=QtGui.QPen(QtGui.QColor(255, 255, 255, 255)))




        # Add the display item to the xy and xz VieWidget, which was defined in
        # the UI file.
        self._mw.scan_ViewWidget.addItem(self.scan_image)
        self._mw.wavelength_ViewWidget.addItem(self.wavemeter_image)

        self._mw.shgPD_ViewWidget.addItem(self.shgPD_image)
        self._mw.shgPD_ViewWidget.showGrid(x=True, y=True, alpha=0.8)
        self._mw.opoPD_ViewWidget.addItem(self.opoPD_image)
        self._mw.opoPD_ViewWidget.showGrid(x=True, y=True, alpha=0.8)
        self._mw.wavemeter_ViewWidget.addItem(self.wavemeter_image)
        self._mw.wavemeter_ViewWidget.showGrid(x=True, y=True, alpha=0.8)
        #self._mw.voltscan_ViewWidget.addItem(self.scan_fit_image)
        self._mw.scan_ViewWidget.showGrid(x=True, y=True, alpha=0.8)

        self.lr = pg.LinearRegionItem([0, 100], bounds=[0, 100])#, pen=pg.mkPen({'color': "E8C4F7", alpha=0.3}))
        self.lr.setZValue(0)
        self._mw.scan_ViewWidget.addItem(self.lr)
        self.lr.sigRegionChangeFinished.connect(self.regionChanged)
        self.lr.sigRegionChanged.connect(self.displayRegion)

        self.freq_pos = pg.InfiniteLine(0, movable=True, pen=pg.mkPen({'color': "E8C4F7", 'width': 2}), bounds=[0,100])
        self._mw.scan_ViewWidget.addItem(self.freq_pos)
        self.freq_pos.setZValue(100)
        self.freq_pos.sigPositionChangeFinished.connect(self.freqChanged)
        self.freq_pos.sigDragged.connect(self.displayFreq)
        
        

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

        #! set initial values
        self._mw.startDoubleSpinBox.setValue(self._cwavescan_logic.scan_range[0])
        self._mw.stopDoubleSpinBox.setValue(self._cwavescan_logic.scan_range[1])
        self._mw.constDoubleSpinBox.setValue(self._cwavescan_logic._static_v)
        self._mw.numberOfBinsSpinBox.setValue(self._cwavescan_logic.number_of_bins)
        self._mw.linesSpinBox.setValue(self._cwavescan_logic.number_of_repeats)

        # Update the inputed/displayed numbers if the cursor has left the field:
        self._mw.startDoubleSpinBox.editingFinished.connect(self.change_start_volt)
        self._mw.pixDurationDoubleSpinBox.editingFinished.connect(self.update_duration)
        self._mw.stopDoubleSpinBox.editingFinished.connect(self.change_stop_volt)
        self._mw.numberOfBinsSpinBox.editingFinished.connect(self.change_numer_of_bins)
        self._mw.constDoubleSpinBox.editingFinished.connect(self.update_setpoint)

        self._mw.scan_cb_max_InputWidget.valueChanged.connect(self.refresh_matrix)
        self._mw.scan_cb_min_InputWidget.valueChanged.connect(self.refresh_matrix)
        self._mw.scan_cb_high_centile_InputWidget.valueChanged.connect(self.refresh_matrix)
        self._mw.scan_cb_low_centile_InputWidget.valueChanged.connect(self.refresh_matrix)

        #! Configure laser control panel:
        #? Connect buttons
        self._mw.pushButton_connectCwave.clicked.connect(self.changeCwaveState)
        # self._mw.checkBox_shutter_shg_out.stateChanged.connect(self.flip_shutter)

        for shutter in self._cwavescan_logic.shutters.keys():
            eval(f"self._mw.checkBox_{shutter}.stateChanged.connect(self.flip_shutter)")

        optimize_commands = ["opt_stop", "opt_tempshg", "regeta_catch"]
        for opt in optimize_commands:
            eval(f"self._mw.pushButtonOpt_{opt}.clicked.connect(self.optimizing)")

        # choose scanning mode
        scan_modes = ["refcavint", "oporeg", "refcavext"]
        for mode in scan_modes:
            eval(f"self._mw.radioButtonMode_{mode}.toggled.connect(self.change_scan_mode)")
        self.sigScanMode.connect(self._cwavescan_logic.change_scan_mode)

        #? Connect signals
        self.sigSetShutter.connect(self._cwavescan_logic.change_shutter_state)
        self.sigOptimize.connect(self._cwavescan_logic.optimize_cwave)
        self.sigCwave.connect(self._cwavescan_logic.connection_cwave)

        #! Connect signals
        self._cwavescan_logic.sigUpdate.connect(self.refresh_matrix)
        self._cwavescan_logic.sigUpdate.connect(self.refresh_plot)
        self._cwavescan_logic.sigUpdate.connect(self.updateGui)
        self._cwavescan_logic.sigUpdateScanPlots.connect(self.updateScanPlots)
        self._cwavescan_logic.sigScanFinished.connect(self.scan_stopped)
        self._cwavescan_logic.sigScanStarted.connect(self.scan_started)



        #! Scan control panel
        self.sigStartScan.connect(self._cwavescan_logic.start_scanning)
        self.sigStopScan.connect(self._cwavescan_logic.stop_scanning)
        self.sigChangeSetpoint.connect(self._cwavescan_logic.change_setpoint)
        self.sigChangeRange.connect(self._cwavescan_logic.set_scan_range)

        self.sigChangeBinsNumber.connect(self._cwavescan_logic.set_number_of_bins)
        # self.sigSaveMeasurement.connect(self._cwavescan_logic.save_data)

        self._mw.action_run_stop.triggered.connect(self.run_stop)
        # self._mw.action_Save.triggered.connect(self.save_data)
        self._mw.show()
    @QtCore.Slot()
    def change_scan_mode(self):
        sender = self.sender()
        if "radioButtonMode_" in sender.objectName():
            _mode = sender.objectName().split('radioButtonMode_')[-1].strip()
            self.sigScanMode.emit(_mode)
        else:
            print("Wrong button for this function!")
    @QtCore.Slot()
    def optimizing(self):
        sender = self.sender()
        if "pushButtonOpt_" in sender.objectName():
            opt_param = sender.objectName().split('pushButtonOpt_')[-1].strip()
            self.sigOptimize.emit(opt_param)
        else:
            print("Wrong button for this function!")

    @QtCore.Slot()
    def flip_shutter(self):
        sender = self.sender()
        state = sender.isChecked()
        if "checkBox_shtter" in sender.objectName():
            _shutter = sender.objectName().split('checkBox_')[-1].strip()
            self.sigSetShutter.emit(_shutter, state)
        elif "checkBox_laser_en" in sender.objectName():
            _pump = sender.objectName().split('checkBox_')[-1].strip()
            self.sigSetShutter.emit(_pump, state)
        else:
            print("Wrong button for this function!")

    @QtCore.Slot()
    def updateCwaveControlPanel(self):
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
        self._mw.label_wavelength.setText(f"{self._cwavescan_logic.wavelength}")
        #! photodiodes  
        self._mw.label_laserPD.setText(f"{self._cwavescan_logic.laserPD}")
        self._mw.label_opoPD.setText(f"{self._cwavescan_logic.opoPD}")
        self._mw.label_shgPD.setText(f"{self._cwavescan_logic.shgPD}")


    @QtCore.Slot()
    def changeCwaveState(self):
        print(self._cwavescan_logic.cwstate)
        self.sigCwave.emit()

    def displayFreq(self):
        freq = self.freq_pos.value()
        self._mw.constDoubleSpinBox.setValue(np.round(freq, 2))

    def freqChanged(self):
        freq = self.freq_pos.value()
        self._mw.constDoubleSpinBox.setValue(np.round(freq, 2))
        self.sigChangeSetpoint.emit(freq)
        # print(freq)

    def displayRegion(self):
        reg = self.lr.getRegion()
        self._mw.startDoubleSpinBox.setValue(np.round(reg[0], 2))
        self._mw.stopDoubleSpinBox.setValue(np.round(reg[1], 2))

    def regionChanged(self):
        region = self.lr.getRegion()
        r1 = self._mw.startDoubleSpinBox.value()
        r2 = self._mw.stopDoubleSpinBox.value()
        self.lr.setRegion([r1, r2])
        # print(region)

    def show(self):
        """Make window visible and put it above all other windows. """
        self._mw.show()
        self._mw.activateWindow()
        self._mw.raise_()

    def run_stop(self, is_checked):
        """ Manages what happens if scan is started/stopped """
        # self._mw.action_run_stop.setEnabled(False)
        if self._mw.action_run_stop.isChecked():
            self.sigStartScan.emit()
        else:
            print("stopiing")
            self._cwavescan_logic.stopRequested = True
            self.sigStopScan.emit()

        # if is_checked:
        #     self.sigStartScan.emit()

            
        #     self._mw.scan_ViewWidget.removeItem(self.scan_fit_image)
        # else:
        #     self.sigStopScan.emit()


    def scan_started(self):
        self._mw.action_run_stop.setEnabled(True)

    def scan_stopped(self):
        self._mw.action_run_stop.setEnabled(True)
        self._mw.action_run_stop.setChecked(False)
        self.refresh_plot()
        self.refresh_matrix()
        self.refresh_lines()


    def refresh_plot(self):
        """ Refresh the xy-plot image """
        self.scan_image.setData(self._cwavescan_logic.plot_x, self._cwavescan_logic.plot_y)
        self.shgPD_image.setData(self._cwavescan_logic.plot_x_shg_pd, self._cwavescan_logic.plot_y_shg_pd[-len(self._cwavescan_logic.plot_x_shg_pd):])
        self.opoPD_image.setData(self._cwavescan_logic.plot_x_opo_pd, self._cwavescan_logic.plot_y_opo_pd[-len(self._cwavescan_logic.plot_x_opo_pd):])
        self.wavemeter_image.setData(self._cwavescan_logic.plot_x_wlm, self._cwavescan_logic.plot_y_wlm[-len(self._cwavescan_logic.plot_x_wlm):])

    def refresh_matrix(self):
        """ Refresh the xy-matrix image """
        self.scan_matrix_image.setImage(self._cwavescan_logic.scan_matrix, axisOrder='row-major')
        scan_image_data = self._cwavescan_logic.scan_matrix
        self.scan_matrix_image.setRect(
            QtCore.QRectF(
                self._cwavescan_logic.scan_range[0],
                0,
                self._cwavescan_logic.scan_range[1] - self._cwavescan_logic.scan_range[0],
                scan_image_data.shape[1])
            )
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

    def refresh_lines(self):
        self._mw.elapsed_lines_DisplayWidget.display(self._cwavescan_logic._scan_counter_up)

    def update_setpoint(self):
        self.sigChangeSetpoint.emit(self._mw.constDoubleSpinBox.value())

    def change_start_volt(self):
        self.sigChangeRange.emit([
            self._mw.startDoubleSpinBox.value(),
            self._mw.stopDoubleSpinBox.value()
        ])

    def update_duration(self):
        self._cwavescan_logic.pix_integration = float(self._mw.pixDurationDoubleSpinBox.value())

    def change_stop_volt(self):
        self.sigChangeRange.emit([
            self._mw.startDoubleSpinBox.value(),
            self._mw.stopDoubleSpinBox.value()
        ])

    def change_numer_of_bins(self):
        self.sigChangeBinsNumber.emit(self._mw.numberOfBinsSpinBox.value())

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


    @QtCore.Slot()
    def updateGui(self):
        # for name, curve in self.curves.items():
        #     curve.setData(x=self._laser_logic.data['time'], y=self._laser_logic.data[name])
        self.updateCwaveControlPanel()

    @QtCore.Slot()
    def updateScanPlots(self):
        self.refresh_plot()
        self.refresh_matrix()
        self.refresh_scan_colorbar()

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

        self.sigSaveMeasurement.emit(filetag, cb_range, pcile_range)

#! Control panel:
    