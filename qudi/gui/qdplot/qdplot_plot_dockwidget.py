# -*- coding: utf-8 -*-

"""
This file contains a custom QDockWidget subclass to be used in the QD Plot GUI module.

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

from qudi.core.gui.qtwidgets.advanced_dockwidget import AdvancedDockWidget
from qudi.core.gui.qtwidgets.fitting import FitWidget
from qudi.core.gui.qtwidgets.scientific_spinbox import ScienDSpinBox
from qtpy import QtWidgets, QtCore, QtGui
import pyqtgraph as pg

__all__ = ('PlotDockWidget',)


class CustomAxis(pg.AxisItem):
    """ This is a CustomAxis that extends the normal pyqtgraph to be able to nudge the axis labels. """

    @property
    def nudge(self):
        if not hasattr(self, "_nudge"):
            self._nudge = 5
        return self._nudge

    @nudge.setter
    def nudge(self, nudge):
        self._nudge = nudge
        s = self.size()
        # call resizeEvent indirectly
        self.resize(s + QtCore.QSizeF(1, 1))
        self.resize(s)

    def resizeEvent(self, ev=None):
        # Set the position of the label
        nudge = self.nudge
        br = self.label.boundingRect()
        p = QtCore.QPointF(0, 0)
        if self.orientation == "left":
            p.setY(int(self.size().height() / 2 + br.width() / 2))
            p.setX(-nudge)
        elif self.orientation == "right":
            p.setY(int(self.size().height() / 2 + br.width() / 2))
            p.setX(int(self.size().width() - br.height() + nudge))
        elif self.orientation == "top":
            p.setY(-nudge)
            p.setX(int(self.size().width() / 2.0 - br.width() / 2.0))
        elif self.orientation == "bottom":
            p.setX(int(self.size().width() / 2.0 - br.width() / 2.0))
            p.setY(int(self.size().height() - br.height() + nudge))
        self.label.setPos(p)
        self.picture = None


class PlotDockWidget(AdvancedDockWidget):
    """
    """

    def __init__(self, *args, plot_number=0, fit_container=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle(f'Plot {plot_number}')
        self.setFeatures(self.DockWidgetFloatable | self.DockWidgetMovable)

        # Create main layout and main widget
        self.main_layout = QtWidgets.QGridLayout()
        self.main_layout.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.main_layout.setContentsMargins(1, 1, 1, 1)
        self.main_layout.setSpacing(0)
        # self.setStyleSheet('border: 1px solid #f00;')  # debugging help for the gui
        main_widget = QtWidgets.QWidget()
        main_widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.MinimumExpanding)
        main_widget.setLayout(self.main_layout)
        self.setWidget(main_widget)

        # Add the main plot area
        plot_display_widget = self._create_plot_display()
        self.main_layout.addWidget(plot_display_widget, 0, 0)

        # Add a placeholder for the fit widget on the right
        self.fit_widget = FitWidget(fit_container=fit_container)
        self.main_layout.addWidget(self.fit_widget, 0, 1)

        # Add widget for the plot controls on the bottom
        self.plot_control_widget = self._create_plot_control()
        self.main_layout.addWidget(self.plot_control_widget, 1, 0, 2, 0, QtCore.Qt.AlignHCenter)

        self.show_controls_checkBox.clicked.connect(self.show_controls, QtCore.Qt.QueuedConnection)
        self.show_fit_checkBox.clicked.connect(self.show_fit, QtCore.Qt.QueuedConnection)

        self.show_controls(False)
        self.show_fit(False)

    def _create_plot_display(self):
        plot_display_layout = QtWidgets.QGridLayout()
        plot_display_layout.setContentsMargins(1, 1, 1, 1)
        plot_display_layout.setSpacing(0)
        plot_display_widget = QtWidgets.QWidget()
        plot_display_widget.setLayout(plot_display_layout)
        plot_display_widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        self.save_button = QtWidgets.QPushButton('Save')
        self.remove_button = QtWidgets.QPushButton('Remove')
        self.show_controls_checkBox = QtWidgets.QCheckBox('Show Controls')
        self.show_fit_checkBox = QtWidgets.QCheckBox('Show Fit')
        plot_display_layout.addWidget(self.save_button, 0, 0)
        plot_display_layout.addWidget(self.remove_button, 0, 2)
        plot_display_layout.addWidget(self.show_controls_checkBox, 0, 3)
        plot_display_layout.addWidget(self.show_fit_checkBox, 0, 4)

        self.plot_widget = pg.PlotWidget(axisItems={'bottom': CustomAxis(orientation='bottom'),
                                                    'left': CustomAxis(orientation='left')})
        self.plot_widget.getAxis('bottom').nudge = 0
        self.plot_widget.getAxis('left').nudge = 0

        self.plot_widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        plot_display_layout.addWidget(self.plot_widget, 1, 0, 15, 0, QtCore.Qt.AlignHCenter)

        return plot_display_widget

    def show_fit(self, visible=True):
        if self.fit_widget:
            self.fit_widget.setVisible(visible)
            self.show_fit_checkBox.setChecked(visible)

    def show_controls(self, visible=True):
        self.plot_control_widget.setVisible(visible)
        self.show_controls_checkBox.setChecked(visible)

    def _create_plot_control(self):
        plot_control_layout = QtWidgets.QGridLayout()
        plot_control_layout.setContentsMargins(1, 1, 1, 1)
        plot_control_layout.setSpacing(0)
        plot_control_widget = QtWidgets.QGroupBox('Plot Control')
        plot_control_widget.setAlignment(QtCore.Qt.AlignLeft)
        plot_control_widget.setLayout(plot_control_layout)
        plot_control_widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.MinimumExpanding)

        x_label = QtWidgets.QLabel('Horizontal Axis')
        y_label = QtWidgets.QLabel('Vertical Axis')
        label_label = QtWidgets.QLabel('Label')
        label_label.setAlignment(QtCore.Qt.AlignCenter)
        unit_label = QtWidgets.QLabel('Units')
        unit_label.setAlignment(QtCore.Qt.AlignCenter)
        range_label = QtWidgets.QLabel('Range')
        range_label.setAlignment(QtCore.Qt.AlignCenter)
        plot_control_layout.addWidget(x_label, 1, 0)
        plot_control_layout.addWidget(y_label, 2, 0)
        plot_control_layout.addWidget(label_label, 0, 1)
        plot_control_layout.addWidget(unit_label, 0, 2)
        plot_control_layout.addWidget(range_label, 0, 3, 1, 5, QtCore.Qt.AlignHCenter)

        self.x_label_lineEdit = QtWidgets.QLineEdit()
        self.x_unit_lineEdit = QtWidgets.QLineEdit()
        self.x_lower_limit_spinBox = ScienDSpinBox()
        self.x_lower_limit_spinBox.setMinimumWidth(70)
        self.x_upper_limit_spinBox = ScienDSpinBox()
        self.x_upper_limit_spinBox.setMinimumWidth(70)
        self.x_auto_button = QtWidgets.QPushButton('Auto Range')

        self.y_label_lineEdit = QtWidgets.QLineEdit()
        self.y_unit_lineEdit = QtWidgets.QLineEdit()
        self.y_lower_limit_spinBox = ScienDSpinBox()
        self.y_lower_limit_spinBox.setMinimumWidth(70)
        self.y_upper_limit_spinBox = ScienDSpinBox()
        self.y_upper_limit_spinBox.setMinimumWidth(70)
        self.y_auto_button = QtWidgets.QPushButton('Auto Range')

        plot_control_layout.addWidget(self.x_label_lineEdit, 1, 1)
        plot_control_layout.addWidget(self.x_unit_lineEdit, 1, 2)
        plot_control_layout.addWidget(self.x_lower_limit_spinBox, 1, 3)
        plot_control_layout.addWidget(self.x_upper_limit_spinBox, 1, 4)
        plot_control_layout.addWidget(self.x_auto_button, 1, 5)

        plot_control_layout.addWidget(self.y_label_lineEdit, 2, 1)
        plot_control_layout.addWidget(self.y_unit_lineEdit, 2, 2)
        plot_control_layout.addWidget(self.y_lower_limit_spinBox, 2, 3)
        plot_control_layout.addWidget(self.y_upper_limit_spinBox, 2, 4)
        plot_control_layout.addWidget(self.y_auto_button, 2, 5)

        return plot_control_widget
