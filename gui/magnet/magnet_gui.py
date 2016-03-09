# -*- coding: utf-8 -*-

"""
This file contains the GUI for magnet control.

QuDi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

QuDi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with QuDi. If not, see <http://www.gnu.org/licenses/>.

Copyright (C) 2016 Alexander Stark alexander.stark@uni-ulm.de
"""
import os
import numpy as np
from collections import OrderedDict

from gui.guibase import GUIBase
from pyqtgraph.Qt import QtCore, QtGui, uic


class MagnetMainWindow(QtGui.QMainWindow):
    """ Create the Main Window based on the *.ui file. """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_magnet_gui.ui')

        # Load it
        super(MagnetMainWindow, self).__init__()
        uic.loadUi(ui_file, self)
        self.show()

class MagnetSettingsWindow(QtGui.QDialog):
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_magnet_settings.ui')

        # Load it
        super(MagnetSettingsWindow, self).__init__()

        uic.loadUi(ui_file, self)


class MagnetGui(GUIBase):
    """ Main GUI for the magnet. """

    _modclass = 'magnetgui'
    _modtype = 'gui'

    ## declare connectors
    _in = {'magnetlogic1': 'MagnetLogic'}

    sigMoveRel = QtCore.Signal(dict)

    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        state_actions = {'onactivate': self.initUI,
                         'ondeactivate': self.deactivation}
        super().__init__(manager, name, config, state_actions, **kwargs)

        self.logMsg('The following configuration was found.',
                    msgType='status')

        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]),
                        msgType='status')


    def initUI(self, e=None):
        """ Definition and initialisation of the GUI.

        @param object e: Fysom.event object from Fysom class.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look in
                         the Base Class). This object contains the passed event,
                         the state before the event happened and the destination
                         of the state which should be reached after the event
                         had happened.
        """
        self._magnet_logic = self.connector['in']['magnetlogic1']['object']

        # self._magnet_logic.sigPosChanged.connect(self.update_pos)

        self._mw = MagnetMainWindow()
        self._create_axis_pos_disp()
        self._create_move_rel_control()
        self._create_move_abs_control()

        self.sigMoveRel.connect(self._magnet_logic.move_rel)

        # Configuring the dock widgets
        # Use the class 'MagnetMainWindow' to create the GUI window


        # Setup dock widgets
        self._mw.centralwidget.hide()
        self._mw.setDockNestingEnabled(True)

