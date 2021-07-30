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
import weakref
import platform
from PySide2 import QtCore, QtGui, QtWidgets
from qudi.core.gui.main_gui.main_gui import QudiMainGui
from qudi.core.modulemanager import ModuleManager
from qudi.core.paths import get_artwork_dir
from qudi.core.logger import get_logger

try:
    import pyqtgraph as pg
except ImportError:
    pg = None

logger = get_logger(__name__)


class SystemTrayIcon(QtWidgets.QSystemTrayIcon):
    """Tray icon class subclassing QSystemTrayIcon for custom functionality.
    """

    def __init__(self):
        """Tray icon constructor.
        Adds all the appropriate menus and actions.
        """
        super().__init__()
        self._actions = dict()
        self.setIcon(QtWidgets.QApplication.instance().windowIcon())
        self.right_menu = QtWidgets.QMenu('Quit')
        self.left_menu = QtWidgets.QMenu('Manager')

        iconpath = os.path.join(get_artwork_dir(), 'icons', 'oxygen', '22x22')
        self.managericon = QtGui.QIcon()
        self.managericon.addFile(os.path.join(iconpath, 'go-home.png'), QtCore.QSize(16, 16))
        self.managerAction = QtWidgets.QAction(self.managericon, 'Manager', self.left_menu)

        self.exiticon = QtGui.QIcon()
        self.exiticon.addFile(os.path.join(iconpath, 'application-exit.png'), QtCore.QSize(16, 16))
        self.quitAction = QtWidgets.QAction(self.exiticon, 'Quit', self.right_menu)

        self.restarticon = QtGui.QIcon()
        self.restarticon.addFile(os.path.join(iconpath, 'view-refresh.png'), QtCore.QSize(16, 16))
        self.restartAction = QtWidgets.QAction(self.restarticon, 'Restart', self.right_menu)

        self.left_menu.addAction(self.managerAction)
        self.left_menu.addSeparator()

        self.right_menu.addAction(self.quitAction)
        self.right_menu.addAction(self.restartAction)
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

    def add_action(self, label, callback, icon=None):
        if label in self._actions:
            raise ValueError(f'Action "{label}" already exists in system tray.')

        if not isinstance(icon, QtGui.QIcon):
            icon = QtGui.QIcon()
            iconpath = os.path.join(get_artwork_dir(), 'icons', 'oxygen', '22x22')
            icon.addFile(os.path.join(iconpath, 'go-next.png'), QtCore.QSize(16, 16))

        action = QtWidgets.QAction(label)
        action.setIcon(icon)
        action.triggered.connect(callback)
        self.left_menu.addAction(action)
        self._actions[label] = action

    def remove_action(self, label):
        action = self._actions.pop(label, None)
        if action is not None:
            action.triggered.disconnect()
            self.left_menu.removeAction(action)


