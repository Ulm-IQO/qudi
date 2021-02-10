# -*- coding: utf-8 -*-

"""
This file contains a custom QDockWidget subclass to be used in the ODMR GUI module.

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

__all__ = ('OdmrFitDockWidget',)


class OdmrFitDockWidget(AdvancedDockWidget):
    """
    """

    def __init__(self, *args, fit_container=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle('ODMR Fit')
        self.setFeatures(self.DockWidgetFloatable | self.DockWidgetMovable)

        self.fit_widget = FitWidget(fit_container=fit_container)
        self.setWidget(self.fit_widget)