#        self._mw.tabifyDockWidget(self._mw.curr_pos_DockWidget, self._mw.move_rel_DockWidget)
#        self._mw.tabifyDockWidget(self._mw.curr_pos_DockWidget, self._mw.move_abs_DockWidget)
#        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(1), self._mw.curr_pos_DockWidget)
#        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(2), self._mw.move_rel_DockWidget)
#        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(3), self._mw.move_abs_DockWidget)

        self.set_default_view_main_window()

        # After a movement command, the device should not block the program, at
        # least on the hardware level. That meant that the dll (or whatever
        # protocol is used to access the hardware) can receive a command during
        # an ongoing action. That is of course controller specific, but in
        # general should it should be possible (unless the controller was
        # written by someone who has no clue what he is doing). Eventually with
        # that you have the possibility of stopping an ongoing movement!
        self._interactive_mode = True
        self._activate_magnet_settings(e)
        self._mw.actionMagnet_Settings.triggered.connect(self.open_magnet_settings)

        self._mw.actionDefault_View.triggered.connect(self.set_default_view_main_window)



    def _activate_magnet_settings(self, e):
        """ Activate magnet settings.

        @param object e: Fysom.event object from Fysom class. A more detailed
                         explanation can be found in the method initUI.
        """
        self._ms = MagnetSettingsWindow()
        self._ms.accepted.connect(self.update_magnet_settings)
        self._ms.rejected.connect(self.keep_former_magnet_settings)
        self._ms.ButtonBox.button(QtGui.QDialogButtonBox.Apply).clicked.connect(self.update_magnet_settings)

        self.keep_former_magnet_settings()

    def deactivation(self, e=None):
        """ Deactivate the module properly.

        @param object e: Fysom.event object from Fysom class. A more detailed
                         explanation can be found in the method initUI.
        """
        self._mw.close()

    def show(self):
        """Make window visible and put it above all other windows. """
        QtGui.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()


    def set_default_view_main_window(self):
        """ Establish the default dock Widget configuration. """

        # connect all widgets to the main Window
        self._mw.curr_pos_DockWidget.setFloating(False)
        self._mw.move_rel_DockWidget.setFloating(False)
        self._mw.move_abs_DockWidget.setFloating(False)

        # align the widget
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(4),
                               self._mw.curr_pos_DockWidget)
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(1),
                               self._mw.move_rel_DockWidget)
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(8),
                               self._mw.move_abs_DockWidget)

    def open_magnet_settings(self):
        """ This method opens the settings menu. """
        self._ms.exec_()

    def update_magnet_settings(self):

        if self._ms.interactive_mode_CheckBox.isChecked():
            self._interactive_mode = True
        else:
            self._interactive_mode = False

    def keep_former_magnet_settings(self):

        self._ms.interactive_mode_CheckBox.setChecked(self._interactive_mode)

    def _create_axis_pos_disp(self):
        """ Create the axis position display.

        The generic variable name for a created QLable is:
            curr_pos_axis{0}_Label
        The generic variable name for a created QDoubleSpinBox is:
            curr_pos_axis{0}_DoubleSpinBox
        where in {0} the name of the axis will be inserted.

        DO NOT CALL THESE VARIABLES DIRECTLY! USE THE DEDICATED METHOD INSTEAD!
        Use the method get_ref_curr_pos_DoubleSpinBox with the appropriated
        label, otherwise you will break the generality.
        """

        constraints = self._magnet_logic.get_hardware_constraints()

        # set the parameters in the curr_pos_DockWidget:
        for index, parameter in enumerate(constraints):

            # Set the QLabel according to the grid
            # this is the name prototype for the label of current position display
            label_var_name = 'curr_pos_axis{0}_Label'.format(parameter)
            setattr(self._mw, label_var_name, QtGui.QLabel(self._mw.curr_pos_DockWidgetContents))
            label_var = getattr(self._mw, label_var_name)
            label_var.setObjectName(label_var_name)
            label_var.setText(parameter)
            self._mw.curr_pos_GridLayout.addWidget(label_var, index, 0, 1, 1)

            # Set the QDoubleSpinBox according to the grid
            # this is the name prototype for the current position display
            dspinbox_var_name = 'curr_pos_axis{0}_DoubleSpinBox'.format(parameter)
            setattr(self._mw, dspinbox_var_name, QtGui.QDoubleSpinBox(self._mw.curr_pos_DockWidgetContents))
            dspinbox_var = getattr(self._mw, dspinbox_var_name)
            dspinbox_var.setObjectName(dspinbox_var_name)
            dspinbox_var.setReadOnly(True)
            dspinbox_var.setButtonSymbols(QtGui.QAbstractSpinBox.NoButtons)
            dspinbox_var.setMaximum(np.inf)
            dspinbox_var.setMinimum(-np.inf)
            #TODO: set the decimals also from the constraints or make them
            #      setable in the settings window!
            dspinbox_var.setDecimals(3)
            dspinbox_var.setSingleStep(constraints[parameter]['pos_step'])
            self._mw.curr_pos_GridLayout.addWidget(dspinbox_var, index, 1, 1, 1)

        extension =  len(constraints)
        self._mw.curr_pos_GridLayout.addWidget(self._mw.curr_pos_get_pos_PushButton, 0, 2, extension, 1)
        self._mw.curr_pos_get_pos_PushButton.clicked.connect(self.update_pos)

    def _create_move_rel_control(self):
        """ Create all the gui elements to control a relative movement.

        The generic variable name for a created QLable is:
            move_rel_axis{0}_Label
        The generic variable name for a created QDoubleSpinBox is:
            move_rel_axis{0}_DoubleSpinBox
        The generic variable name for a created QPushButton in negative dir is:
            move_rel_axis{0}_m_PushButton
        The generic variable name for a created QPushButton in positive dir is:
            move_rel_axis{0}_p_PushButton

        DO NOT CALL THESE VARIABLES DIRECTLY! USE THE DEDICATED METHOD INSTEAD!
        Use the method get_ref_move_rel_DoubleSpinBox with the appropriated
        label, otherwise you will break the generality.
        """

        constraints = self._magnet_logic.get_hardware_constraints()

        # set the axis_labels in the curr_pos_DockWidget:
        for index, axis_label in enumerate(constraints):

            label_var_name = 'move_rel_axis{0}_Label'.format(axis_label)
            setattr(self._mw, label_var_name, QtGui.QLabel(self._mw.move_rel_DockWidgetContents))
            label_var = getattr(self._mw, label_var_name) # get the reference
            # set axis_label for the label:
            label_var.setObjectName(label_var_name)
            label_var.setText(axis_label)
            # add the label to the grid:
            self._mw.move_rel_GridLayout.addWidget(label_var, index, 0, 1, 1)

            # Set the QDoubleSpinBox according to the grid
            # this is the name prototype for the relative movement display
            dspinbox_var_name = 'move_rel_axis{0}_DoubleSpinBox'.format(axis_label)
            setattr(self._mw, dspinbox_var_name, QtGui.QDoubleSpinBox(self._mw.move_rel_DockWidgetContents))
            dspinbox_var = getattr(self._mw, dspinbox_var_name)
            dspinbox_var.setObjectName(dspinbox_var_name)
