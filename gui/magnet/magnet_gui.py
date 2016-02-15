# -*- coding: utf-8 -*-

"""
This file contains the dummy for a motorized stage interface.

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
        ui_file = os.path.join(this_dir, 'magnet_gui.ui')

        # Load it
        super(MagnetMainWindow, self).__init__()
        uic.loadUi(ui_file, self)
        self.show()

class MagnetGui(GUIBase):
    """ Main GUI for the magnet. """

    _modclass = 'magnetgui'
    _modtype = 'gui'

    ## declare connectors
    _in = {'magnetlogic1': 'MagnetLogic'}


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
        """ Definition and initialisation of the GUI plus staring the measurement.
        """
        self._magnet_logic = self.connector['in']['magnetlogic1']['object']

        # self._magnet_logic.sigPosChanged.connect(self.update_pos)

        self._mw = MagnetMainWindow()
        self._create_axis_pos_disp()
        self._create_move_rel_control()

        # Configuring the dock widgets
        # Use the class 'MagnetMainWindow' to create the GUI window


        # Setup dock widgets
        self._mw.centralwidget.hide()
        self._mw.setDockNestingEnabled(True)

        self._mw.tabifyDockWidget(self._mw.curr_pos_DockWidget, self._mw.move_rel_DockWidget)
        self._mw.tabifyDockWidget(self._mw.curr_pos_DockWidget, self._mw.move_abs_DockWidget)
        # self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(1), self._mw.curr_pos_DockWidget)
        # self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(1), self._mw.move_rel_DockWidget)
        # self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(1), self._mw.move_abs_DockWidget)



    def deactivation(self, e=None):
        self._mw.close()

    def show(self):
        """Make window visible and put it above all other windows.
        """
        QtGui.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

    def _create_axis_pos_disp(self):
        """ Create the axis position display.

        The generic variable name for a created QLable is:
            curr_pos_axis_{0}_Label
        The generic variable name for a created QDoubleSpinBox is:
            curr_pos_axis_{0}_DoubleSpinBox
        where in {0} the name of the axis will be inserted.

        DO NOT CALL THESE VARIABLES DIRECTLY! USE THE DEDICATED METHOD INSTEAD!
        Otherwise you will break the generality.
        """

        constraints = self._magnet_logic.get_hardware_constraints()

#        param = OrderedDict()
#        param['x'] = {'pos_min': 0, 'pos_max':200, 'pos_step': 0.1}
#        param['y'] = {'pos_min': 0, 'pos_max':50, 'pos_step':0.2}
#        param['z'] = {'pos_min': 0, 'pos_max':50, 'pos_step':0.2}
#        param['phi'] = {'pos_min': 0, 'pos_max':50, 'pos_step':0.2}
#
#        constraints = param

        # set the parameters in the curr_pos_DockWidget:
        for index, parameter in enumerate(constraints):

            # Set the QLabel according to the grid
            # this is the name prototype for the label of current position display
            label_var_name = 'curr_pos_axis_{0}_Label'.format(parameter)
            setattr(self._mw, label_var_name, QtGui.QLabel(self._mw.curr_pos_DockWidgetContents))
            label_var = getattr(self._mw, label_var_name)
            label_var.setObjectName(label_var_name)
            label_var.setText(parameter)
            self._mw.curr_pos_GridLayout.addWidget(label_var, index, 0, 1, 1)

            # Set the QDoubleSpinBox according to the grid
            # this is the name prototype for the current position display
            dspinbox_var_name = 'curr_pos_axis_{0}_DoubleSpinBox'.format(parameter)
            setattr(self._mw, dspinbox_var_name, QtGui.QDoubleSpinBox(self._mw.curr_pos_DockWidgetContents))
            dspinbox_var = getattr(self._mw, dspinbox_var_name)
            dspinbox_var.setObjectName(dspinbox_var_name)
            dspinbox_var.setReadOnly(True)
            dspinbox_var.setButtonSymbols(QtGui.QAbstractSpinBox.NoButtons)
            dspinbox_var.setMaximum(np.inf)
            dspinbox_var.setMinimum(-np.inf)
            dspinbox_var.setSingleStep(constraints[parameter]['pos_step'])

            self._mw.curr_pos_GridLayout.addWidget(dspinbox_var, index, 1, 1, 1)

    def _create_move_rel_control(self):
        """ Create all the gui elements to control a relative movement.

        The generic variable name for a created QLable is:
            move_rel_axis_{0}_Label
        The generic variable name for a created QDoubleSpinBox is:
            move_rel_axis_{0}_DoubleSpinBox
        The generic variable name for a created QPushButton in negative dir is:
            move_rel_axis_{0}_m_PushButton
        The generic variable name for a created QPushButton in positive dir is:
            move_rel_axis_{0}_p_PushButton

        DO NOT CALL THESE VARIABLES DIRECTLY! USE THE DEDICATED METHOD INSTEAD!
        Otherwise you will break the generality.
        """

        constraints = self._magnet_logic.get_hardware_constraints()

#        param = OrderedDict()
#        param['x'] = {'pos_min': 0, 'pos_max':200, 'pos_step': 0.1}
#        param['y'] = {'pos_min': 0, 'pos_max':50, 'pos_step':0.2}
#        param['z'] = {'pos_min': 0, 'pos_max':50, 'pos_step':0.2}
#        param['phi'] = {'pos_min': 0, 'pos_max':50, 'pos_step':0.2}

#        constraints = param

        # set the parameters in the curr_pos_DockWidget:
        for index, parameter in enumerate(constraints):

            label_var_name = 'move_rel_axis_{0}_Label'.format(parameter)
            setattr(self._mw, label_var_name, QtGui.QLabel(self._mw.move_rel_DockWidgetContents))
            label_var = getattr(self._mw, label_var_name) # get the reference
            # set parameter for the label:
            label_var.setObjectName(label_var_name)
            label_var.setText(parameter)
            # add the label to the grid:
            self._mw.move_rel_GridLayout.addWidget(label_var, index, 0, 1, 1)

            # Set the QDoubleSpinBox according to the grid
            # this is the name prototype for the relative movement display
            dspinbox_var_name = 'move_rel_axis_{0}_DoubleSpinBox'.format(parameter)
            setattr(self._mw, dspinbox_var_name, QtGui.QDoubleSpinBox(self._mw.move_rel_DockWidgetContents))
            dspinbox_var = getattr(self._mw, dspinbox_var_name)
            dspinbox_var.setObjectName(dspinbox_var_name)
#            dspinbox_var.setButtonSymbols(QtGui.QAbstractSpinBox.NoButtons)
            dspinbox_var.setMaximum(constraints[parameter]['pos_max'])
            dspinbox_var.setMinimum(constraints[parameter]['pos_min'])
            dspinbox_var.setDecimals(3)
            dspinbox_var.setSingleStep(constraints[parameter]['pos_step'])
            self._mw.move_rel_GridLayout.addWidget(dspinbox_var, index, 1, 1, 1)


            # this is the name prototype for the relative movement minus button
            func_name = '_move_rel_axis_{0}_m'.format(parameter)
            # create a method and assign it as attribute:
            setattr(self, func_name, self._function_builder(func_name,parameter,-1) )
            move_rel_m_ref =  getattr(self, func_name)  # get the reference

            # the change of the PushButton is connected to the previous method.
            button_var_name = 'move_rel_axis_{0}_m_PushButton'.format(parameter)
            setattr(self._mw, button_var_name, QtGui.QPushButton(self._mw.move_rel_DockWidgetContents))
            button_var = getattr(self._mw, button_var_name)
            button_var.setObjectName(button_var_name)
            button_var.setText('-')
            button_var.clicked.connect(move_rel_m_ref)
            self._mw.move_rel_GridLayout.addWidget(button_var, index, 2, 1, 1)


            # this is the name prototype for the relative movement plus button
            func_name = '_move_rel_axis_{0}_p'.format(parameter)
            setattr(self, func_name, self._function_builder(func_name,parameter,1) )
            move_rel_p_ref =  getattr(self, func_name)

            # the change of the PushButton is connected to the previous method.
            button_var_name = 'move_rel_axis_{0}_p_PushButton'.format(parameter)
            setattr(self._mw, button_var_name, QtGui.QPushButton(self._mw.move_rel_DockWidgetContents))
            button_var = getattr(self._mw, button_var_name)
            button_var.setObjectName(button_var_name)
            button_var.setText('+')
            button_var.clicked.connect(move_rel_p_ref)
            self._mw.move_rel_GridLayout.addWidget(button_var, index, 3, 1, 1)


    def _function_builder(self, func_name, parameter, direction):
        def func_dummy_name():
            self.move_rel(parameter,direction)

        func_dummy_name.__name__ = func_name
        return func_dummy_name

        # create the signals for the push buttons and connect them to the move
        # rel method in the Logic

    def move_rel(self, axis_label, direction):

        self.logMsg('Axislabel: {0}, direction: {1}'.format(axis_label,direction) ,msgType='status')



    def get_ref_curr_pos_DoubleSpinBox(self, label):
        """ Get the reference to the double spin box for the passed label. """
        dspinbox_name = 'curr_pos_axis_{0}_DoubleSpinBox'.format(label)
        dspinbox_ref = getattr(self._mw, dspinbox_name)
        return dspinbox_ref

    def get_ref_move_rel_DoubleSpinBox(self, label):
        """ Get the reference to the double spin box for the passed label. """
        dspinbox_name = 'move_rel_axis_{0}_DoubleSpinBox'.format(label)
        dspinbox_ref = getattr(self._mw, dspinbox_name)
        return dspinbox_ref

    def update_pos(self, param_dict=None):
        """ Update the current position.

        @param dict param_dict: optional, if you want to update specific
                                positions.

        If no value is passed, the current possition is retrieved from the
        logic and the display is changed.
        """

        if param_dict is not None:
            param_dict = self._magnet_logic.get_pos()

        for entry in param_dict:
            # this is the name prototype for the current position display
            dspinbox_var_name = 'curr_pos_axis_{0}_DoubleSpinBox'.format(entry)
            dspinbox_var = getattr(self._mw, dspinbox_var_name)
            dspinbox_var.setValue(param_dict[entry])

