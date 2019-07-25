# -*- coding: utf-8 -*-
"""
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

import numpy as np
import pyqtgraph as pg
from core.module import Connector
from gui.guibase import GUIBase
from qtpy import QtWidgets, QtGui, QtCore
from gui.colordefs import QudiPalettePale as palette


class WfmView(GUIBase):
    """
    """

    sequencegenerator = Connector(interface='SequenceGeneratorLogic')

    def __init__(self, config, **kwargs):
        """
        """
        super().__init__(config=config, **kwargs)
        self._seqgen = None
        self._mw = None
        self._render_button = None
        self._waveform_combobox = None
        self._waveform_view_widget = None
        self._waveform_plot = None
        return

    def on_activate(self):
        """This creates all the necessary UI elements.
        """
        self._seqgen = self.sequencegenerator()

        self._mw = QtWidgets.QMainWindow()
        self._mw.setWindowTitle('Waveform View')
        self._render_button = QtWidgets.QPushButton('Render Waveform')
        self._waveform_combobox = QtWidgets.QComboBox()
        self._waveform_combobox.setMinimumWidth(150)
        self._waveform_view_widget = pg.PlotWidget()
        self._waveform_view_widget.setMinimumSize(100, 100)
        self._waveform_plot = pg.PlotDataItem(x=np.arange(10000),
                                              y=3*np.sin(np.linspace(0, 20*np.pi, 9999)),
                                              pen=pg.mkPen(palette.c1),
                                              symbol=None,
                                              stepMode=True)
        self._waveform_view_widget.addItem(self._waveform_plot)
        # rect = QtCore.QRectF(-0.5, -0.5, 1.0, 1.0)
        # path = QtGui.QPainterPath()
        # path.addRect(rect)
        # item = pg.ScatterPlotItem(x=[5000], y=[0], pxMode=False, pen=pg.mkPen(palette.c1), brush=pg.mkBrush(palette.c1), size=(1000, 1), symbol=path)
        item = QtWidgets.QGraphicsRectItem(self._waveform_plot.mapRectToView(QtCore.QRectF(2000.5, 2.5, 999, -5)))
        item.setPen(QtGui.QPen(palette.c1, 1, QtCore.Qt.SolidLine, QtCore.Qt.FlatCap, QtCore.Qt.MiterJoin))
        item.setBrush(palette.c1)
        self._waveform_view_widget.addItem(item)
        self._waveform_view_widget.setLabel('left', 'Amplitude', units='V')
        self._waveform_view_widget.setLabel('bottom', 'Time', units='s')
        central_layout = QtWidgets.QGridLayout()
        central_layout.addWidget(self._render_button, 0, 0)
        central_layout.addWidget(self._waveform_combobox, 0, 1)
        central_layout.addWidget(self._waveform_view_widget, 1, 0, 1, 3)
        central_layout.setColumnStretch(2, 1)
        central_layout.setRowStretch(1, 1)
        centralwidget = QtWidgets.QWidget()
        centralwidget.setLayout(central_layout)
        self._mw.setCentralWidget(centralwidget)
        self._mw.setGeometry(300, 300, 500, 200)

        self.update_ensembles()

        self._seqgen.sigEnsembleDictUpdated.connect(self.update_ensembles)
        self._render_button.clicked.connect(self.render_waveform)
        self.show()
        return

    def on_deactivate(self):
        """
        """
        self._render_button.clicked.disconnect()
        self._seqgen.sigEnsembleDictUpdated.disconnect()
        self._mw.close()

    def show(self):
        """Make window visible and put it above all other windows.
        """
        self._mw.show()
        self._mw.activateWindow()
        self._mw.raise_()
        return

    @QtCore.Slot(dict)
    def update_ensembles(self, ensemble_dict=None):
        if ensemble_dict is None:
            ensemble_dict = self._seqgen.saved_pulse_block_ensembles
        self._waveform_combobox.clear()
        self._waveform_combobox.addItems(list(ensemble_dict))
        return

    @QtCore.Slot()
    def render_waveform(self):
        # Determine PulseBlockEnsemble name to render waveform from
        name = self._waveform_combobox.currentText()
        if not name:
            self.log.warning('No waveform selected to render.')
            return
        # Get PulseBlockEnsemble instance from logic module
        ensemble = self._seqgen.get_ensemble(name)
        # Get ensemble info from logic module
        ens_info = self._seqgen.analyze_block_ensemble(ensemble)
        # Get all saved blocks from logic module
        block_dict = self._seqgen.saved_pulse_blocks
        # Get current sample rate
        sample_rate = self._seqgen.pulse_generator_settings['sample_rate']
        self._waveform_widget.render_waveform(ensemble, ens_info, block_dict, 2048, sample_rate)
        self._x_axis_widget.render_axis(ens_info['number_of_samples'])
        self._y_axis_widget.render_axis()
        return

    # def render_waveform(self, ensemble, info_dict, block_dict, vertical_resolution, sample_rate, update=False):
    #     # Determine max frequency from current widget size
    #     max_freq = self.width() / (4 * info_dict['ideal_length'])
    #     print(max_freq)
    #     # Create empty QPainterPath to construct the waveform
    #     path_list = list()
    #     element_index = 0
    #     sample_index = 0
    #     for ens_step, (blk_name, reps) in enumerate(ensemble):
    #         # Get PulseBlock instance from logic module
    #         block = block_dict[blk_name]
    #         for ii in range(reps + 1):
    #             for element in block:
    #                 elem_len = info_dict['elements_length_bins'][element_index]
    #                 element_index += 1
    #                 if elem_len == 0:
    #                     continue
    #                 func = element.pulse_function['a_ch1']
    #                 func_name = func.__class__.__name__
    #                 path = QtGui.QPainterPath()
    #                 if path_list:
    #                     path.moveTo(path_list[-1][0].currentPosition())
    #                 else:
    #                     path.moveTo(0, vertical_resolution // 2)
    #                 if func_name == 'Idle':
    #                     path.lineTo(sample_index, vertical_resolution // 2)
    #                     path.lineTo(sample_index + elem_len, vertical_resolution // 2)
    #                     path_list.append((path, False))
    #                 elif func_name == 'DC':
    #                     path.lineTo(
    #                         sample_index,
    #                         vertical_resolution - round((func.voltage * vertical_resolution) + vertical_resolution // 2))
    #                     path.lineTo(
    #                         sample_index + elem_len,
    #                         vertical_resolution - round((func.voltage * vertical_resolution) + vertical_resolution // 2))
    #                     path_list.append((path, False))
    #                 elif func_name == 'Sin':
    #                     if func.frequency > max_freq:
    #                         path.addRect(
    #                             sample_index,
    #                             round(vertical_resolution // 2 - (func.amplitude * vertical_resolution // 2)),
    #                             elem_len,
    #                             round(func.amplitude * vertical_resolution))
    #                         path.moveTo(sample_index + elem_len, vertical_resolution // 2)
    #                         path_list.append((path, True))
    #                     else:
    #                         times = sample_index + np.arange(elem_len, dtype='float64')
    #                         sample_array = func.get_samples(times / sample_rate)
    #                         for s_i, sample in enumerate(sample_array):
    #                             path.lineTo(
    #                                 sample_index + s_i,
    #                                 vertical_resolution - round((sample * vertical_resolution // 2) + vertical_resolution // 2)-1)
    #                             path.lineTo(
    #                                 sample_index + s_i + 1,
    #                                 vertical_resolution - round((sample * vertical_resolution // 2) + vertical_resolution // 2)-1)
    #                         path_list.append((path, False))
    #                 sample_index += elem_len
    #
    #     self._orig_size = QtCore.QSize(info_dict['number_of_samples'], vertical_resolution)
    #     self._painter_paths = path_list
    #     self.update()
    #     return