#            dspinbox_var.setButtonSymbols(QtGui.QAbstractSpinBox.NoButtons)
            dspinbox_var.setMaximum(constraints[axis_label]['pos_max'])
            dspinbox_var.setMinimum(constraints[axis_label]['pos_min'])
            #TODO: set the decimals also from the constraints!
            dspinbox_var.setDecimals(3)
            dspinbox_var.setSingleStep(constraints[axis_label]['pos_step'])
            self._mw.move_rel_GridLayout.addWidget(dspinbox_var, index, 1, 1, 1)


            # this is the name prototype for the relative movement minus button
            func_name = '_move_rel_axis{0}_m'.format(axis_label)
            # create a method and assign it as attribute:
            setattr(self, func_name, self._function_builder_move_rel(func_name,axis_label,-1) )
            move_rel_m_ref =  getattr(self, func_name)  # get the reference

            # the change of the PushButton is connected to the previous method.
            button_var_name = 'move_rel_axis{0}_m_PushButton'.format(axis_label)
            setattr(self._mw, button_var_name, QtGui.QPushButton(self._mw.move_rel_DockWidgetContents))
            button_var = getattr(self._mw, button_var_name)
            button_var.setObjectName(button_var_name)
            button_var.setText('-')
            button_var.clicked.connect(move_rel_m_ref, type=QtCore.Qt.QueuedConnection)
            self._mw.move_rel_GridLayout.addWidget(button_var, index, 2, 1, 1)

            # this is the name prototype for the relative movement plus button
            func_name = '_move_rel_axis{0}_p'.format(axis_label)
            setattr(self, func_name, self._function_builder_move_rel(func_name,axis_label,1) )
            move_rel_p_ref =  getattr(self, func_name)

            # the change of the PushButton is connected to the previous method.
            button_var_name = 'move_rel_axis{0}_p_PushButton'.format(axis_label)
            setattr(self._mw, button_var_name, QtGui.QPushButton(self._mw.move_rel_DockWidgetContents))
            button_var = getattr(self._mw, button_var_name)
            button_var.setObjectName(button_var_name)
            button_var.setText('+')
            button_var.clicked.connect(move_rel_p_ref, type=QtCore.Qt.QueuedConnection)
            self._mw.move_rel_GridLayout.addWidget(button_var, index, 3, 1, 1)

    def _create_move_abs_control(self):
        """ Create all the GUI elements to control a relative movement.

        The generic variable name for a created QLable is:
            move_rel_axis{0}_Label
        The generic variable name for a created QLable is:
            move_abs_axis{0}_Slider
        The generic variable name for a created QDoubleSpinBox is:
            move_abs_axis{0}_DoubleSpinBox
        The generic variable name for a created QPushButton for move is:
            move_abs_PushButton

        DO NOT CALL THESE VARIABLES DIRECTLY! USE THE DEDICATED METHOD INSTEAD!
        Use the method get_ref_move_abs_DoubleSpinBox with the appropriated
        label, otherwise you will break the generality.
        """

        constraints = self._magnet_logic.get_hardware_constraints()

        for index, axis_label in enumerate(constraints):

            label_var_name = 'move_abs_axis{0}_Label'.format(axis_label)
            setattr(self._mw, label_var_name, QtGui.QLabel(self._mw.move_abs_DockWidgetContents))
            label_var = getattr(self._mw, label_var_name) # get the reference
            # set axis_label for the label:
            label_var.setObjectName(label_var_name)
            label_var.setText(axis_label)
            # add the label to the grid:
            self._mw.move_abs_GridLayout.addWidget(label_var, index, 0, 1, 1)

            # Set the QDoubleSpinBox according to the grid
            # this is the name prototype for the relative movement display
            slider_obj_name = 'move_abs_axis{0}_Slider'.format(axis_label)
            setattr(self._mw, slider_obj_name, QtGui.QSlider(self._mw.move_abs_DockWidgetContents))
            slider_obj = getattr(self._mw, slider_obj_name)
            slider_obj.setObjectName(slider_obj_name)
            slider_obj.setOrientation(QtCore.Qt.Horizontal)
