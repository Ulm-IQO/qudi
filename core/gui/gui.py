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

import os
import platform
from qtpy import QtCore, QtGui, QtWidgets
import logging

logger = logging.getLogger(__name__)


class SystemTrayIcon(QtWidgets.QSystemTrayIcon):
    """Tray icon class subclassing QSystemTrayIcon for custom functionality.
    """
    def __init__(self, artwork_dir):
        """Tray icon constructor.
        Adds all the appropriate menus and actions.
        """
        super().__init__()
        self.setIcon(QtWidgets.QApplication.instance().windowIcon())
        self.right_menu = QtWidgets.QMenu('Quit')
        self.left_menu = QtWidgets.QMenu('Manager')
        iconpath = os.path.join(artwork_dir, 'icons', 'oxygen', '22x22')
        self.managericon = QtGui.QIcon()
        self.managericon.addFile(os.path.join(iconpath, 'go-home.png'), QtCore.QSize(16, 16))
        self.exiticon = QtGui.QIcon()
        self.exiticon.addFile(os.path.join(iconpath, 'application-exit.png'), QtCore.QSize(16, 16))
        self.quitAction = QtWidgets.QAction(self.exiticon, 'Quit', self.right_menu)
        self.managerAction = QtWidgets.QAction(self.managericon, 'Manager', self.left_menu)
        self.left_menu.addAction(self.managerAction)
        self.right_menu.addAction(self.quitAction)
        self.setContextMenu(self.right_menu)
        self.activated.connect(self.handle_activation)

    @QtCore.Slot(QtWidgets.QSystemTrayIcon.ActivationReason)
    def handle_activation(self, reason):
        """ Click handler.
        This method is called when the tray icon is left-clicked.
        It opens a menu at the position of the left click.

        @param reason: reason that caused the activation
        """
        if reason == self.Trigger:
            self.left_menu.exec_(QtGui.QCursor.pos())


