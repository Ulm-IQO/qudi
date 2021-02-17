# -*- coding: utf-8 -*-
"""
This module contains a GUI component to crate easily a colorbar in any GUI module

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
from functools import partial

from gui.colordefs import QudiPalettePale as Palette
from gui.guibase import GUIBase
from gui.colordefs import ColorScaleInferno
from qtwidgets.scientific_spinbox import ScienDSpinBox, ScienSpinBox

from qtpy import QtWidgets
from qtpy import uic
from gui.guiutils import ColorBar
from gui.colordefs import ColorScaleMagma

import numpy as np

import time

class ColorbarWidget(QtWidgets.QWidget):
    """ Create the widget, based on the corresponding *.ui file."""

    def __init__(self, image_widget, unit='c/s'):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_colorbar.ui')

        # Load it
        super(ColorbarWidget, self).__init__()
        uic.loadUi(ui_file, self)

        self._cb_min = 0
        self._cb_max = 100
        self.unit = unit

        self.init_spin_box()
        self.init_colorbar()

        self.set_image(image_widget)

        self.percentile.clicked.emit()
        self.percentile.setChecked(True)

    def init_spin_box(self):
        """ Initialize all the spinboxes """
        self._min_percentile = ScienDSpinBox()
        self._min_manual = ScienDSpinBox()
        self._max_percentile = ScienDSpinBox()
        self._max_manual = ScienDSpinBox()

        self._min_percentile.setSuffix('%')
        self._min_percentile.setMinimum(0)
        self._min_percentile.setMaximum(100)
        self._min_percentile.setValue(0)

        self._min_manual.setSuffix(self.unit)

        self._max_percentile.setSuffix('%')
        self._max_percentile.setMinimum(0)
        self._max_percentile.setMaximum(100)
        self._max_percentile.setValue(100)

        self._max_manual.setSuffix(self.unit)

        self.min.addWidget(self._min_manual)
        self.min.addWidget(self._min_percentile)
        self.max.addWidget(self._max_percentile)
        self.max.addWidget(self._max_manual)

        self._min_percentile.valueChanged.connect(self.shortcut_to_cb_centiles)
        self._min_manual.valueChanged.connect(self.shortcut_to_cb_manual)
        self._max_percentile.valueChanged.connect(self.shortcut_to_cb_centiles)
        self._max_manual.valueChanged.connect(self.shortcut_to_cb_manual)

        self.manual.clicked.connect(self.update_cb_range)
        self.percentile.clicked.connect(self.update_cb_range)

    def init_colorbar(self):
        """ Create the colorbar """
        self.my_colors = ColorScaleInferno()
        self._color_map = ColorScaleMagma()
        self._cb = ColorBar(self.my_colors.cmap_normed, width=100, cb_min=self._cb_min, cb_max=self._cb_max)
        self.colorbar.addItem(self._cb)
        self.colorbar.hideAxis('bottom')
        self.colorbar.setLabel('left', 'Intensity', units=self.unit)
        self.colorbar.setMouseEnabled(x=False, y=False)

    def set_image(self, image_widget):
        """ Set the image widget associated to the colorbar """
        self._image = image_widget
        self._min_manual.setValue(np.min(self._image.image))
        self._min_percentile.setValue(0)
        self._max_manual.setValue(np.max(self._image.image))
        self._max_percentile.setValue(100)
        self.refresh_colorbar()

    def get_cb_range(self):
        """ Determines the cb_min and cb_max values for the image """
        # If "Manual" is checked, or the image data is empty (all zeros), then take manual cb range.
        if self.manual.isChecked() or np.count_nonzero(self._image.image) < 1:
            cb_min = self._min_manual.value()
            cb_max = self._max_manual.value()

        # Otherwise, calculate cb range from percentiles.
        else:
            # Exclude any zeros (which are typically due to unfinished scan)
            image_nonzero = self._image.image[np.nonzero(self._image.image)]

            # Read centile range
            low_centile = self._min_percentile.value()
            high_centile = self._max_percentile.value()

            cb_min = np.percentile(image_nonzero, low_centile)
            cb_max = np.percentile(image_nonzero, high_centile)

        cb_range = [cb_min, cb_max]

        return cb_range

    def refresh_colorbar(self):
        """ Adjust the colorbar. """
        cb_range = self.get_cb_range()
        self._cb.refresh_colorbar(cb_range[0], cb_range[1])

    def refresh_image(self):
        """ Update the image colors range."""

        image_data = self._image.image
        cb_range = self.get_cb_range()
        self._image.setImage(image=image_data, levels=(cb_range[0], cb_range[1]))
        self.refresh_colorbar()

    def update_cb_range(self):
        """ Redraw colour bar and image."""
        self.refresh_colorbar()
        self.refresh_image()

    def shortcut_to_cb_manual(self):
        """ Someone edited the absolute counts range for the colour bar, better update."""
        self.manual.setChecked(True)
        self.update_cb_range()

    def shortcut_to_cb_centiles(self):
        """Someone edited the centiles range for the colour bar, better update."""
        self.percentile.setChecked(True)
        self.update_cb_range()