#            dspinbox_var.setButtonSymbols(QtGui.QAbstractSpinBox.NoButtons)

            max_val = abs(constraints[axis_label]['pos_max'] - constraints[axis_label]['pos_min'])

            max_steps = int(max_val/constraints[axis_label]['pos_step'])

            slider_obj.setMaximum(max_steps)
            slider_obj.setMinimum(0)
            #TODO: set the decimals also from the constraints!
#            slider_obj.setDecimals(3)
            slider_obj.setSingleStep(1)
            slider_obj.setEnabled(False)

            self._mw.move_abs_GridLayout.addWidget(slider_obj, index, 1, 1, 1)

            # Set the QDoubleSpinBox according to the grid
            # this is the name prototype for the relative movement display
            dspinbox_var_name = 'move_abs_axis{0}_DoubleSpinBox'.format(axis_label)
            setattr(self._mw, dspinbox_var_name, QtGui.QDoubleSpinBox(self._mw.move_abs_DockWidgetContents))
            dspinbox_var = getattr(self._mw, dspinbox_var_name)
            dspinbox_var.setObjectName(dspinbox_var_name)
#            dspinbox_var.setButtonSymbols(QtGui.QAbstractSpinBox.NoButtons)
            dspinbox_var.setMaximum(constraints[axis_label]['pos_max'])
            dspinbox_var.setMinimum(constraints[axis_label]['pos_min'])
            #TODO: set the decimals also from the constraints!
            dspinbox_var.setDecimals(3)
            dspinbox_var.setSingleStep(constraints[axis_label]['pos_step'])
            self._mw.move_abs_GridLayout.addWidget(dspinbox_var, index, 2, 1, 1)


        # TODO: connect the slider move with the doublespinbox value.
        # TODO: Update after get pos the sliders.
        # TODO: connect the doublespinbox change with the slider

        extension =  len(constraints)
        self._mw.move_abs_GridLayout.addWidget(self._mw.move_abs_PushButton, 0, 3, extension, 1)
        self._mw.move_abs_PushButton.clicked.connect(self.move_abs)

    def _function_builder_move_rel(self, func_name, axis_label, direction):
        """ Create a function/method, which gots executed for pressing move_rel.

        @param str func_name: name how the function should be called.
        @param str axis_label: label of the axis you want to create a control
                               function for.
        @param int direction: either 1 or -1 depending on the relative movement.
        @return: function with name func_name

        A routine to construct a method on the fly and attach it as attribute
        to the object, so that it can be used or so that other signals can be
        connected to it. That means the return value is already fixed for a
        function name.
        """

        def func_dummy_name():
            self.move_rel(axis_label, direction)

        func_dummy_name.__name__ = func_name
        return func_dummy_name

        # create the signals for the push buttons and connect them to the move
        # rel method in the Logic

    def move_rel(self, axis_label, direction):
        """ Move relative by the axis with given label an direction.

        @param str axis_label: tells which axis should move.
        @param int direction: either 1 or -1 depending on the relative movement.

        That method get called from methods, which are created on the fly at
        runtime during the activation of that module (basically from the
        methods with the generic name _move_rel_axis{0} or
        _por _move_rel_axis{0}_m with the appropriate label).
        """

        dspinbox = self.get_ref_move_rel_DoubleSpinBox(axis_label)
        movement = dspinbox.value() * direction