class Gui(QtCore.QObject):
    """ Set up all necessary GUI elements, like application icons, themes, etc.
    """

    _sigPopUpMessage = QtCore.Signal(str, str)
    _sigBalloonMessage = QtCore.Signal(str, str, object, object)

    def __init__(self, artwork_dir, stylesheet_path=None):
        super().__init__()
        QtWidgets.QApplication.instance().setQuitOnLastWindowClosed(False)

        self._artwork_dir = artwork_dir
        self._init_app_icon()
        self.system_tray_icon = SystemTrayIcon(artwork_dir)
        self.show_system_tray_icon()
        if stylesheet_path is not None:
            self.set_style_sheet(stylesheet_path)
        self._sigPopUpMessage.connect(self.pop_up_message, QtCore.Qt.QueuedConnection)
        self._sigBalloonMessage.connect(self.balloon_message, QtCore.Qt.QueuedConnection)

    def _init_app_icon(self):
        """ Set up the Qudi application icon.
        """
        iconpath = os.path.join(self._artwork_dir, 'logo')
        app_icon = QtGui.QIcon()
        app_icon.addFile(os.path.join(iconpath, 'logo-qudi-16x16.png'), QtCore.QSize(16, 16))
        app_icon.addFile(os.path.join(iconpath, 'logo-qudi-24x24.png'), QtCore.QSize(24, 24))
        app_icon.addFile(os.path.join(iconpath, 'logo-qudi-32x32.png'), QtCore.QSize(32, 32))
        app_icon.addFile(os.path.join(iconpath, 'logo-qudi-48x48.png'), QtCore.QSize(48, 48))
        app_icon.addFile(os.path.join(iconpath, 'logo-qudi-256x256.png'), QtCore.QSize(256, 256))
        QtWidgets.QApplication.instance().setWindowIcon(app_icon)

    def set_theme(self, theme):
        """
        Set icon theme for qudi app.

        @param str theme: qudi theme name
        """
        # Make icons work on non-X11 platforms, set custom theme
        # if not sys.platform.startswith('linux') and not sys.platform.startswith('freebsd'):
        #
        # To enable the use of custom action icons, for now the above if statement has been
        # removed and the QT theme is being set to our artwork/icons folder for
        # all OSs.
        themepaths = QtGui.QIcon.themeSearchPaths()
        themepaths.append(os.path.join(self._artwork_dir, 'icons'))
        QtGui.QIcon.setThemeSearchPaths(themepaths)
        QtGui.QIcon.setThemeName(theme)

    @staticmethod
    def set_style_sheet(stylesheetpath):
        """
        Set qss style sheet for application.

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
        QtWidgets.QApplication.instance().setStyleSheet(stylesheet)

    @staticmethod
    def close_windows():
        """ Close all application windows.
        """
        QtWidgets.QApplication.instance().closeAllWindows()

    def show_system_tray_icon(self):
        """ Show system tray icon
        """
        self.system_tray_icon.show()

    def hide_system_tray_icon(self):
        """ Hide system tray icon
        """
        self.system_tray_icon.hide()

    def close_system_tray_icon(self):
        """
        Kill and delete system tray icon. Tray icon will be lost until Gui.__init__ is called again.
        """
        self.hide_system_tray_icon()
        self.system_tray_icon.quitAction.triggered.disconnect()
        self.system_tray_icon.managerAction.triggered.disconnect()
        self.system_tray_icon = None

    def system_tray_notification_bubble(self, title, message, time=None, icon=None):
        """
        Helper method to invoke balloon messages in the system tray by calling
        QSystemTrayIcon.showMessage.

        @param str title: The notification title of the balloon
        @param str message: The message to be shown in the balloon
        @param float time: optional, The lingering time of the balloon in seconds
        @param QIcon icon: optional, an icon to be used in the balloon. "None" will use OS default.
        """
        if icon is None:
            icon = QtGui.QIcon()
        if time is None:
            time = 15
        self.system_tray_icon.showMessage(title, message, icon, int(round(time * 1000)))

    @staticmethod
    def prompt_shutdown(modules_locked=True):
        """
        Display a dialog, asking the user to confirm shutdown.
        """
        if modules_locked:
            msg = 'Some qudi modules are locked right now.\n' \
                  'Do you really want to quit and force modules to deactivate?'
        else:
            msg = 'Do you really want to quit?'
        result = QtWidgets.QMessageBox.question(None,
                                                'Qudi: Shutdown?',
                                                msg,
                                                QtWidgets.QMessageBox.Yes,
                                                QtWidgets.QMessageBox.No)
        return result == QtWidgets.QMessageBox.Yes

    @QtCore.Slot(str, str)
    def pop_up_message(self, title, message):
        """
        Slot prompting a dialog window with a message and an OK button to dismiss it.

        @param str title: The window title of the dialog
        @param str message: The message to be shown in the dialog window
        """
        if not isinstance(title, str):
            logger.error('pop-up message title must be str type')
            return
        if not isinstance(message, str):
            logger.error('pop-up message must be str type')
            return
        if self.thread() is not QtCore.QThread.currentThread():
            self._sigPopUpMessage.emit(title, message)
            return
        QtWidgets.QMessageBox.information(None, title, message, QtWidgets.QMessageBox.Ok)
        return

    @QtCore.Slot(str, str, object, object)
    def balloon_message(self, title, message, time=None, icon=None):
        """
        Slot prompting a balloon notification from the system tray icon.

        @param str title: The notification title of the balloon
        @param str message: The message to be shown in the balloon
        @param float time: optional, The lingering time of the balloon in seconds
        @param QIcon icon: optional, an icon to be used in the balloon. "None" will use OS default.
        """
        if not self.system_tray_icon.supportsMessages():
            logger.warning('{0}:\n{1}'.format(title, message))
            return
        if self.thread() is not QtCore.QThread.currentThread():
            self._sigBalloonMessage.emit(title, message, time, icon)
            return
        self.system_tray_notification_bubble(title, message, time=time, icon=icon)
        return
