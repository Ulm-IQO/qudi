from gui.guibase import GUIBase
from qtpy import QtWidgets, QtCore, QtGui
from core.connector import Connector


class MotorGridGui(GUIBase):

    gridlogic = Connector(interface='MotorGridLogic')

    def on_activate(self):
        self._mw = MotorGridMainWindow()
        self.dropdown = self._mw.dropdown
        self.dropdown.addItems(self.gridlogic().positions)

        try:
            closest_device = self.gridlogic().get_closest()
            idx = self.dropdown.findText(closest_device)
            if idx != -1:
                self.dropdown.setCurrentIndex(idx)
        except ValueError:
            pass

        self.dropdown.lineEdit().returnPressed.connect(self.edit_done)

        self._mw.goto_button.clicked.connect(self.goto_device)
        self._mw.save_button.clicked.connect(self.save_position)
        self._mw.delete_button.clicked.connect(self.delete_position)
        self._mw.global_offset_button.clicked.connect(self.global_offset)

        self._mw.action_clear_all.triggered.connect(self.clear_all)

        self.show()

    def on_deactivate(self):
        self._mw.goto_button.clicked.disconnect()
        self._mw.save_button.clicked.disconnect()
        self._mw.delete_button.clicked.disconnect()
        self._mw.global_offset_button.clicked.disconnect()
        self._mw.close()

    def show(self):
        """ Make sure that the window is visible and at the top.
        """
        self._mw.show()
        self._mw.raise_()

    def edit_done(self):
        device = self.dropdown.currentText()
        if device not in self.gridlogic().positions:
            self.gridlogic().save_position(device)
        elif device in self.gridlogic().positions:
            self.gridlogic().move_to(device)

    def save_position(self):
        device = self.dropdown.currentText()
        if device not in self.gridlogic().positions:
            self.dropdown.addItem(device)
        self.gridlogic().save_position(device)

    def delete_position(self):
        device = self.dropdown.currentText()
        self.dropdown.removeItem(self.dropdown.currentIndex())
        self.gridlogic().delete_position(device)

    def goto_device(self):
        device = self.dropdown.currentText()
        if device in self.gridlogic().positions:
            self.gridlogic().move_to(device)
        else:
            raise ValueError(f'Device name {device} not known by logic')

    def clear_all(self):
        self.gridlogic().clear_all_positions()
        self.dropdown.clear()

    def global_offset(self):
        device = self.dropdown.currentText()
        if device in self.gridlogic().positions:
            self.gridlogic().globally_update_position(device)
        else:
            raise ValueError(f'Device name {device} not known by logic')


class MotorGridMainWindow(QtWidgets.QMainWindow):
    """ Main Window for the MotorGrid module """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle('qudi: Motor Grid Gui')
        # Create main layout and central widget
        self.main_layout = QtWidgets.QGridLayout()
        self.main_layout.setColumnStretch(1, 1)
        self.main_layout.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.main_layout.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)
        widget = QtWidgets.QWidget()
        widget.setLayout(self.main_layout)
        widget.setFixedSize(1, 1)
        self.setCentralWidget(widget)

        # Create QActions and menu bar
        menu_bar = QtWidgets.QMenuBar()
        self.setMenuBar(menu_bar)

        menu = menu_bar.addMenu('Menu')
        self.action_close = QtWidgets.QAction('Close Window')
        self.action_close.setCheckable(False)
        self.action_close.setIcon(QtGui.QIcon('artwork/icons/oxygen/22x22/application-exit.png'))
        self.addAction(self.action_close)
        menu.addAction(self.action_close)
        menu = menu_bar.addMenu('Clear')
        self.action_clear_all = QtWidgets.QAction('Clear all')
        self.action_clear_all.setCheckable(False)
        menu.addAction(self.action_clear_all)

        # close window upon triggering close action
        self.action_close.triggered.connect(self.close)

        self.dropdown = QtWidgets.QComboBox()
        self.dropdown.setEditable(True)
        self.dropdown.setInsertPolicy(QtWidgets.QComboBox.InsertAtTop)
        self.main_layout.addWidget(self.dropdown)

        # self.line_edit = QtWidgets.QLineEdit()
        # self.main_layout.addWidget(self.line_edit)

        self.goto_button = QtWidgets.QPushButton("GoTo")
        # self.global_offset_button = QtWidgets.QPushButton("Global offset")
        self.main_layout.addWidget(self.goto_button)

        self.button_box = QtWidgets.QDialogButtonBox()
        # self.goto_button = self.button_box.addButton("GoTo", QtWidgets.QDialogButtonBox.ActionRole)
        self.save_button = self.button_box.addButton("Save", QtWidgets.QDialogButtonBox.ActionRole)
        self.delete_button = self.button_box.addButton("Delete", QtWidgets.QDialogButtonBox.ActionRole)
        self.global_offset_button = self.button_box.addButton("Global offset", QtWidgets.QDialogButtonBox.ActionRole)

        self.main_layout.addWidget(self.button_box, 2, 0, 1, 0, QtCore.Qt.AlignCenter)

