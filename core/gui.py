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
