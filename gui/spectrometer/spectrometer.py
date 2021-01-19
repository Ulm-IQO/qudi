# -*- coding: utf-8 -*-
"""
This module contains a GUI for operating the spectrum logic module.

Qudi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Qudi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Qudi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

import os
import pyqtgraph as pg
import numpy as np
from functools import partial

from core.connector import Connector
from core.configoption import ConfigOption
from core.util.units import ScaledFloat
from core.statusvariable import StatusVar
from gui.guibase import GUIBase
from gui.colordefs import ColorScaleInferno
from gui.colordefs import QudiPalette as palette
from qtwidgets.scientific_spinbox import ScienDSpinBox
from interface.grating_spectrometer_interface import PortType
from logic.spectrum_logic import AcquisitionMode
from qtpy import QtCore
from qtpy import QtWidgets
from qtpy import uic
from gui.gui_components.colorbar.colorbar import ColorbarWidget

class MainWindow(QtWidgets.QMainWindow):

    def __init__(self):
        """ Create the laser scanner window.
        """
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_mainwindow.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)
        self.show()

class SettingsTab(QtWidgets.QWidget):

    def __init__(self):
        """ Create the laser scanner window.
        """
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_settings_tab.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)
        self.show()

class ImageTab(QtWidgets.QWidget):

    def __init__(self):
        """ Create the laser scanner window.
        """
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_image_tab.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)
        self.show()

class AlignementTab(QtWidgets.QWidget):

    def __init__(self):
        """ Create the laser scanner window.
        """
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_alignement_tab.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)
        self.show()

class SpectrumTab(QtWidgets.QWidget):

    def __init__(self):
        """ Create the laser scanner window.
        """
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_spectrum_tab.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)
        self.show()


class Main(GUIBase):
    """
    """
    # declare connectors
    spectrumlogic = Connector(interface='SpectrumLogic')
    savelogic = Connector(interface='SaveLogic')

    _cooler_temperature_unit = ConfigOption('cooler_temperature_unit')

    _alignement_read_mode = StatusVar('alignement_read_mode', 'FVB')
    _alignement_exposure_time = StatusVar('alignement_exposure_time', 0)
    _alignement_time_window = StatusVar('alignement_time_window', 60)

    _image_read_mode = StatusVar('image_read_mode', 'IMAGE_ADVANCED')
    _image_acquisition_mode = StatusVar('image_acquisition_mode', 'LIVE')
    _image_exposure_time = StatusVar('image_exposure_time', None)
    _image_readout_speed = StatusVar('image_readout_speed', None)

    _spectrum_read_mode = StatusVar('spectrum_read_mode', 'MULTIPLE_TRACKS')
    _spectrum_acquisition_mode = StatusVar('spectrum_acquisition_mode', 'SINGLE_SCAN')
    _spectrum_exposure_time = StatusVar('spectrum_exposure_time', None)
    _spectrum_readout_speed = StatusVar('spectrum_readout_speed', None)

    _active_tracks = StatusVar('active_tracks', [])
    _image_advanced = StatusVar('image_advanced', [])

    _image_data = StatusVar('image_data', np.zeros((1000, 1000)))
    _image_dark = StatusVar('image_dark', np.zeros((1000, 1000)))
    _image_params = StatusVar('image_params', dict())
    _counter_data = StatusVar('counter_data', np.zeros((2, 1000)))
    _spectrum_data = StatusVar('spectrum_data', np.zeros((2, 1000)))
    _spectrum_dark = StatusVar('spectrum_dark', np.zeros(1000))
    _spectrum_params = StatusVar('spectrum_params', dict())

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Definition and initialisation of the GUI.
        """
        self._spectrumlogic = self.spectrumlogic()

        # setting up the window
        self._mw = MainWindow()
        self._settings_tab = SettingsTab()
        self._image_tab = ImageTab()
        self._alignement_tab = AlignementTab()
        self._spectrum_tab = SpectrumTab()

        self._mw.tab.addTab(self._settings_tab, "Settings")
        self._mw.tab.addTab(self._image_tab, "Image")
        self._mw.tab.addTab(self._alignement_tab, "Aligement")
        self._mw.tab.addTab(self._spectrum_tab, "Spectrum")

        self._acquire_dark_buttons = []
        self._start_acquisition_buttons = []
        self._stop_acquisition_buttons = []
        self._save_data_buttons = []

        self._track_buttons = [self._image_tab.track1, self._image_tab.track2,
                               self._image_tab.track3, self._image_tab.track4]
        self._track_selector = []

        if not self._image_exposure_time:
            self._image_exposure_time = self._spectrumlogic.exposure_time
        if not self._image_readout_speed:
            self._image_readout_speed = self._spectrumlogic.readout_speed
        if not self._alignement_exposure_time:
            self._alignement_exposure_time = self._spectrumlogic.exposure_time
        if not self._spectrum_exposure_time:
            self._spectrum_exposure_time = self._spectrumlogic.exposure_time
        if not self._spectrum_readout_speed:
            self._spectrum_readout_speed = self._spectrumlogic.readout_speed

        self._activate_settings_tab()
        self._activate_image_tab()
        self._activate_alignement_tab()
        self._activate_spectrum_tab()
        self._settings_window = [self._image_tab.image_settings, self._alignement_tab.counter_settings,
                    self._spectrum_tab.spectrum_settings]

        self._manage_stop_acquisition()

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        self._alignement_read_mode = self._alignement_tab.read_modes.currentData()
        self._alignement_exposure_time = self.alignement_exposure_time_widget.value()
        self._image_acquisition_mode = self._image_tab.acquisition_modes.currentData()
        self._image_read_mode = self._image_tab.read_modes.currentData()
        self._image_exposure_time = self.image_exposure_time_widget.value()
        self._image_readout_speed = self._image_tab.readout_speed.currentData()
        self._spectrum_acquisition_mode = self._spectrum_tab.acquisition_modes.currentData()
        self._spectrum_read_mode = self._spectrum_tab.read_modes.currentData()
        self._spectrum_exposure_time = self.spectrum_exposure_time_widget.value()
        self._spectrum_readout_speed = self._spectrum_tab.readout_speed.currentData()
        self._mw.close()

    def show(self):
        """Make window visible and put it above all other windows.
        """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

    def _activate_settings_tab(self):

        spectro_constraints = self._spectrumlogic.spectro_constraints

        self._grating_buttons = [self._settings_tab.grating_1, self._settings_tab.grating_2, self._settings_tab.grating_3]
        self._input_port_buttons = [self._settings_tab.input_front, self._settings_tab.input_side]
        self._input_slit_width = []
        self._output_port_buttons = [self._settings_tab.output_front, self._settings_tab.output_side]
        self._output_slit_width = []

        for i in range(3):
            self._grating_buttons[i].setText('{}rpm'.format(
                round(self._spectrumlogic.spectro_constraints.gratings[i].ruling/1000)))
            self._grating_buttons[i].setCheckable(True)
            self._grating_buttons[i].clicked.connect(partial(self._manage_grating_buttons, i))
            if i == self._spectrumlogic.grating_index:
                self._grating_buttons[i].setDown(True)

        self._input_ports = [port for port in spectro_constraints.ports if port.type in [PortType.INPUT_FRONT, PortType.INPUT_SIDE]]
        self._output_ports = [port for port in spectro_constraints.ports if port.type in [PortType.OUTPUT_FRONT, PortType.OUTPUT_SIDE]]

        for i in range(2):

            if i<len(self._input_ports):

                self._input_port_buttons[i].setText(self._input_ports[i].type.name[6:].lower())
                self._input_port_buttons[i].setCheckable(True)
                if self._input_ports[i].type.name == self._spectrumlogic.input_port:
                    self._input_port_buttons[i].setDown(True)

                input_widget = ScienDSpinBox()
                input_widget.setRange(self._input_ports[i].constraints.min, self._input_ports[i].constraints.max)
                input_widget.setValue(self._spectrumlogic.get_input_slit_width(self._input_ports[i].type.name))
                input_widget.setSuffix('m')
                input_widget.editingFinished.connect(partial(self._manage_slit_width, i))
                self._input_slit_width.append(input_widget)

                self._settings_tab.input_layout.addWidget(input_widget, i, 2)
                if len(self._input_ports) > 1:
                    self._input_port_buttons[i].clicked.connect(partial(self._manage_port_buttons, i))

            else:
                self._input_port_buttons[i].setEnabled(False)

            if i < len(self._output_ports):

                self._output_port_buttons[i].setText(self._output_ports[i].type.name[7:].lower())
                self._output_port_buttons[i].setCheckable(True)
                if self._output_ports[i].type.name == self._spectrumlogic.output_port:
                    self._output_port_buttons[i].setDown(True)

                output_widget = ScienDSpinBox()
                output_widget.setRange(self._output_ports[i].constraints.min, self._output_ports[i].constraints.max)
                output_widget.setValue(self._spectrumlogic.get_output_slit_width(self._output_ports[i].type.name))
                output_widget.setSuffix('m')
                output_widget.editingFinished.connect(partial(self._manage_slit_width, i+2))
                self._output_slit_width.append(output_widget)

                self._settings_tab.output_layout.addWidget(output_widget, i, 2)
                if len(self._output_ports)>1:
                    self._output_port_buttons[i].clicked.connect(partial(self._manage_port_buttons, i + 2))

            else:
                self._output_port_buttons[i].setEnabled(False)

        self._calibration_widget = ScienDSpinBox()
        self._calibration_widget.setValue(self._spectrumlogic.wavelength_calibration)
        self._calibration_widget.setSuffix('m')
        self._settings_tab.calibration_layout.addWidget(self._calibration_widget)

        for gain in self._spectrumlogic.camera_constraints.internal_gains:
            self._settings_tab.camera_gains.addItem(str(gain), gain)
            if gain == self._spectrumlogic.camera_gain:
                self._settings_tab.camera_gains.setCurrentText(str(gain))

        for trigger_mode in self._spectrumlogic.camera_constraints.trigger_modes:
            self._settings_tab.trigger_modes.addItem(trigger_mode, trigger_mode)
            if trigger_mode == self._spectrumlogic.trigger_mode:
                self._settings_tab.trigger_modes.setCurrentText(trigger_mode)

        self._temperature_widget = ScienDSpinBox()
        self._temperature_widget.setRange(-273.15, 500)
        self._temperature_widget.setValue(self._spectrumlogic.temperature_setpoint-273.15)
        self._temperature_widget.setSuffix('°C')
        self._settings_tab.camera_cooler_layout.addWidget(self._temperature_widget)

        self._settings_tab.cooler_on.clicked.connect(self._manage_cooler_button)
        if self._spectrumlogic.cooler_status:
            self._settings_tab.cooler_on.setDown(True)
            self._settings_tab.cooler_on.setText("OFF")
            self._mw.cooler_on_label.setText("Cooler ON")
        else:
            self._settings_tab.cooler_on.setText("ON")
            self._mw.cooler_on_label.setText("Cooler OFF")
        self._mw.camera_temperature.setText("{}°C".format(round(self._spectrumlogic.camera_temperature-273.15, 2)))

        self._center_wavelength_widget = ScienDSpinBox()
        self._center_wavelength_widget.setMinimum(0)
        self._center_wavelength_widget.setValue(self._spectrumlogic.center_wavelength)
        self._center_wavelength_widget.setSuffix("m")
        self._mw.center_wavelength.addWidget(self._center_wavelength_widget, 1)
        self._mw.go_to_wavelength.clicked.connect(self._manage_center_wavelength)
        self._mw.center_wavelength_current.setText("{:.2r}m".format(ScaledFloat(self._spectrumlogic.center_wavelength)))

        self._calibration_widget.editingFinished.connect(self.set_settings_params)
        self._settings_tab.camera_gains.currentTextChanged.connect(self.set_settings_params)
        self._settings_tab.trigger_modes.currentTextChanged.connect(self.set_settings_params)
        self._temperature_widget.editingFinished.connect(self.set_settings_params)
        if not self._spectrumlogic.camera_constraints.has_shutter:
            self._settings_tab.shutter_modes.setEnabled(False)
        else:
            self._settings_tab.shutter_modes.setCurrentText(self._spectrumlogic.shutter_state)
            self._settings_tab.shutter_modes.currentTextChanged.connect(self.set_settings_params)

        self._update_temperature_timer = QtCore.QTimer()
        self._update_temperature_timer.timeout.connect(self._update_temperature)
        self._update_temperature_timer.start(1000)

        self._spectrumlogic.sigUpdateSettings.connect(self._update_settings)

    def _activate_image_tab(self):

        for read_mode in self._spectrumlogic.camera_constraints.read_modes:
            if read_mode.name[:5] == "IMAGE":
                self._image_tab.read_modes.addItem(read_mode.name, read_mode.name)
                if read_mode == self._image_read_mode:
                    self._image_tab.read_modes.setCurrentText(read_mode.name)

        for acquisition_mode in AcquisitionMode.__members__:
            if acquisition_mode != "MULTI_SCAN":
                self._image_tab.acquisition_modes.addItem(acquisition_mode, acquisition_mode)
                if acquisition_mode == self._image_acquisition_mode:
                    self._image_tab.acquisition_modes.setCurrentText(acquisition_mode)

        self.image_exposure_time_widget = ScienDSpinBox()
        self.image_exposure_time_widget.setMinimum(0)
        self.image_exposure_time_widget.setValue(self._image_exposure_time)
        self.image_exposure_time_widget.setSuffix('s')
        self._image_tab.exposure_time_layout.addWidget(self.image_exposure_time_widget)

        for readout_speed in self._spectrumlogic.camera_constraints.readout_speeds:
            self._image_tab.readout_speed.addItem("{:.2r}Hz".format(ScaledFloat(readout_speed)), readout_speed)
            if readout_speed == self._image_readout_speed:
                self._image_tab.readout_speed.setCurrentText("{:.2r}Hz".format(ScaledFloat(readout_speed)))

        self._image_tab.save.clicked.connect(partial(self.save_data, 0))
        self._save_data_buttons.append(self._image_tab.save)
        self._image_tab.acquire_dark.clicked.connect(partial(self.start_dark_acquisition, 0))
        self._acquire_dark_buttons.append(self._image_tab.acquire_dark)
        self._image_tab.start_acquisition.clicked.connect(partial(self.start_acquisition, 0))
        self._start_acquisition_buttons.append(self._image_tab.start_acquisition)
        self._image_tab.stop_acquisition.clicked.connect(self.stop_acquisition)
        self._stop_acquisition_buttons.append(self._image_tab.stop_acquisition)

        self.my_colors = ColorScaleInferno()
        self._image = pg.ImageItem(image=self._image_data, axisOrder='row-major')
        self._image.setLookupTable(self.my_colors.lut)
        self._image_tab.graph.addItem(self._image)
        self._colorbar = ColorbarWidget(self._image)
        self._image_tab.colorbar.addWidget(self._colorbar)

        self.track_colors = [palette.c1, palette.c2, palette.c3, palette.c4]
        for i in range(4):
            self._track_buttons[i].setCheckable(True)
            self._track_buttons[i].clicked.connect(partial(self._manage_track_buttons, i))
            if 2*i<len(self._active_tracks):
                top_pos = self._active_tracks[2*i]
                bottom_pos = self._active_tracks[2*i+1]
            else:
                top_pos = 0
                bottom_pos = 10
            color = self.track_colors[i].getRgb()
            track_color = pg.mkBrush(color[0], color[1], color[2], 100)
            track = pg.LinearRegionItem(values=[top_pos,bottom_pos], orientation=pg.LinearRegionItem.Horizontal,
                                        brush=track_color)
            track.hide()
            self._track_selector.append(track)
            self._image_tab.graph.addItem(track)

        self._image_tab.image_advanced.setCheckable(True)
        self._image_tab.image_advanced.clicked.connect(self._manage_image_advanced_button)
        self._image_advanced_widget = pg.ROI([0,0], [100,100])
        self._image_advanced_widget.addScaleHandle((1,0), (0,1))
        self._image_advanced_widget.addScaleHandle((0,1), (1,0))
        self._image_advanced_widget.hide()
        self._image_tab.graph.addItem(self._image_advanced_widget)

        self._image_tab.horizontal_binning.setRange(1, self._spectrumlogic.camera_constraints.width-1)
        self._image_tab.vertical_binning.setRange(1, self._spectrumlogic.camera_constraints.height-1)


        self._image_tab.horizontal_binning.editingFinished.connect(self.set_image_params)
        self._image_tab.vertical_binning.editingFinished.connect(self.set_image_params)
        self._image_tab.read_modes.currentTextChanged.connect(self.set_image_params)
        self._image_tab.acquisition_modes.currentTextChanged.connect(self.set_image_params)
        self.image_exposure_time_widget.editingFinished.connect(self.set_image_params)
        self._image_tab.readout_speed.currentTextChanged.connect(self.set_image_params)

    def _activate_alignement_tab(self):

        self.time_window_widget = ScienDSpinBox()
        self.time_window_widget.setMinimum(0)
        self.time_window_widget.setValue(self._alignement_time_window)
        self.time_window_widget.setSuffix('s')
        self.time_window_widget.editingFinished.connect(self._change_time_window)
        self._alignement_tab.time_window_layout.addWidget(self.time_window_widget,1)
        self._alignement_tab.clean.clicked.connect(self._clean_time_window)

        for read_mode in self._spectrumlogic.camera_constraints.read_modes:
            self._alignement_tab.read_modes.addItem(str(read_mode.name), read_mode.name)
            if read_mode == self._alignement_read_mode:
                self._alignement_tab.read_modes.setCurrentText(str(read_mode.name))

        self.alignement_exposure_time_widget = ScienDSpinBox()
        self.alignement_exposure_time_widget.setMinimum(0)
        self.alignement_exposure_time_widget.setValue(self._alignement_exposure_time)
        self.alignement_exposure_time_widget.setSuffix('s')
        self._alignement_tab.exposure_time_layout.addWidget(self.alignement_exposure_time_widget)
        self._change_time_window()

        self._alignement_tab.start_acquisition.clicked.connect(partial(self.start_acquisition, 1))
        self._start_acquisition_buttons.append(self._alignement_tab.start_acquisition)
        self._alignement_tab.stop_acquisition.clicked.connect(self.stop_acquisition)
        self._stop_acquisition_buttons.append(self._alignement_tab.stop_acquisition)

        self._alignement_tab.graph.setLabel('left', 'photon counts', units='counts/s')
        self._alignement_tab.graph.setLabel('bottom', 'acquisition time', units='s')
        self._counter_plot = self._alignement_tab.graph.plot(self._counter_data[0], self._counter_data[1])

        self._alignement_tab.read_modes.currentTextChanged.connect(self.set_alignement_params)
        self.alignement_exposure_time_widget.editingFinished.connect(self.set_alignement_params)

    def _activate_spectrum_tab(self):

        for read_mode in self._spectrumlogic.camera_constraints.read_modes:
            if read_mode.name[:5] != "IMAGE":
                self._spectrum_tab.read_modes.addItem(str(read_mode.name), read_mode.name)
                if read_mode == self._spectrum_read_mode:
                    self._spectrum_tab.read_modes.setCurrentText(str(read_mode.name))

        for acquisition_mode in AcquisitionMode.__members__:
            self._spectrum_tab.acquisition_modes.addItem(acquisition_mode, acquisition_mode)
            if acquisition_mode == self._spectrum_acquisition_mode:
                self._spectrum_tab.acquisition_modes.setCurrentText(acquisition_mode)

        self.spectrum_exposure_time_widget = ScienDSpinBox()
        self.spectrum_exposure_time_widget.setMinimum(0)
        self.spectrum_exposure_time_widget.setValue(self._spectrum_exposure_time)
        self.spectrum_exposure_time_widget.setSuffix('s')
        self._spectrum_tab.exposure_time_layout.addWidget(self.spectrum_exposure_time_widget)

        for readout_speed in self._spectrumlogic.camera_constraints.readout_speeds:
            self._spectrum_tab.readout_speed.addItem("{:.2r}Hz".format(ScaledFloat(readout_speed)), readout_speed)
            if readout_speed == self._spectrum_readout_speed:
                self._spectrum_tab.readout_speed.setCurrentText("{:.2r}Hz".format(ScaledFloat(readout_speed)))

        self._spectrum_scan_delay_widget = ScienDSpinBox()
        self._spectrum_scan_delay_widget.setMinimum(0)
        self._spectrum_scan_delay_widget.setValue(self._spectrumlogic.scan_delay)
        self._spectrum_scan_delay_widget.setSuffix('s')
        self._spectrum_tab.scan_delay.addWidget(self._spectrum_scan_delay_widget)

        self._spectrum_tab.scan_number_spin.setValue(self._spectrumlogic.number_of_scan)

        self._spectrum_tab.save.clicked.connect(partial(self.save_data, 1))
        self._save_data_buttons.append(self._spectrum_tab.save)
        self._spectrum_tab.acquire_dark.clicked.connect(partial(self.start_dark_acquisition, 1))
        self._acquire_dark_buttons.append(self._spectrum_tab.acquire_dark)
        self._spectrum_tab.start_acquisition.clicked.connect(partial(self.start_acquisition, 2))
        self._start_acquisition_buttons.append(self._spectrum_tab.start_acquisition)
        self._spectrum_tab.stop_acquisition.clicked.connect(self.stop_acquisition)
        self._stop_acquisition_buttons.append(self._spectrum_tab.stop_acquisition)

        self._spectrum_tab.graph.setLabel('left', 'Photoluminescence', units='counts/s')
        self._spectrum_tab.graph.setLabel('bottom', 'wavelength', units='m')

        self._spectrum_tab.read_modes.currentTextChanged.connect(self.set_spectrum_params)
        self._spectrum_tab.acquisition_modes.currentTextChanged.connect(self.set_spectrum_params)
        self.spectrum_exposure_time_widget.editingFinished.connect(self.set_spectrum_params)
        self._spectrum_tab.read_modes.currentTextChanged.connect(self.set_spectrum_params)
        self._spectrum_scan_delay_widget.editingFinished.connect(self.set_spectrum_params)
        self._spectrum_tab.scan_number_spin.editingFinished.connect(self.set_spectrum_params)

    def _update_settings(self):
        """
        self._manage_grating_buttons(self._spectrumlogic.grating_index)

        if len(self._input_ports)>1:
            input_port_index = 0 if self._spectrumlogic.input_port == PortType.INPUT_FRONT else 1
            self._manage_port_buttons(input_port_index)
            self._input_slit_width[input_port_index].setValue(self._spectrumlogic.input_slit_width)
        else:
            self._input_slit_width[0].setValue(self._spectrumlogic.input_slit_width)
        if len(self._output_ports)>1:
            output_port_index = 0 if self._spectrumlogic.output_port == PortType.OUTPUT_FRONT else 1
            self._manage_port_buttons(output_port_index+2)
            self._output_slit_width[output_port_index] = self._spectrumlogic.output_slit_width
        else:
            self._output_slit_width[0] = self._spectrumlogic.output_slit_width

        self._calibration_widget.setValue(self._spectrumlogic.wavelength_calibration)
        self._settings_tab.camera_gains.setCurrentText(str(self._spectrumlogic.camera_gain))
        self._settings_tab.trigger_modes.setCurrentText(self._spectrumlogic.trigger_mode)
        self._temperature_widget.setValue(self._spectrumlogic.temperature_setpoint-273.15)

        cooler_on = not self._spectrumlogic.cooler_status
        if self._settings_tab.cooler_on.isChecked() == cooler_on:
            self._settings_tab.cooler_on.setChecked(cooler_on)
            self._settings_tab.cooler_on.setDown(cooler_on)
            self._settings_tab.cooler_on.setText("ON" if cooler_on else "OFF")
            self._mw.cooler_on_label.setText("Cooler {}".format("ON" if not cooler_on else "OFF"))
        if self._spectrumlogic.camera_constraints.has_shutter:
            self._settings_tab.shutter_modes.setCurrentText(self._spectrumlogic.shutter_state)

        self._mw.center_wavelength_current.setText("{:.2r}m".format(ScaledFloat(self._spectrumlogic.center_wavelength)))
        """
        pass

    def set_settings_params(self):

        self._spectrumlogic.wavelength_calibration = self._calibration_widget.value()
        self._spectrumlogic.camera_gain = self._settings_tab.camera_gains.currentData()
        self._spectrumlogic.trigger_mode = self._settings_tab.trigger_modes.currentData()
        self._spectrumlogic.temperature_setpoint = self._temperature_widget.value()+273.15
        self._spectrumlogic.shutter_state = self._settings_tab.shutter_modes.currentText()

    def set_image_params(self):

        self._manage_image_advanced()
        self._spectrumlogic.acquisition_mode = self._image_tab.acquisition_modes.currentData()
        self._spectrumlogic.read_mode = self._image_tab.read_modes.currentData()
        self._spectrumlogic.exposure_time = self.image_exposure_time_widget.value()
        self._spectrumlogic.readout_speed = self._image_tab.readout_speed.currentData()

        self._spectrumlogic._update_acquisition_params()
        self._image_params = self._spectrumlogic.acquisition_params

    def set_alignement_params(self):

        self._spectrumlogic.acquisition_mode = "LIVE_SCAN"
        self._spectrumlogic.read_mode = self._alignement_tab.read_modes.currentData()
        self._spectrumlogic.exposure_time = self.alignement_exposure_time_widget.value()
        self._spectrumlogic.readout_speed = max(self._spectrumlogic.camera_constraints.readout_speeds)

        self._manage_tracks()
        self._change_time_window()

    def set_spectrum_params(self):

        self._spectrumlogic.acquisition_mode = self._spectrum_tab.acquisition_modes.currentData()
        self._spectrumlogic.read_mode = self._spectrum_tab.read_modes.currentData()
        self._spectrumlogic.exposure_time = self.spectrum_exposure_time_widget.value()
        self._spectrumlogic.readout_speed = self._spectrum_tab.readout_speed.currentData()
        self._spectrumlogic.scan_delay = self._spectrum_scan_delay_widget.value()
        self._spectrumlogic.number_of_scan = self._spectrum_tab.scan_number_spin.value()

        self._manage_tracks()
        self._spectrumlogic._update_acquisition_params()
        self._spectrum_params = self._spectrumlogic.acquisition_params

    def start_dark_acquisition(self, index):

        self._manage_start_acquisition(index)

        self._spectrumlogic.acquisition_mode = "SINGLE_SCAN"
        self._spectrumlogic.shutter_state = "CLOSED"
        self._spectrumlogic.sigUpdateData.connect(partial(self._update_dark, index))

        if index == 0:
            self._spectrumlogic.read_modes = self._image_tab.read_modes.currentData()
            self._spectrumlogic.exposure_time = self.image_exposure_time_widget.value()
            self._spectrumlogic.readout_speed = self._image_tab.readout_speed.currentData()
        elif index == 1:
            self._spectrumlogic.read_modes = self._spectrum_tab.read_modes.currentData()
            self._spectrumlogic.exposure_time = self.spectrum_exposure_time_widget.value()
            self._spectrumlogic.readout_speed = self._spectrum_tab.readout_speed.currentData()

        self._spectrumlogic.start_acquisition()

    def start_acquisition(self, index):

        self._manage_start_acquisition(index)
        self._spectrumlogic.sigUpdateData.connect(partial(self._update_data, index))

        if index==0:
            self.set_image_params()
        elif index==1:
            self.set_alignement_params()
        elif index==2:
            self.set_spectrum_params()

        self._spectrumlogic.start_acquisition()

    def stop_acquisition(self):

        self._spectrumlogic.stop_acquisition()
        self._spectrumlogic.sigUpdateData.disconnect()
        self._manage_stop_acquisition()

    def _manage_grating_buttons(self, index):

        for i in range(3):
            btn = self._grating_buttons[i]
            if i == index:
                btn.setChecked(True)
                btn.setDown(True)
                self._spectrumlogic.grating_index = i
            else:
                btn.setChecked(False)
                btn.setDown(False)
        self._mw.center_wavelength_current.setText("{:.2r}m".format(ScaledFloat(self._spectrumlogic.center_wavelength)))
        self._calibration_widget.setValue(self._spectrumlogic.wavelength_calibration)

    def _manage_port_buttons(self, index):
        for i in range(2):
            if index < 2:
                btn = self._input_port_buttons[i]
                if i == index:
                    self._spectrumlogic.input_port = self._spectrumlogic.spectro_constraints.ports[i].type
                    btn.setChecked(True)
                    btn.setDown(True)
                else:
                    btn.setChecked(False)
                    btn.setDown(False)
            elif index > 1:
                btn = self._output_port_buttons[i]
                if i+2 == index:
                    self._spectrumlogic.output_port = self._spectrumlogic.spectro_constraints.ports[i+2].type
                    btn.setChecked(True)
                    btn.setDown(True)
                else:
                    btn.setChecked(False)
                    btn.setDown(False)

    def _manage_slit_width(self, index):

        if index<2:
            self._spectrumlogic.set_input_slit_width(self._input_slit_width[index].value(), self._input_ports[index].type)
        elif index>1:
            self._spectrumlogic.set_output_slit_width(self._output_slit_width[index-2].value(), self._output_ports[index-2].type)

    def _manage_cooler_button(self):
        cooler_on = not self._spectrumlogic.cooler_status
        self._spectrumlogic.cooler_status = cooler_on
        self._settings_tab.cooler_on.setChecked(cooler_on)
        self._settings_tab.cooler_on.setDown(cooler_on)
        self._settings_tab.cooler_on.setText("ON" if not cooler_on else "OFF")
        self._mw.cooler_on_label.setText("Cooler {}".format("ON" if cooler_on else "OFF"))

    def _manage_center_wavelength(self):

        self._spectrumlogic.center_wavelength = self._center_wavelength_widget.value()
        self._mw.center_wavelength_current.setText("{:.2r}m".format(ScaledFloat(self._spectrumlogic.center_wavelength)))

    def _manage_tracks(self):
        self._active_tracks = []
        for i in range(4):
            if self._track_selector[i].isVisible():
                track = list(self._track_selector[i].getRegion())
                self._active_tracks.append(track[0])
                self._active_tracks.append(track[1])
        self._spectrumlogic.active_tracks = self._active_tracks

    def _manage_image_advanced(self):

        hbin = self._image_tab.horizontal_binning.value()
        vbin = self._image_tab.vertical_binning.value()
        self._spectrumlogic.image_advanced_binning = (hbin, vbin)
        image_advanced = self._image_advanced_widget.getArraySlice(self._image_data, self._image, returnSlice=False)[0]
        self._image_advanced = list(image_advanced[1])+list(image_advanced[0])
        self._spectrumlogic.image_advanced_area = self._image_advanced

    def _manage_track_buttons(self, index):

        track_selector = self._track_selector[index]
        if track_selector.isVisible():
            track_selector.hide()
        else:
            track_selector.setVisible(True)

    def _manage_image_advanced_button(self):

        if self._image_advanced_widget.isVisible():
            self._image_advanced_widget.hide()
        else:
            self._image_advanced_widget.setVisible(True)

    def _update_temperature(self):

        self._mw.camera_temperature.setText(str(round(self._spectrumlogic.camera_temperature-273.15, 2))+"°C")

    def _manage_start_acquisition(self, index):

        for i in range(3):
            self._settings_window[i].setEnabled(False)
            self._start_acquisition_buttons[i].setEnabled(False)
            if i == index:
                self._stop_acquisition_buttons[i].setEnabled(True)
            else:
                self._stop_acquisition_buttons[i].setEnabled(False)
            if i < 2:
                self._acquire_dark_buttons[i].setEnabled(False)
                self._save_data_buttons[i].setEnabled(False)
        self._spectrum_tab.multiple_scan_settings.setEnabled(False)

    def _manage_stop_acquisition(self):

        for i in range(3):
            self._settings_window[i].setEnabled(True)
            self._start_acquisition_buttons[i].setEnabled(True)
            self._stop_acquisition_buttons[i].setEnabled(False)
            if i<2:
                self._acquire_dark_buttons[i].setEnabled(True)
                self._save_data_buttons[i].setEnabled(True)
        self._spectrum_tab.multiple_scan_settings.setEnabled(True)

    def _clean_time_window(self):

        self._counter_data = np.zeros((2, 1000))
        self._change_time_window()

    def _change_time_window(self):

        time_window = self.time_window_widget.value()
        exposure_time = self.alignement_exposure_time_widget.value()
        number_points = int(time_window / exposure_time)
        x = np.linspace(self._counter_data[0, -1] - time_window, self._counter_data[0, -1], number_points)
        if self._counter_data.shape[1] < number_points:
            y = np.zeros(number_points)
            y[-self._counter_data.shape[1]:] = self._counter_data[1]
        else:
            y = self._counter_data[1,-number_points:]
        self._counter_data = np.array([x, y])
        self._alignement_tab.graph.setRange(xRange=(x[-1]-self.time_window_widget.value(), x[-1]))

    def _update_data(self, index):

        data = np.array(self._spectrumlogic.acquired_data)

        if index == 0:

            if self._image_dark.shape == data.shape[:-2]:
                self._image_data = data - self._image_dark
            else:
                self._image_data = data
                self._image_tab.dark_acquired_msg.setText("No Dark Acquired")

            if self._spectrumlogic.read_mode == "IMAGE_ADVANCED":
                self._image.setRect(self._image_advanced_widget.parentBounds())
            else:
                width = self._spectrumlogic.camera_constraints.width
                height = self._spectrumlogic.camera_constraints.height
                self._image.setRect(QtCore.QRect(0,0,width,height))
            self._image.setImage(self._image_data)

        elif index == 1:

            counts = data.sum()
            x = self._counter_data[0]+self._spectrumlogic.exposure_time
            y = np.append(self._counter_data[1][1:], counts)
            self._counter_data = np.array([x, y])
            self._alignement_tab.graph.setRange(xRange=(x[-1]-self.time_window_widget.value(), x[-1]))
            self._counter_plot.setData(x, y)

        elif index == 2:

            x = self._spectrumlogic.wavelength_spectrum
            if self._image_dark.shape == data.shape[:-1]:
                y = data - self._spectrum_dark
            else:
                y = data
                self._spectrum_tab.dark_acquired_msg.setText("No Dark Acquired")

            if self._spectrumlogic.acquisition_mode == "MULTI_SCAN":
                self._spectrum_data = np.array([[x, scan] for scan in y])
                self._spectrum_tab.graph.clear()
                if self._spectrumlogic.read_mode == "MULTIPLE_TRACKS":
                    i = 0
                    for track in y[-1]:
                        self._spectrum_tab.graph.plot(x, track, pen=self.track_colors[i])
                        i += 1
                else:
                    self._spectrum_tab.graph.plot(x, y[-1], pen=self.track_colors[0])
            else:
                self._spectrum_data = np.array([x, y])
                self._spectrum_tab.graph.clear()
                if self._spectrumlogic.read_mode == "MULTIPLE_TRACKS":
                    i = 0
                    for track in y:
                        self._spectrum_tab.graph.plot(x, track, pen=self.track_colors[i])
                        i += 1
                else:
                    self._spectrum_tab.graph.plot(x, y, pen=self.track_colors[0])

        if not self._spectrumlogic.module_state() == 'locked':
            self._spectrumlogic.sigUpdateData.disconnect()
            self._manage_stop_acquisition()

    def _update_dark(self, index):

        dark = np.array(self._spectrumlogic.acquired_data)

        if index == 0:
            self._image_dark = dark
            self._image_tab.dark_acquired_msg.setText("Dark Acquired")
        elif index == 1:
            self._spectrum_dark = dark
            self._spectrum_tab.dark_acquired_msg.setText("Dark Acquired")

        self._spectrumlogic.sigUpdateData.disconnect()
        self._manage_stop_acquisition()
        self._spectrumlogic.shutter_state = self._settings_tab.shutter_modes.currentText()

    def save_data(self, index):

        filepath = self.savelogic().get_path_for_module(module_name='spectrometer')

        if index==0:
            data = {'data': np.array(self._image_data).flatten()}
            self.savelogic().save_data(data, filepath=filepath, parameters=self._image_params)
        elif index==1:
            data = {'data': np.array(self._spectrum_data).flatten()}
            self.savelogic().save_data(data, filepath=filepath, parameters=self._spectrum_params)