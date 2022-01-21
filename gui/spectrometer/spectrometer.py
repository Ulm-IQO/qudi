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
from PyQt5.Qt import QRectF, QPoint

from qtpy import QtCore
from qtpy import QtWidgets
from qtpy import uic

from gui.gui_components.colorbar.colorbar import ColorbarWidget


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self):
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_mainwindow.ui')
        super().__init__()
        uic.loadUi(ui_file, self)
        self.show()


class SettingsTab(QtWidgets.QWidget):

    def __init__(self):
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_settings_tab.ui')
        super().__init__()
        uic.loadUi(ui_file, self)
        self.show()


class ImageTab(QtWidgets.QWidget):

    def __init__(self):
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_image_tab.ui')
        super().__init__()
        uic.loadUi(ui_file, self)
        self.show()

class AlignmentTab(QtWidgets.QWidget):

    def __init__(self):
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_alignment_tab.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)
        self.show()


class SpectrumTab(QtWidgets.QWidget):
    def __init__(self):
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_spectrum_tab.ui')
        super().__init__()
        uic.loadUi(ui_file, self)
        self.show()


class Main(GUIBase):
    """ GUI module to interface a spectrometer """

    spectrumlogic = Connector(interface='SpectrumLogic')
    savelogic = Connector(interface='SaveLogic')

    _cooler_temperature_unit = ConfigOption('cooler_temperature_unit')

    _alignment_read_mode = StatusVar('alignment_read_mode', 'FVB')
    _alignment_exposure_time = StatusVar('alignment_exposure_time', 0)
    _alignment_time_window = StatusVar('alignment_time_window', 60)

    _image_read_mode = StatusVar('image_read_mode', 'IMAGE_ADVANCED')
    _image_acquisition_mode = StatusVar('image_acquisition_mode', 'LIVE')
    _image_exposure_time = StatusVar('image_exposure_time', None)
    _image_readout_speed = StatusVar('image_readout_speed', None)

    _spectrum_read_mode = StatusVar('spectrum_read_mode', 'MULTIPLE_TRACKS')
    _spectrum_acquisition_mode = StatusVar('spectrum_acquisition_mode', 'SINGLE_SCAN')
    _spectrum_exposure_time = StatusVar('spectrum_exposure_time', None)
    _spectrum_readout_speed = StatusVar('spectrum_readout_speed', None)

    _image_data = StatusVar('image_data', None)
    _image_background = StatusVar('image_background', None)
    _image_params = StatusVar('image_params', None)
    _counter_data = StatusVar('counter_data', np.zeros((2, 10)))
    _spectrum_data = StatusVar('spectrum_data', None)
    _spectrum_background = StatusVar('spectrum_background', None)
    _spectrum_params = StatusVar('spectrum_params', None)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Definition and initialisation of the GUI. """

        # setting up the window
        self._mw = MainWindow()
        self._settings_tab = SettingsTab()
        self._mw.tab.addTab(self._settings_tab, "Settings")

        self._image_tab = ImageTab()
        self._mw.tab.addTab(self._image_tab, "Image")

        self._alignment_tab = AlignmentTab()
        self._mw.tab.addTab(self._alignment_tab, "Alignment")

        self._spectrum_tab = SpectrumTab()
        self._mw.tab.addTab(self._spectrum_tab, "Spectrum")

        self._start_acquisition_buttons = []
        self._stop_acquisition_buttons = []
        self._save_data_buttons = []

        self._track_buttons = [self._image_tab.track1, self._image_tab.track2,
                               self._image_tab.track3, self._image_tab.track4]
        self._track_selector = []

        if not self._image_exposure_time:
            self._image_exposure_time = self.spectrumlogic().exposure_time
        if not self._image_readout_speed:
            self._image_readout_speed = self.spectrumlogic().readout_speed
        if not self._alignment_exposure_time:
            self._alignment_exposure_time = self.spectrumlogic().exposure_time
        if not self._spectrum_exposure_time:
            self._spectrum_exposure_time = self.spectrumlogic().exposure_time
        if not self._spectrum_readout_speed:
            self._spectrum_readout_speed = self.spectrumlogic().readout_speed

        self._activate_settings_tab()
        self._activate_image_tab()
        self._activate_alignment_tab()
        self._activate_spectrum_tab()
        self._settings_window = [self._image_tab.image_settings, self._alignment_tab.counter_settings,
                    self._spectrum_tab.spectrum_settings]

        self._manage_stop_acquisition()

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        self._alignment_read_mode = self._alignment_tab.read_modes.currentData()
        self._alignment_exposure_time = self.alignment_exposure_time_widget.value()
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
        """ Make window visible and put it above all other windows """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

    def _activate_settings_tab(self):
        """ Initialization method for the setting tab """

        spectro_constraints = self.spectrumlogic().spectro_constraints

        self._grating_buttons = [self._settings_tab.grating_1, self._settings_tab.grating_2, self._settings_tab.grating_3]
        self._input_port_buttons = [self._settings_tab.input_front, self._settings_tab.input_side]
        self._input_slit_width = []
        self._output_port_buttons = [self._settings_tab.output_front, self._settings_tab.output_side]
        self._output_slit_width = []

        for i in range(3):
            if i < len(self.spectrumlogic().spectro_constraints.gratings):
                self._grating_buttons[i].setText('{}rpm'.format(
                    round(self.spectrumlogic().spectro_constraints.gratings[i].ruling/1000)))
                self._grating_buttons[i].setCheckable(True)
                self._grating_buttons[i].clicked.connect(partial(self._manage_grating_buttons, i))
                if i == self.spectrumlogic().grating:
                    self._grating_buttons[i].setDown(True)
            else:
                self._grating_buttons[i].setVisible(False)

        self._input_ports = [port for port in spectro_constraints.ports if port.type in [PortType.INPUT_FRONT, PortType.INPUT_SIDE]]
        self._output_ports = [port for port in spectro_constraints.ports if port.type in [PortType.OUTPUT_FRONT, PortType.OUTPUT_SIDE]]

        for i in range(2):

            if i<len(self._input_ports):

                self._input_port_buttons[i].setText(self._input_ports[i].type.name[6:].lower())
                self._input_port_buttons[i].setCheckable(True)
                if self._input_ports[i].type.name == self.spectrumlogic().input_port:
                    self._input_port_buttons[i].setDown(True)

                input_widget = ScienDSpinBox()
                input_widget.setRange(self._input_ports[i].constraints.min, self._input_ports[i].constraints.max)
                input_widget.setValue(self.spectrumlogic().get_input_slit_width(self._input_ports[i].type.name))
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
                if self._output_ports[i].type.name == self.spectrumlogic().output_port:
                    self._output_port_buttons[i].setDown(True)

                output_widget = ScienDSpinBox()
                output_widget.setRange(self._output_ports[i].constraints.min, self._output_ports[i].constraints.max)
                output_widget.setValue(self.spectrumlogic().get_output_slit_width(self._output_ports[i].type.name))
                output_widget.setSuffix('m')
                output_widget.editingFinished.connect(partial(self._manage_slit_width, i+2))
                self._output_slit_width.append(output_widget)

                self._settings_tab.output_layout.addWidget(output_widget, i, 2)
                if len(self._output_ports)>1:
                    self._output_port_buttons[i].clicked.connect(partial(self._manage_port_buttons, i + 2))

            else:
                self._output_port_buttons[i].setEnabled(False)

        self._calibration_widget = ScienDSpinBox()
        self._calibration_widget.setValue(self.spectrumlogic().wavelength_calibration)
        self._calibration_widget.setSuffix('m')
        self._settings_tab.calibration_layout.addWidget(self._calibration_widget)

        for gain in self.spectrumlogic().camera_constraints.internal_gains:
            self._settings_tab.camera_gains.addItem(str(gain), gain)
            if gain == self.spectrumlogic().camera_gain:
                self._settings_tab.camera_gains.setCurrentText(str(gain))

        for trigger_mode in self.spectrumlogic().camera_constraints.trigger_modes:
            self._settings_tab.trigger_modes.addItem(trigger_mode, trigger_mode)
            if trigger_mode == self.spectrumlogic().trigger_mode:
                self._settings_tab.trigger_modes.setCurrentText(trigger_mode)

        self._center_wavelength_widget = ScienDSpinBox()
        self._center_wavelength_widget.setMinimum(0)
        self._center_wavelength_widget.setValue(self.spectrumlogic().center_wavelength)
        self._center_wavelength_widget.setSuffix("m")
        self._mw.center_wavelength.addWidget(self._center_wavelength_widget, 1)
        self._mw.go_to_wavelength.clicked.connect(self._manage_center_wavelength)
        self._mw.center_wavelength_current.setText("{:.2r}m".format(ScaledFloat(self.spectrumlogic().center_wavelength)))

        self._calibration_widget.editingFinished.connect(self.set_settings_params)
        self._settings_tab.camera_gains.currentTextChanged.connect(self.set_settings_params)
        self._settings_tab.trigger_modes.currentTextChanged.connect(self.set_settings_params)

        if not self.spectrumlogic().camera_constraints.has_shutter:
            self._settings_tab.shutter_modes.setEnabled(False)
        else:
            self._settings_tab.shutter_modes.setCurrentText(self.spectrumlogic().shutter_state)
            self._settings_tab.shutter_modes.currentTextChanged.connect(self.set_settings_params)

        if self.spectrumlogic().camera_constraints.has_cooler:

            self._settings_tab.cooler_on.clicked.connect(self._manage_cooler_button)
            if self.spectrumlogic().cooler_status:
                self._settings_tab.cooler_on.setDown(True)
                self._settings_tab.cooler_on.setText("OFF")
                self._mw.cooler_on_label.setText("Cooler ON")
            else:
                self._settings_tab.cooler_on.setText("ON")
                self._mw.cooler_on_label.setText("Cooler OFF")

            self._temperature_widget = ScienDSpinBox()
            self._temperature_widget.setRange(-273.15, 500)
            self._temperature_widget.setValue(self.spectrumlogic().temperature_setpoint - 273.15)
            self._temperature_widget.setSuffix('°C')
            self._settings_tab.camera_cooler_layout.addWidget(self._temperature_widget)
            self._temperature_widget.editingFinished.connect(self.set_settings_params)

            self._mw.camera_temperature.setText(
                "{}°C".format(round(self.spectrumlogic().camera_temperature - 273.15, 2)))
            self._update_temperature_timer = QtCore.QTimer()
            self._update_temperature_timer.timeout.connect(self._update_temperature)
            self._update_temperature_timer.start(1000)

        else:

            self._settings_tab.cooler_on.setVisible(False)
            self._mw.camera_temperature.setVisible(False)
            self._mw.cooler_on_label.setVisible(False)

        self.spectrumlogic().sigUpdateSettings.connect(self._update_settings)

    def _activate_image_tab(self):
        """ Initialization method for the image tab """

        camera_width = self.spectrumlogic().camera_constraints.width
        camera_height = self.spectrumlogic().camera_constraints.height

        for read_mode in self.spectrumlogic().camera_constraints.read_modes:
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

        for readout_speed in self.spectrumlogic().camera_constraints.readout_speeds:
            self._image_tab.readout_speed.addItem("{:.2r}Hz".format(ScaledFloat(readout_speed)), readout_speed)
            if readout_speed == self._image_readout_speed:
                self._image_tab.readout_speed.setCurrentText("{:.2r}Hz".format(ScaledFloat(readout_speed)))

        self._image_tab.save.clicked.connect(self.save_image_data)
        self._save_data_buttons.append(self._image_tab.save)
        self._image_tab.upload_background.clicked.connect(self.upload_image_background)
        self._image_tab.clean_background.clicked.connect(self.clean_image_background)
        self._image_tab.start_acquisition.clicked.connect(partial(self.start_acquisition, 0))
        self._start_acquisition_buttons.append(self._image_tab.start_acquisition)
        self._image_tab.stop_acquisition.clicked.connect(self.stop_acquisition)
        self._stop_acquisition_buttons.append(self._image_tab.stop_acquisition)

        self.my_colors = ColorScaleInferno()
        if self._image_data:
            self._image = pg.ImageItem(image=self._image_data['data'], axisOrder='row-major')
        else:
            self._image = pg.ImageItem(image=np.zeros((10,10)), axisOrder='row-major')
        self._image.setLookupTable(self.my_colors.lut)
        self._image_tab.graph.addItem(self._image)
        self._colorbar = ColorbarWidget(self._image)
        self._image_tab.colorbar.addWidget(self._colorbar)

        self.track_colors = np.array([palette.c5, palette.c2, palette.c6, palette.c4])
        self.plot_colors = self.track_colors
        height = self.spectrumlogic().camera_constraints.height
        for i in range(4):
            self._track_buttons[i].setCheckable(True)
            self._track_buttons[i].clicked.connect(partial(self._manage_track_buttons, i))
            tracks = self.spectrumlogic().active_tracks
            if 2*i<len(tracks):
                top_pos = tracks[2*i]
                bottom_pos = tracks[2*i+1]
            else:
                top_pos = 0
                bottom_pos = 10
            color = self.track_colors[i].getRgb()
            track_color = pg.mkBrush(color[0], color[1], color[2], 100)
            track = pg.LinearRegionItem(values=[top_pos, bottom_pos], orientation=pg.LinearRegionItem.Horizontal,
                                        brush=track_color)
            track.setBounds([0, height])
            track.hide()
            self._track_selector.append(track)
            self._image_tab.graph.addItem(track)

        self._image_tab.image_advanced.setCheckable(True)
        self._image_tab.image_advanced.clicked.connect(self._manage_image_advanced_button)
        self._image_advanced_widget = pg.ROI([0,0], [camera_width, camera_height],
                                             maxBounds=QRectF(QPoint(0, 0), QPoint(camera_width, camera_height)))
        self._image_advanced_widget.addScaleHandle((1,0), (0,1))
        self._image_advanced_widget.addScaleHandle((0,1), (1,0))
        self._image_advanced_widget.hide()
        self._image_tab.graph.addItem(self._image_advanced_widget)

        self._image_tab.horizontal_binning.setRange(1, camera_width-1)
        self._image_tab.vertical_binning.setRange(1, camera_height-1)

        self._image_tab.horizontal_binning.editingFinished.connect(self.set_image_params)
        self._image_tab.vertical_binning.editingFinished.connect(self.set_image_params)
        self._image_tab.read_modes.currentTextChanged.connect(self.set_image_params)
        self._image_tab.acquisition_modes.currentTextChanged.connect(self.set_image_params)
        self.image_exposure_time_widget.editingFinished.connect(self.set_image_params)
        self._image_tab.readout_speed.currentTextChanged.connect(self.set_image_params)

        self._image_background_dialog = QtWidgets.QFileDialog()
        if self._image_background:
            self._image_tab.background_msg.setText("Background Loaded")
        else:
            self._image_tab.background_msg.setText("No Background")

    def _activate_alignment_tab(self):

        self.time_window_widget = ScienDSpinBox()
        self.time_window_widget.setMinimum(0)
        self.time_window_widget.setValue(self._alignment_time_window)
        self.time_window_widget.setSuffix('s')
        self.time_window_widget.editingFinished.connect(self._change_time_window)
        self._alignment_tab.time_window_layout.addWidget(self.time_window_widget,1)
        self._alignment_tab.clean.clicked.connect(self._clean_time_window)

        for read_mode in self.spectrumlogic().camera_constraints.read_modes:
            self._alignment_tab.read_modes.addItem(str(read_mode.name), read_mode.name)
            if read_mode == self._alignment_read_mode:
                self._alignment_tab.read_modes.setCurrentText(str(read_mode.name))

        self.alignment_exposure_time_widget = ScienDSpinBox()
        self.alignment_exposure_time_widget.setMinimum(0)
        self.alignment_exposure_time_widget.setValue(self._alignment_exposure_time)
        self.alignment_exposure_time_widget.setSuffix('s')
        self._alignment_tab.exposure_time_layout.addWidget(self.alignment_exposure_time_widget)

        self._alignment_tab.start_acquisition.clicked.connect(partial(self.start_acquisition, 1))
        self._start_acquisition_buttons.append(self._alignment_tab.start_acquisition)
        self._alignment_tab.stop_acquisition.clicked.connect(self.stop_acquisition)
        self._stop_acquisition_buttons.append(self._alignment_tab.stop_acquisition)

        self._alignment_tab.graph.setLabel('left', 'photon counts', units='counts/s')
        self._alignment_tab.graph.setLabel('bottom', 'acquisition time', units='s')
        self._counter_plot = self._alignment_tab.graph.plot(self._counter_data[0], self._counter_data[1])

        self._alignment_tab.read_modes.currentTextChanged.connect(self.set_alignment_params)
        self.alignment_exposure_time_widget.editingFinished.connect(self.set_alignment_params)

    def _activate_spectrum_tab(self):
        """ Initialization method for the spectrum tab """

        for read_mode in self.spectrumlogic().camera_constraints.read_modes:
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

        for readout_speed in self.spectrumlogic().camera_constraints.readout_speeds:
            self._spectrum_tab.readout_speed.addItem("{:.2r}Hz".format(ScaledFloat(readout_speed)), readout_speed)
            if readout_speed == self._spectrum_readout_speed:
                self._spectrum_tab.readout_speed.setCurrentText("{:.2r}Hz".format(ScaledFloat(readout_speed)))

        self._spectrum_scan_delay_widget = ScienDSpinBox()
        self._spectrum_scan_delay_widget.setMinimum(0)
        self._spectrum_scan_delay_widget.setValue(self.spectrumlogic().scan_delay)
        self._spectrum_scan_delay_widget.setSuffix('s')
        self._spectrum_tab.scan_delay.addWidget(self._spectrum_scan_delay_widget)

        self._spectrum_scan_wavelength_step_widget = ScienDSpinBox()
        self._spectrum_scan_wavelength_step_widget.setValue(self.spectrumlogic().scan_wavelength_step)
        self._spectrum_scan_wavelength_step_widget.setSuffix('m')
        self._spectrum_tab.scan_wavelength_step.addWidget(self._spectrum_scan_wavelength_step_widget)

        self._spectrum_tab.scan_number_spin.setValue(self.spectrumlogic().number_of_scan)

        self._spectrum_tab.save.clicked.connect(self.save_spectrum_data)
        self._save_data_buttons.append(self._spectrum_tab.save)
        self._spectrum_tab.upload_background.clicked.connect(self.upload_spectrum_background)
        self._spectrum_tab.clean_background.clicked.connect(self.clean_spectrum_background)
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
        self._spectrum_scan_wavelength_step_widget.editingFinished.connect(self.set_spectrum_params)

        self._spectrum_background_dialog = QtWidgets.QFileDialog()
        if self._spectrum_background:
            self._spectrum_tab.background_msg.setText("Background Loaded")
        else:
            self._spectrum_tab.background_msg.setText("No Background")

    def _update_settings(self):

        self._manage_grating_buttons(self.spectrumlogic()._grating)

        if len(self._input_ports)>1:
            input_port_index = 0 if self.spectrumlogic()._input_port == PortType.INPUT_FRONT else 1
            self._manage_port_buttons(input_port_index)
            self._input_slit_width[input_port_index].setValue(self.spectrumlogic()._input_slit_width[input_port_index])
        else:
            self._input_slit_width[0].setValue(self.spectrumlogic()._input_slit_width[0])
        if len(self._output_ports)>1:
            output_port_index = 0 if self.spectrumlogic()._output_port == PortType.OUTPUT_FRONT else 1
            self._manage_port_buttons(output_port_index+2)
            self._output_slit_width[output_port_index].setValue(self.spectrumlogic()._output_slit_width[output_port_index])
        else:
            self._output_slit_width[0].setValue(self.spectrumlogic()._output_slit_width[0])

        self._calibration_widget.setValue(self.spectrumlogic().wavelength_calibration)
        self._settings_tab.camera_gains.setCurrentText(str(int(self.spectrumlogic()._camera_gain)))
        self._settings_tab.trigger_modes.setCurrentText(self.spectrumlogic()._trigger_mode)
        if self.spectrumlogic().camera_constraints.has_cooler:
            self._temperature_widget.setValue(self.spectrumlogic()._temperature_setpoint-273.15)

            cooler_on = self.spectrumlogic()._cooler_status
            if self._settings_tab.cooler_on.isDown() != cooler_on:
                self._settings_tab.cooler_on.setChecked(cooler_on)
                self._settings_tab.cooler_on.setDown(cooler_on)
                self._settings_tab.cooler_on.setText("ON" if not cooler_on else "OFF")
                self._mw.cooler_on_label.setText("Cooler {}".format("ON" if cooler_on else "OFF"))

        #if self.spectrumlogic().camera_constraints.has_shutter:
        #    self._settings_tab.shutter_modes.setCurrentText(self.spectrumlogic()._shutter_state)

        self._mw.center_wavelength_current.setText("{:.2r}m".format(ScaledFloat(self.spectrumlogic()._center_wavelength)))

    def set_settings_params(self):

        if self.spectrumlogic().module_state() == 'locked':
            return

        self.spectrumlogic().wavelength_calibration = self._calibration_widget.value()
        self.spectrumlogic().camera_gain = self._settings_tab.camera_gains.currentData()
        self.spectrumlogic().trigger_mode = self._settings_tab.trigger_modes.currentData()
        if self.spectrumlogic().camera_constraints.has_cooler:
            self.spectrumlogic().temperature_setpoint = self._temperature_widget.value()+273.15
        self.spectrumlogic().shutter_state = self._settings_tab.shutter_modes.currentText()

        self._mw.center_wavelength_current.setText("{:.2r}m".format(ScaledFloat(self.spectrumlogic().center_wavelength)))

    def set_image_params(self):

        if self.spectrumlogic().module_state() == 'locked':
            return

        self._manage_image_advanced()
        self.spectrumlogic().acquisition_mode = self._image_tab.acquisition_modes.currentData()
        self.spectrumlogic().read_mode = self._image_tab.read_modes.currentData()
        self.spectrumlogic().exposure_time = self.image_exposure_time_widget.value()
        self.spectrumlogic().readout_speed = self._image_tab.readout_speed.currentData()

        self.spectrumlogic()._update_acquisition_params()
        self._image_params = dict(self.spectrumlogic().acquisition_params)

    def set_alignment_params(self):

        if self.spectrumlogic().module_state() == 'locked':
            return

        self.spectrumlogic().acquisition_mode = "LIVE_SCAN"
        self.spectrumlogic().read_mode = self._alignment_tab.read_modes.currentData()
        self.spectrumlogic().exposure_time = self.alignment_exposure_time_widget.value()
        self.spectrumlogic().readout_speed = max(self.spectrumlogic().camera_constraints.readout_speeds)

        self._manage_tracks()

    def set_spectrum_params(self):

        if self.spectrumlogic().module_state() == 'locked':
            return

        self._manage_tracks()
        self.spectrumlogic().acquisition_mode = self._spectrum_tab.acquisition_modes.currentData()
        self.spectrumlogic().read_mode = self._spectrum_tab.read_modes.currentData()
        self.spectrumlogic().exposure_time = self.spectrum_exposure_time_widget.value()
        self.spectrumlogic().readout_speed = self._spectrum_tab.readout_speed.currentData()
        self.spectrumlogic().scan_delay = self._spectrum_scan_delay_widget.value()
        self.spectrumlogic().number_of_scan = self._spectrum_tab.scan_number_spin.value()
        self.spectrumlogic().scan_wavelength_step = self._spectrum_scan_wavelength_step_widget.value()

        self.spectrumlogic()._update_acquisition_params()
        self._spectrum_params = dict(self.spectrumlogic().acquisition_params)

    def upload_image_background(self):
        filename = self._image_background_dialog.getOpenFileName()[0]
        try:
            data = np.loadtxt(r"{}".format(filename)).T
            self._image_background = {"wavelength":data[0],
                                      "data":data[1].reshape()}
            self._image_tab.background_msg.setText("Background Loaded")
        except:
            pass

    def clean_image_background(self):
        self._image_background = None
        self._image_tab.background_msg.setText("No Background")

    def upload_spectrum_background(self):
        filename = self._spectrum_background_dialog.getOpenFileName()[0]
        try:
            data = np.loadtxt(r"{}".format(filename)).T
            self._spectrum_background = {"wavelength":data[0],
                                        "data":data[1]}
            self._spectrum_tab.background_msg.setText("Background Loaded")
        except:
            pass

    def clean_spectrum_background(self):
        self._spectrum_background = None
        self._spectrum_tab.background_msg.setText("No Background")

    def start_acquisition(self, tab_index):

        self._manage_start_acquisition(tab_index)
        self.spectrumlogic().sigUpdateData.connect(partial(self._update_data, tab_index))

        if tab_index==0:
            self.set_image_params()
        elif tab_index==1:
            self.set_alignment_params()
        elif tab_index==2:
            self.set_spectrum_params()

        self.spectrumlogic().start_acquisition()

    def stop_acquisition(self):

        self.spectrumlogic().stop_acquisition()
        self.spectrumlogic().sigUpdateData.disconnect()
        self._manage_stop_acquisition()

    def save_image_data(self):

        filepath = self.savelogic().get_path_for_module(module_name='spectrometer')
        self.spectrumlogic().savelogic().save_data({"wavelength":self._image_data['wavelength'].flatten(),
                                   "data":self._image_data['data'].flatten()}, filepath=filepath, parameters=self._image_params)

    def save_spectrum_data(self):

        filepath = self.savelogic().get_path_for_module(module_name='spectrometer')
        self.spectrumlogic().savelogic().save_data({"wavelength":self._spectrum_data['wavelength'].flatten(),
                                   "data":self._spectrum_data['data'].flatten()}, filepath=filepath, parameters=self._spectrum_params)

    def _manage_grating_buttons(self, tab_index):

        for i in range(3):
            btn = self._grating_buttons[i]
            if i == tab_index:
                btn.setChecked(True)
                btn.setDown(True)
                self.spectrumlogic().grating = i
            else:
                btn.setChecked(False)
                btn.setDown(False)
        self._mw.center_wavelength_current.setText("{:.2r}m".format(ScaledFloat(self.spectrumlogic().center_wavelength)))
        self._calibration_widget.setValue(self.spectrumlogic().wavelength_calibration)

    def _manage_port_buttons(self, tab_index):
        for i in range(2):
            if tab_index < 2:
                btn = self._input_port_buttons[i]
                if i == tab_index:
                    self.spectrumlogic().input_port = self.spectrumlogic().spectro_constraints.ports[i].type
                    btn.setChecked(True)
                    btn.setDown(True)
                else:
                    btn.setChecked(False)
                    btn.setDown(False)
            elif tab_index > 1:
                btn = self._output_port_buttons[i]
                if i+2 == tab_index:
                    self.spectrumlogic().output_port = self.spectrumlogic().spectro_constraints.ports[i+2].type
                    btn.setChecked(True)
                    btn.setDown(True)
                else:
                    btn.setChecked(False)
                    btn.setDown(False)

    def _manage_slit_width(self, tab_index):

        if tab_index < 2:
            self.spectrumlogic().set_input_slit_width(self._input_slit_width[tab_index].value(), self._input_ports[tab_index].type)
        elif tab_index > 1:
            self.spectrumlogic().set_output_slit_width(self._output_slit_width[tab_index-2].value(), self._output_ports[tab_index-2].type)

    def _manage_cooler_button(self):
        cooler_on = not self.spectrumlogic().cooler_status
        self.spectrumlogic().cooler_status = cooler_on
        self._settings_tab.cooler_on.setChecked(cooler_on)
        self._settings_tab.cooler_on.setDown(cooler_on)
        self._settings_tab.cooler_on.setText("ON" if not cooler_on else "OFF")
        self._mw.cooler_on_label.setText("Cooler {}".format("ON" if cooler_on else "OFF"))

    def _manage_center_wavelength(self):

        self.spectrumlogic().center_wavelength = self._center_wavelength_widget.value()
        self._mw.center_wavelength_current.setText("{:.2r}m".format(ScaledFloat(self.spectrumlogic().center_wavelength)))

    def _manage_tracks(self):

        active_tracks = []
        for i in range(4):
            if self._track_selector[i].isVisible():
                track = self._track_selector[i].getRegion()
                active_tracks.append(int(track[0]))
                active_tracks.append(int(track[1]))
        active_tracks = np.array(active_tracks)
        self.plot_colors[np.argsort(active_tracks[::2])]
        if np.any(self.spectrumlogic().active_tracks != active_tracks):
            self.spectrumlogic().active_tracks = active_tracks

    def _manage_image_advanced(self):

        hbin = self._image_tab.horizontal_binning.value()
        vbin = self._image_tab.vertical_binning.value()
        self.spectrumlogic().image_advanced_binning = [hbin, vbin]

        roi_size = list(self._image_advanced_widget.size())
        roi_origin = list(self._image_advanced_widget.pos())
        image_advanced = [int(roi_origin[0]), int(roi_origin[0]+roi_size[0]), int(roi_origin[1]), int(roi_origin[1]+roi_size[1])]
        self.spectrumlogic().image_advanced_area = image_advanced

    def _manage_track_buttons(self, tab_index):

        track_selector = self._track_selector[tab_index]
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

        self._mw.camera_temperature.setText(str(round(self.spectrumlogic().camera_temperature-273.15, 2))+"°C")

    def _manage_start_acquisition(self, tab_index):

        self._spectrum_tab.upload_background.setEnabled(False)
        self._image_tab.upload_background.setEnabled(False)
        self._spectrum_tab.clean_background.setEnabled(False)
        self._image_tab.clean_background.setEnabled(False)
        for i in range(3):
            self._settings_window[i].setEnabled(False)
            self._start_acquisition_buttons[i].setEnabled(False)
            if i == tab_index:
                self._stop_acquisition_buttons[i].setEnabled(True)
            else:
                self._stop_acquisition_buttons[i].setEnabled(False)
            if i < 2:
                self._save_data_buttons[i].setEnabled(False)
        self._spectrum_tab.multiple_scan_settings.setEnabled(False)

    def _manage_stop_acquisition(self):

        self._spectrum_tab.upload_background.setEnabled(True)
        self._image_tab.upload_background.setEnabled(True)
        self._spectrum_tab.clean_background.setEnabled(True)
        self._image_tab.clean_background.setEnabled(True)
        for i in range(3):
            self._settings_window[i].setEnabled(True)
            self._start_acquisition_buttons[i].setEnabled(True)
            self._stop_acquisition_buttons[i].setEnabled(False)
            if i < 2:
                self._save_data_buttons[i].setEnabled(True)
        self._spectrum_tab.multiple_scan_settings.setEnabled(True)

    def _clean_time_window(self):

        time_window = self.time_window_widget.value()
        exposure_time = self.alignment_exposure_time_widget.value()
        number_points = int(time_window / exposure_time)
        self._counter_data = np.zeros((2, number_points))
        self._counter_plot.setData([])

    def _change_time_window(self):

        time_window = self.time_window_widget.value()
        exposure_time = self.alignment_exposure_time_widget.value()
        number_points = int(time_window / exposure_time)
        x = np.linspace(self._counter_data[0, -1] - time_window, self._counter_data[0, -1], number_points)
        if self._counter_data.shape[1] < number_points:
            y = np.empty(number_points)
            y[-self._counter_data.shape[1]:] = self._counter_data[1]
        else:
            y = self._counter_data[1, -number_points:]
        self._counter_data = np.array([x, y])
        self._alignment_tab.graph.setRange(xRange=(x[-1]-self.time_window_widget.value(), x[-1]))

    def _update_data(self, tab_index):

        data = self.spectrumlogic().acquired_data
        wavelength = self.spectrumlogic().acquired_wavelength

        if tab_index == 0:

            if self._image_background:
                if self._image_background['data'].shape == data.shape:
                    data = data - self._image_background['data']
                else:
                    self._image_tab.background_msg.setText("Wrong Background Size")

            print(data)
            data = data/self._image_params['exposure_time']

            self._image_data = {"wavelength":wavelength,
                                "data":data}

            self._image.setImage(data)
            self._colorbar.refresh_image()

            if self.spectrumlogic().read_mode == "IMAGE_ADVANCED":
                rectf = self._image_advanced_widget.parentBounds()
                self._image.setRect(rectf)
            else:
                width = self.spectrumlogic().camera_constraints.width
                height = self.spectrumlogic().camera_constraints.height
                self._image.setRect(QtCore.QRect(0, 0, width, height))

        elif tab_index == 1:

            counts = data.mean()
            x = self._counter_data[0]+self.spectrumlogic().exposure_time
            y = np.append(self._counter_data[1][1:], counts)
            self._counter_data = np.array([x, y])
            self._alignment_tab.graph.setRange(xRange=(x[-1]-self.time_window_widget.value(), x[-1]))
            self._counter_plot.setData(x, y)

        elif tab_index == 2:

            if self._spectrum_background:
                if self._spectrum_background["data"].shape[-1] == data.shape[-1]:
                    data = data - self._spectrum_background["data"]
                else:
                    self._spectrum_tab.background_msg.setText("Wrong Background Size")

            data = data/self._spectrum_params['exposure_time']

            self._spectrum_data = {"wavelength":wavelength,
                                   "data":data}

            self._spectrum_tab.graph.clear()

            if self.spectrumlogic().acquisition_mode == 'MULTI_SCAN':

                if self._spectrum_tab.multipe_scan_mode.currentText() == "Scan Average":
                    y = np.mean(data, axis=0)
                    x = wavelength[-1]
                elif self._spectrum_tab.multipe_scan_mode.currentText() == "Scan Median":
                    y = np.median(data, axis=0)
                    x = wavelength[-1]
                elif self._spectrum_tab.multipe_scan_mode.currentText() == "Scan Accumulation":
                    s = data.shape
                    if len(s)>2:
                        y = np.reshape(data, (s[1], s[0]*s[2]))
                    else:
                        y = np.reshape(data, (s[0] * s[1]))
                    x = np.reshape(wavelength, (s[0]*s[-1]))
                else:
                    y = data[-1]
                    x = wavelength[-1]

            else:

                y = data
                x = wavelength

            if self.spectrumlogic().read_mode == "MULTIPLE_TRACKS":
                for i in range(len(y)):
                    self._spectrum_tab.graph.plot(x.T, y[i].T, pen=self.plot_colors[i])
            else:
                self._spectrum_tab.graph.plot(x.T, y.T, pen=self.plot_colors[0])

        if not self.spectrumlogic().module_state() == 'locked':
            self.spectrumlogic().sigUpdateData.disconnect()
            self._manage_stop_acquisition()