#        self.sigMoveRel.emit({axis_label:movement})
        self._magnet_logic.move_rel({axis_label:movement})
        if self._interactive_mode:
            self.update_pos()

    def move_abs(self, param_dict=None):
        """ Perform an absolute movement.

        @param param_dict: with {<axis_label>:<position>}, can of course
                           contain many entries of the same kind.

        Basically all the axis can be controlled at the same time.
        """

        if (param_dict is not None) and (type(param_dict) is not bool):
            self._magnet_logic.move_abs(param_dict)
        else:
            constraints = self._magnet_logic.get_hardware_constraints()
            move_abs = {}
            for label in constraints:
                move_abs[label] = self.get_ref_move_abs_DoubleSpinBox(label).value()

            self._magnet_logic.move_abs(move_abs)

        if self._interactive_mode:
            self.update_pos()


    def get_ref_curr_pos_DoubleSpinBox(self, label):
        """ Get the reference to the double spin box for the passed label. """

        dspinbox_name = 'curr_pos_axis{0}_DoubleSpinBox'.format(label)
        dspinbox_ref = getattr(self._mw, dspinbox_name)
        return dspinbox_ref

    def get_ref_move_rel_DoubleSpinBox(self, label):
        """ Get the reference to the double spin box for the passed label. """

        dspinbox_name = 'move_rel_axis{0}_DoubleSpinBox'.format(label)
        dspinbox_ref = getattr(self._mw, dspinbox_name)
        return dspinbox_ref

    def get_ref_move_abs_DoubleSpinBox(self, label):
        """ Get the reference to the double spin box for the passed label. """
        
        dspinbox_name = 'move_abs_axis{0}_DoubleSpinBox'.format(label)
        dspinbox_ref = getattr(self._mw, dspinbox_name)
        return dspinbox_ref

#    def reset_move_abs_display(self):
#        """ After pressing the get position method, the slider and the
#        positions should be set to those. """

    def update_pos(self, param_list=None):
        """ Update the current position.

        @param dict param_dict: optional, if specific positions needed to be
                                updated.

        If no value is passed, the current possition is retrieved from the
        logic and the display is changed.
        """


        curr_pos =  self._magnet_logic.get_pos()

        if (param_list is not None) and (type(param_list) is not bool):
            curr_pos =  self._magnet_logic.get_pos(param_list)

        for entry in curr_pos:
            # this is the name prototype for the current position display
            dspinbox_var_name = 'curr_pos_axis{0}_DoubleSpinBox'.format(entry)
            dspinbox_var = getattr(self._mw, dspinbox_var_name)
            dspinbox_var.setValue(curr_pos[entry])