class Gui(QtCore.QObject):
    """ Set up all necessary GUI elements, like application icons, themes, etc.
    """

    _instance = None

    _sigPopUpMessage = QtCore.Signal(str, str)
    _sigBalloonMessage = QtCore.Signal(str, str, object, object)

    def __new__(cls, *args, **kwargs):
        if cls._instance is None or cls._instance() is None:
            obj = super().__new__(cls, *args, **kwargs)
            cls._instance = weakref.ref(obj)
            return obj
        raise RuntimeError(
            'Gui is a singleton. Please use Gui.instance() to get a reference to the already '
            'created instance.'
        )

    def __init__(self, qudi_instance, stylesheet_path=None, theme=None, use_opengl=False):
        if stylesheet_path is not None and not os.path.isfile(stylesheet_path):
            raise FileNotFoundError('stylesheet_path "{0}" not found.'.format(stylesheet_path))
        if theme is None:
            theme = 'qudiTheme'

        super().__init__()

        app = QtWidgets.QApplication.instance()
        if app is None:
            raise RuntimeError('No Qt GUI app running (no QApplication instance).')

        app.setQuitOnLastWindowClosed(False)

        self._init_app_icon()
        self.set_theme(theme)
        if stylesheet_path is not None:
            self.set_style_sheet(stylesheet_path)
        self.system_tray_icon = SystemTrayIcon()

        self._sigPopUpMessage.connect(self.pop_up_message, QtCore.Qt.QueuedConnection)
        self._sigBalloonMessage.connect(self.balloon_message, QtCore.Qt.QueuedConnection)

        self._configure_pyqtgraph(use_opengl)
        self.main_gui_module = QudiMainGui(qudi_main_weakref=weakref.ref(qudi_instance),
                                           name='qudi_main_gui')
        self.system_tray_icon.managerAction.triggered.connect(self.main_gui_module.show,
                                                              QtCore.Qt.QueuedConnection)
        self.system_tray_icon.quitAction.triggered.connect(qudi_instance.quit,
                                                           QtCore.Qt.QueuedConnection)
        self.system_tray_icon.restartAction.triggered.connect(qudi_instance.restart,
                                                              QtCore.Qt.QueuedConnection)
        qudi_instance.module_manager.sigModuleStateChanged.connect(self._tray_module_action_changed)
        self.show_system_tray_icon()

    @classmethod
    def instance(cls):
        if cls._instance is None:
            return None
        return cls._instance()

    @staticmethod
    def _init_app_icon():
        """ Set up the Qudi application icon.
        """
        iconpath = os.path.join(get_artwork_dir(), 'logo')
        app_icon = QtGui.QIcon()
        app_icon.addFile(os.path.join(iconpath, 'logo-qudi-16x16.png'), QtCore.QSize(16, 16))
        app_icon.addFile(os.path.join(iconpath, 'logo-qudi-24x24.png'), QtCore.QSize(24, 24))
        app_icon.addFile(os.path.join(iconpath, 'logo-qudi-32x32.png'), QtCore.QSize(32, 32))
        app_icon.addFile(os.path.join(iconpath, 'logo-qudi-48x48.png'), QtCore.QSize(48, 48))
        app_icon.addFile(os.path.join(iconpath, 'logo-qudi-256x256.png'), QtCore.QSize(256, 256))
        QtWidgets.QApplication.instance().setWindowIcon(app_icon)

    @staticmethod
    def _configure_pyqtgraph(use_opengl=False):
        # Configure pyqtgraph (if present)
        if pg is not None:
            # test setting background of pyqtgraph
            testwidget = QtWidgets.QWidget()
            testwidget.ensurePolished()
            bgcolor = testwidget.palette().color(QtGui.QPalette.Normal, testwidget.backgroundRole())
            # set manually the background color in hex code according to our color scheme:
            pg.setConfigOption('background', bgcolor)
            # experimental opengl usage
            pg.setConfigOption('useOpenGL', use_opengl)

    @staticmethod
    def set_theme(theme):
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
        themepaths.append(os.path.join(get_artwork_dir(), 'icons'))
        QtGui.QIcon.setThemeSearchPaths(themepaths)
        QtGui.QIcon.setThemeName(theme)

    @staticmethod
    def set_style_sheet(stylesheet_path):
        """
        Set qss style sheet for application.

        @param str stylesheet_path: path to style sheet file
        """
        with open(stylesheet_path, 'r') as stylesheetfile:
            stylesheet = stylesheetfile.read()

        if stylesheet_path.endswith('qdark.qss'):
            path = os.path.join(os.path.dirname(stylesheet_path), 'qdark').replace('\\', '/')
            stylesheet = stylesheet.replace('{qdark}', path)

        # see issue #12 on qdarkstyle github
        if platform.system().lower() == 'darwin' and stylesheet_path.endswith('qdark.qss'):
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

    def activate_main_gui(self):
        if QtCore.QThread.currentThread() is not self.thread():
            QtCore.QMetaObject.invokeMethod(self,
                                            'activate_main_gui',
                                            QtCore.Qt.BlockingQueuedConnection)
            return

        logger.info('Activating main GUI module...')
        print('> Activating main GUI module...')
        if self.main_gui_module.module_state() != 'deactivated':
            self.main_gui_module.show()
            return

        self.main_gui_module.module_state.activate()
        QtWidgets.QApplication.instance().processEvents()

    def deactivate_main_gui(self):
        if QtCore.QThread.currentThread() is not self.thread():
            QtCore.QMetaObject.invokeMethod(self,
                                            'deactivate_main_gui',
                                            QtCore.Qt.BlockingQueuedConnection)
            return

        if self.main_gui_module.module_state() == 'deactivated':
            return

        self.main_gui_module.module_state.deactivate()
        QtWidgets.QApplication.instance().processEvents()

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
        self.system_tray_icon.restartAction.triggered.disconnect()
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

    def prompt_shutdown(self, modules_locked=True):
        """ Display a dialog, asking the user to confirm shutdown.
        """
        if modules_locked:
            msg = 'Some qudi modules are locked right now.\n' \
                  'Do you really want to quit and force modules to deactivate?'
        else:
            msg = 'Do you really want to quit?'

        result = QtWidgets.QMessageBox.question(self.main_gui_module.mw,
                                                'Qudi: Quit?',
                                                msg,
                                                QtWidgets.QMessageBox.Yes,
                                                QtWidgets.QMessageBox.No)
        return result == QtWidgets.QMessageBox.Yes

    def prompt_restart(self, modules_locked=True):
        """ Display a dialog, asking the user to confirm restart.
        """
        if modules_locked:
            msg = 'Some qudi modules are locked right now.\n' \
                  'Do you really want to restart and force modules to deactivate?'
        else:
            msg = 'Do you really want to restart?'

        result = QtWidgets.QMessageBox.question(self.main_gui_module.mw,
                                                'Qudi: Restart?',
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

    @QtCore.Slot(str, str, str)
    def _tray_module_action_changed(self, base, module_name, state):
        if self.system_tray_icon and base == 'gui':
            if state == 'deactivated':
                self.system_tray_icon.remove_action(module_name)
            else:
                mod_manager = ModuleManager.instance()
                try:
                    module_inst = mod_manager[module_name].instance
                except KeyError:
                    return
                self.system_tray_icon.add_action(module_name, module_inst.show)
