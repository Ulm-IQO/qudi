# -*- coding: utf-8 -*-
"""
This file contains the Qudi console app class.

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

import platform
import types
from qtpy.QtCore import QObject
from qtpy.QtWidgets import QApplication
from qtpy.QtGui import QIcon
from qtpy.QtCore import QSize


class Gui(QObject):
    """ Set up all necessary GUI elements, like application icons, themes, etc.
    """

    def __init__(self):
        super().__init__()
        QApplication.instance().setQuitOnLastWindowClosed(False)

    def setAppIcon(self):
        """ Set up the Qudi application icon.
        """
        iconpath = 'artwork/logo/logo-qudi-'
        self.appIcon = QIcon()
        self.appIcon.addFile('{0}16x16.png'.format(iconpath), QSize(16, 16))
        self.appIcon.addFile('{0}24x24.png'.format(iconpath), QSize(24, 24))
        self.appIcon.addFile('{0}32x32.png'.format(iconpath), QSize(32, 32))
        self.appIcon.addFile('{0}48x48.png'.format(iconpath), QSize(48, 48))
        self.appIcon.addFile('{0}256x256.png'.format(iconpath),
                             QSize(256, 256))
        QApplication.instance().setWindowIcon(self.appIcon)

    def setTheme(self, theme, path):
        """ Set icon theme for qudi app.
            
            @param str theme: Qudi theme name
            @param str path: search path for qudi icons
        """
        # Make icons work on non-X11 platforms, set custom theme
        # if not sys.platform.startswith('linux') and not sys.platform.startswith('freebsd'):
        #
        # To enable the use of custom action icons, for now the above if statement has been
        # removed and the QT theme is being set to our artwork/icons folder for
        # all OSs.
        themepaths = QIcon.themeSearchPaths()
        themepaths.append(path)
        QIcon.setThemeSearchPaths(themepaths)
        QIcon.setThemeName(theme)

    def setStyleSheet(self, stylesheetpath):
        """ Set qss style sheet for application.

            @param str stylesheetpath: path to style sheet file
        """
        with open(stylesheetpath, 'r') as stylesheetfile:
            stylesheet = stylesheetfile.read()

        # see issue #12 on qdarkstyle github
        if platform.system().lower() == 'darwin' and stylesheetpath.endswith('qdark.qss'):
            mac_fix = '''
            QDockWidget::title
            {
                background-color: #31363b;
                text-align: center;
                height: 12px;
            }
            '''
            stylesheet += mac_fix
        QApplication.instance().setStyleSheet(stylesheet)

    def closeWindows(self):
        """ Close all application windows.
        """
        QApplication.instance().closeAllWindows()


def connect_trigger_to_function(caller, trigger, event, function, connection_type=None):
    """" Safely connect a GUI action to a logic/gui method

    @param (module) caller: A reference to the calling module (self) to catch a deactivation event and clean up properly
    @param (QtObject) trigger : the object that generate the trigger
    @param (str) event : the type of event to listen to
    @param (function) function: The function to call when triggered
    @param (PyQt5.QtCore.Qt.ConnectionType) connection_type: The connection type passed to connect()

    The connection type can be blocking or queued, more info here : https://doc.qt.io/qt-5/qt.html
    """
    event_object = getattr(trigger, event) if event is not None else trigger
    if connection_type is None:
        event_object.connect(function)
    else:
        event_object.connect(function, connection_type)
    caller.add_deactivation_callback(lambda: event_object.disconnect())


def connect_view_to_model(caller, view, model_holder, model_getter, model_setter=None, **setter_params):
    """" A method to connect the Spinbox view to the model (variable) so updates in both ways are done automatically

    @param (module) caller: A reference to the calling module (self) to catch a deactivation event and clean up properly
    @param (Spinbox) view: The spinbox that has to be connected to the model
    @param (function) model_holder: The module which has the attribute/method that hold the model
    @param (str) model_getter: The name of the variable or getter function
    @param (str) model_setter: (optional) The name of the variable or setter function
    @param (dict) setter_params: (optional) parameters fed to the setter method if necessary

    The idea behind this tool is to connect an attribute (model) of the logic like "logic().resolution" to a view of
    the GUI which is here a SpinBox. Any change on the model update the view and any change on the view update the
    model.

    Here two paradigm can be used, a variable from the logic read directly or a pair of getter/setter like :
        logic().get_resolution() and logic().set_resolution(value)

    """

    model_setter = model_getter if model_setter is None else model_setter

    def update_model():
        value = view.value()
        attr = getattr(model_holder, model_setter)
        if isinstance(attr, types.MethodType):
            attr(value, **setter_params)
        else:
            setattr(model_holder, model_setter, value)
    view.editingFinished.connect(update_model)

    def update_view():
        attr = getattr(model_holder, model_getter)
        if isinstance(attr, types.MethodType):
            value = attr()
        else:
            value = attr
        view.blockSignals(True)
        view.setValue(value)
        view.blockSignals(False)

    def on_module_change(name_list):
        if model_getter in name_list:
            update_view()

    model_holder.model_has_changed.connect(on_module_change)

    caller.add_deactivation_callback(lambda: model_holder.model_has_changed.disconnect())
    caller.add_deactivation_callback(lambda: view.editingFinished.disconnect())

    update_view()

