"""
QCheckBox with a callback function for acceptance or denial of state change.

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

from qtpy.QtWidgets import QCheckBox

class CheckBox(QCheckBox):
    """
    This QCheckBox provides a callback function which is called before
    the state is changed and which can be used to prevent state changes on
    certain conditions.

    The callback function has the following signature:
    bool callback(new_state: bool)
    where new_state is a boolean with the new state if accepted and the return
    value is True for acceptance and False for denial.

    Usage Example:
    checkbox = CheckBox()
    def on_accept_state_change(new_state):
        if (not new_state):
            result = QMessageBox.question(
                    self,
                    'Are you sure you want to disable this?',
                    QMessageBox.StandardButtons(
                        QMessageBox.Yes | QMessageBox.No)
                    )
            return result == QMessageBox.Yes
    checkbox.accept_state_change_callback = on_accept_state_change
    """
    def __init__(self, *args, **kwargs):
        """
        Constructor. See QCheckBox for details.
        """
        super().__init__(*args, **kwargs)
        self._callback = None

    @property
    def accept_state_change_callback(self):
        """
        Returns state changing callback function.

        The callback function has the following signature:
        bool callback(new_state: bool)
        where new_state is a boolean with the new state if accepted and the
        return value is True for acceptance and False for denial.
        """
        return self._callback

    @accept_state_change_callback.setter
    def accept_state_change_callback(self, value):
        """
        Sets state changing callback function.

        The callback function has the following signature:
        bool callback(new_state: bool)
        where new_state is a boolean with the new state if accepted and the
        return value is True for acceptance and False for denial.
        """
        self._callback = value

    def nextCheckState(self):
        """
        Protected functions that calls the callback.
        """
        if (self._callback is not None):
            if (self._callback(not self.isChecked())):
                super().nextCheckState()
        else:
            super().nextCheckState()
