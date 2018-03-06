# -*- coding: utf-8 -*-

"""
This file contains a widget for fit parameters.

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
from qtpy import QtCore, QtGui, QtWidgets
from collections import OrderedDict
from qtwidgets.scientific_spinbox import ScienDSpinBox
import numpy as np
import math

import logging
logger = logging.getLogger(__name__)


class FitSettingsDialog(QtWidgets.QDialog):
    """ A dialog that is used to configure the fits in a FitContainer. """
    sigFitsUpdated = QtCore.Signal(dict)

    def __init__(self, fit_container):
        """ Create a FitSettingsDialog for a matching FitContainer.
            @param fit_container FitContainer: the FitContainer that this dialog should manipulate
        """
        super().__init__()

        self.fc = fit_container
        self.title = '{0} fit settings'.format(self.fc.name)

        # set up window
        self.setModal(False)
        self.setWindowTitle(self.title)

        # variables
        self.all_functions = self.fc.fit_logic.fit_list[self.fc.dimension]
        self.tabs = {}
        self.parameters = {}
        self.parameterUse = {}
        self.currentFits = OrderedDict()
        self.fitWidgets = OrderedDict()
        self.currentFitWidgets = OrderedDict()

        # widgets and layouts
        self._dialogLayout = QtWidgets.QVBoxLayout()
        self._btnLayout = QtWidgets.QHBoxLayout()
        self._tabWidget = QtWidgets.QTabWidget()
        self._firstPage = QtWidgets.QWidget()
        self._firstPageLayout = QtWidgets.QVBoxLayout()
        self._scrollArea = QtWidgets.QScrollArea()
        self._scrollWidget = QtWidgets.QWidget()
        self._scrLayout = QtWidgets.QVBoxLayout()
        self._dbox = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok
                | QtWidgets.QDialogButtonBox.Apply
                | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal
        )
        self._addFitButton = QtWidgets.QPushButton('Add fit')
        self._saveFitButton = QtWidgets.QPushButton('Save fits')
        self._loadFitButton = QtWidgets.QPushButton('Load fits')

        # layout construction
        self._scrollWidget.setLayout(self._scrLayout)
        self._scrollArea.setWidget(self._scrollWidget)
        self._scrollArea.setWidgetResizable(True)
        self._btnLayout.addWidget(self._addFitButton)
        self._btnLayout.addWidget(self._saveFitButton)
        self._btnLayout.addWidget(self._loadFitButton)
        self._firstPageLayout.addLayout(self._btnLayout)
        self._firstPageLayout.addWidget(self._scrollArea)
        self._firstPage.setLayout(self._firstPageLayout)
        self._tabWidget.addTab(self._firstPage, 'Fit functions')
        self._dialogLayout.addWidget(self._tabWidget)
        self._dialogLayout.addWidget(self._dbox)
        self.setLayout(self._dialogLayout)

        # connections
        self._dbox.accepted.connect(self.accept)
        self._dbox.rejected.connect(self.reject)
        self._dbox.clicked.connect(self.buttonClicked)
        self.accepted.connect(self.applySettings)
        self.rejected.connect(self.resetSettings)
        self._addFitButton.clicked.connect(self.addFitButtonClicked)
        self._loadFitButton.clicked.connect(self.loadFitButtonClicked)
        self._saveFitButton.clicked.connect(self.saveFitButtonClicked)
        self.sigFitsUpdated.connect(self.fc.set_fit_functions)
        self.fc.sigNewFitParameters.connect(self.updateParameters)

        # load user defined fits from fit container
        if len(self.fc.fit_list) > 0:
            self.loadFits(self.fc.fit_list)

    @QtCore.Slot(QtWidgets.QAbstractButton)
    def buttonClicked(self, button):
        """ Slot for signals from dialog button box.
            @param button QAbstractButton: designates which button was clicked.
        """
        if self._dbox.buttonRole(button) ==  QtWidgets.QDialogButtonBox.ApplyRole:
            self.applySettings()

    @QtCore.Slot()
    def addFitButtonClicked(self):
        """ The 'Add Fit' button was clicked. Display a name input dialog and add the fit. """
        res = QtWidgets.QInputDialog.getText(
            self,
            'New fit',
            'Enter a name for this fit:',
            )
        if res[1]:
            self.addFit(res[0])

    @QtCore.Slot()
    def saveFitButtonClicked(self):
        """ The 'Save Fits' button was clicked. Display file chooser and save fits to file. """
        res = QtWidgets.QFileDialog.getSaveFileName(
            self,
            'Save fit collection for {0}'.format(self.title),
            '/path',
            'Fit files (*.fit *.yml)'
            )
        self.fc.fit_logic.save_fits(res[0], {self.fc.dimension: self.fc.fit_list})

    @QtCore.Slot()
    def loadFitButtonClicked(self):
        """ The 'Load Fits' button was clicked. Display file chooser and load fits from file. """
        res = QtWidgets.QFileDialog.getOpenFileName(
            self,
            'Load fit collection for {0}'.format(self.title),
            '/path',
            'Fit files (*.fit *.yml)'
            )
        fits = self.fc.fit_logic.load_fits(res[0])
        self.loadFits(fits[self.fc.dimension])

    def loadFits(self, user_fits):
        """ Take a fit config dictionary and create widgets for the fits inside.
            @param user_fits dict: configured fits dictionary
        """
        self.removeAllFits()
        self.applySettings()

        for name, fit in user_fits.items():
            self.addFit(name, fit=fit['fit_name'], estimator=fit['est_name'])

            # add new tab for new fit
            model, params = self.all_functions[fit['fit_name']]['make_model']()
            self.tabs[name] = FitParametersWidget(params)
            self._tabWidget.addTab(self.tabs[name], name)
            self.updateParameters(name, fit['parameters'])
        # build fit list and send update signals
        self.applySettings()

    def addFit(self, name, fit=None, estimator=None):
        """ Add a new fit to the dialog.
            @param name str: configured name for fit
            @param fit str: name of the fit function for this fit
            @param estimator str: name of the estimator function for this fit
        """
        if len(name) < 1:
            return
        if name in self.fitWidgets:
            logging.error('{0}: Fit {1} already exists.'.format(self.title, name))
            return
        fcw = FitConfigWidget(name, self.all_functions, fit, estimator)
        self.currentFitWidgets[name] = fcw
        self._scrLayout.addWidget(fcw)
        fcw.sigRemoveFit.connect(self.removeFit)
        fcw.show()

    @QtCore.Slot(str)
    def removeFit(self, name):
        """ Remove a fit from the dialog. Hides the FitonfigWidet and disables the parameter tab.
            @param name str: name of fit to remove
        """
        widget = self.currentFitWidgets.pop(name)
        widget.hide()
        self._scrLayout.removeWidget(widget)
        tab = self.tabs[name]
        tab.setEnabled(False)

    def removeAllFits(self):
        """ Remove all configured fits from dialog.
        """
        for name in self.currentFits.keys():
            self.removeFit(name)

    def getFits(self):
        """ Return all configured fits from this dialog.
        """
        return self.currentFits

    def applySettings(self):
        """ Apply all settings that the user has made in the dialog and send out update signals.

        This copies all input widget values to thei coresponding internal data structures,
        creates an removes widgets and parameter tabs.
        """
        # remove all settings tabs and config widgets that the user removed
        for name, widget in self.fitWidgets.items():
            if name not in self.currentFitWidgets:
                tab = self.tabs.pop(name)
                index = self._tabWidget.indexOf(tab)
                if index >= 0:
                    self._tabWidget.removeTab(index)
                self._scrLayout.removeWidget(widget)

        self.fitWidgets = OrderedDict()

        # add tabs for new fits, replace tabs for changed fits
        for name, widget in self.currentFitWidgets.items():
            oldfit = widget.fit
            oldest = widget.estimator
            widget.applySettings()

            if name in self.tabs and widget.fit != oldfit:
                # remove old tab, add new tab, preferably in the same place, for changed fit
                tab = self.tabs.pop(name)
                index = self._tabWidget.indexOf(tab)
                if index >= 0:
                    self._tabWidget.removeTab(index)
                model, params = self.all_functions[widget.fit]['make_model']()
                self.tabs[name] = FitParametersWidget(params)
                if index >= 0:
                    self._tabWidget.insertTab(index, self.tabs[name], name)
                else:
                    self._tabWidget.addTab(self.tabs[name], name)

            elif name not in self.tabs:
                # add new tab for new fir
                model, params = self.all_functions[widget.fit]['make_model']()
                self.tabs[name] = FitParametersWidget(params)
                self._tabWidget.addTab(self.tabs[name], name)

            # put all widgets here
            self.fitWidgets[name] = widget

        # reset update tabs and put new values in dict
        self.parameters = {}
        self.parameterUse = {}

        for name, tab in self.tabs.items():
            self.parameters[name], self.parameterUse[name] = tab.applyFitParameters()

        self.buildCurrentFits()
        self.sigFitsUpdated.emit(self.currentFits)

    def buildCurrentFits(self):
        """ Update dictionary of the configured fits for FitContainer or other componenrs.
        """
        # arrange all of this information in a convenient form
        self.currentFits = OrderedDict()
        for name, widget in self.fitWidgets.items():
            try:
                self.currentFits[name] = {
                    'fit_name': widget.fit,
                    'est_name': widget.estimator,
                    'make_fit': self.all_functions[widget.fit]['make_fit'],
                    'make_model': self.all_functions[widget.fit]['make_model'],
                    'estimator': self.all_functions[widget.fit][widget.estimator],
                    'parameters': self.parameters[name]
                }
            except KeyError:
                continue

    def resetSettings(self):
        """ Reset all input widgets to their stored values, discarding changes by the user.
        """
        for name, widget in self.currentFitWidgets.items():
            if name not in self.fitWidgets:
                self._scrLayout.removeWidget(widget)

        self.currentFitWidgets = OrderedDict()
        for name, widget in self.fitWidgets.items():
            widget.resetSettings()
            widget.show()
            self.currentFitWidgets[name] = widget

        # reset tabs, do not update dicts
        for name, tab in self.tabs.items():
            tab.setEnabled(True)
            tab.resetFitParameters()

    def getParameters(self, fit_name):
        """ Return Parameters object for a given fit.
            @param fit_name str: name of the fit

            @return Parameters: lmfit parameters container
        """
        return self.parameters[fit]

    def updateParameters(self, fit_name, parameters):
        """ Update parameters of a given fit.
            @param fit_name str: name of fit
            @param parameters Parameters: lmfit Parameters container

        This function updates all parameters for a fit that the dialog has stored and ingores
        any other parameters in he parameter container.
        """
        if fit_name in self.parameters:
            for name, param in parameters.items():
                if name in self.parameters[fit_name]:
                    self.parameters[fit_name][name] = param
            self.tabs[fit_name].updateFitParameters(parameters)


class FitSettingsComboBox(QtWidgets.QComboBox):
    """ A QComboBox for use with FitContainer. """

    sigFitUpdated = QtCore.Signal(tuple)

    def __init__(self, *args, **kwargs):
        """ Create a FitSettingxComboBox.
            @param args list(): positional arguments passed to QComboBox
            @param kwargs dict(): keyword arguments passed to QComboBox
        """
        super().__init__(*args, **kwargs)
        self.fit_functions = OrderedDict()
        self.fit_functions['No Fit'] = None
        self.addItem('No Fit')
        self.setCurrentIndex(self.findText('No Fit'))

    @QtCore.Slot(dict)
    def setFitFunctions(self, user_fits):
        """ Set the fit functions that can be chosen in this combobox
            @param user_fits dict: fit dictionary of configured fits
        """
        current = self.getCurrentFit()
        self.clear()
        self.fit_functions = OrderedDict()
        self.fit_functions['No Fit'] = None
        self.addItem('No Fit')

        for name, fit in user_fits.items():
            self.fit_functions[name] = fit
            self.addItem(name)

        self.setCurrentFit(current[0])

    def getCurrentFit(self):
        """ Return name and fit dictionary for the current fit.

            @return tuple(str, dict): name nad fit dict for current fit
        """
        name = self.currentText()
        return (name, self.fit_functions[name])

    def setCurrentFit(self, name):
        """ Set current fit by name. 'No Fit' if the name is invalid.
            @param name str: name of the fit to be set as current fit
        """
        if name in self.fit_functions:
            self.setCurrentIndex(self.findText(name))
        else:
            self.setCurrentIndex(self.findText('No Fit'))


class FitConfigWidget(QtWidgets.QWidget):
    """ A widget that contains a fit function combobox, an estimator combobox and a remove button.
    """

    sigRemoveFit = QtCore.Signal(str)

    def __init__(self, name, all_fits, fit=None, estimator=None):
        """ Create a FitConfigWidget.
            @param name str: name of the fit
            @param all_fits dict: dict of all fits, their estimators and parameters
            @param fit str: optional name of fit function to be selected
            @param etimator str: optional name of estimator to be selected
        """
        super().__init__()
        self.name = name
        self.fit = ''
        self.estimator = ''
        self.all_fits = all_fits

        self.nameLabel = QtWidgets.QLabel(name)
        self.fitComboBox = QtWidgets.QComboBox()
        self.estComboBox = QtWidgets.QComboBox()
        self.delButton = QtWidgets.QToolButton()

        self.delIcon = QtGui.QIcon()
        self.delIcon.addFile('artwork/icons/oxygen/22x22/edit-delete.png')
        self.delButton.setIcon(self.delIcon)

        self._layout = QtWidgets.QHBoxLayout()
        self._layout.addWidget(self.nameLabel)
        self._layout.addWidget(self.fitComboBox)
        self._layout.addWidget(self.estComboBox)
        self._layout.addWidget(self.delButton)

        self.setLayout(self._layout)

        for name, afit in self.all_fits.items():
            if 'make_fit' in afit and 'make_model' in afit:
                self.fitComboBox.addItem(name)

        if fit is not None and fit in all_fits:
            self.fitComboBox.setCurrentIndex(self.fitComboBox.findText(fit))
            self.fitChanged(self.fitComboBox.findText(fit))
            if estimator is not None and estimator in all_fits[fit]:
                self.estComboBox.setCurrentIndex(self.estComboBox.findText(estimator))
                self.estimatorChanged(self.estComboBox.findText(estimator))
                self.applySettings()

        elif self.fitComboBox.count() > 0:
            self.fitChanged(self.fitComboBox.currentIndex())
            if self.estComboBox.count() > 0:
                self.estimatorChanged(self.estComboBox.currentIndex())

        self.fitComboBox.activated.connect(self.fitChanged)
        self.estComboBox.activated.connect(self.estimatorChanged)
        self.delButton.clicked.connect(self.removeWidget)

    @QtCore.Slot(int)
    def fitChanged(self, index):
        """ The fit changed, update the estimator ComboBox.
            @param index int: index of the new selected fit
        """
        name = self.fitComboBox.itemText(index)
        self.estComboBox.clear()
        for estimator in self.all_fits[name]:
            if not estimator.startswith('make_'):
                self.estComboBox.addItem(estimator)

    @QtCore.Slot(int)
    def estimatorChanged(self, index):
        """ Estimator changed. Nothing really needs to happen.
        """
        name = self.estComboBox.itemText(index)
        # FIXME: remove this maybe?

    def applySettings(self):
        """ Copy widget contents to internal variables.
        """
        self.fit = self.fitComboBox.currentText()
        self.estimator = self.estComboBox.currentText()

    def resetSettings(self):
        """ Restore widget contents from external variable.
        """
        self.fitComboBox.setCurrentIndex(self.fitComboBox.findText(self.fit))
        self.fitChanged(self.fitComboBox.findText(self.fit))
        self.estComboBox.setCurrentIndex(self.estComboBox.findText(self.estimator))
        self.estimatorChanged(self.estComboBox.findText(self.estimator))

    @QtCore.Slot()
    def removeWidget(self):
        """ Remove button pressed, hide widget and send signal for removal.
        """
        self.hide()
        self.sigRemoveFit.emit(self.name)


class FitParametersWidget(QtWidgets.QWidget):
    """ A widget that manages the parameters for a fit. """

    def __init__(self, parameters):
        """ Definition, configuration and initialisation of the optimizer settings GUI. Adds a row
            with the value, min, max and vary for each variable in parameters.
            @param parameters Parameters: lmfit parameters collection to be displayed here
        """
        super().__init__()

        self.parameters = parameters

        # create labels and layout
        self._layout = QtWidgets.QGridLayout(self)
        self.useLabel = QtWidgets.QLabel('Edit?')
        self.valueLabel = QtWidgets.QLabel('Value')
        self.minimumLabel = QtWidgets.QLabel('Minimum')
        self.maximumLabel = QtWidgets.QLabel('Maximum')
        self.exprLabel = QtWidgets.QLabel('Expression')
        self.varyLabel = QtWidgets.QLabel('Vary?')

        # add labels to layout
        self._layout.addWidget(self.useLabel, 0, 0)
        self._layout.addWidget(self.valueLabel, 0, 2)
        self._layout.addWidget(self.minimumLabel, 0, 3)
        self._layout.addWidget(self.maximumLabel, 0, 4)
        self._layout.addWidget(self.exprLabel, 0, 5)
        self._layout.addWidget(self.varyLabel, 0, 6)

        # create all parameter fields and add to layout
        self.widgets = {}
        self.paramUseSettings = {}
        n = 2
        for name, param in parameters.items():
            self.paramUseSettings[name] = False
            self.widgets[name + '_use'] = useCheckbox = QtWidgets.QCheckBox()
            self.widgets[name + '_label'] = parameterNameLabel = QtWidgets.QLabel(str(name))
            self.widgets[name + '_value'] = valueSpinbox = ScienDSpinBox()
            self.widgets[name + '_min'] = minimumSpinbox = ScienDSpinBox()
            self.widgets[name + '_max'] = maximumSpinbox = ScienDSpinBox()
            self.widgets[name + '_expr'] = expressionLineEdit = QtWidgets.QLineEdit()
            self.widgets[name + '_vary'] = varyCheckbox = QtWidgets.QCheckBox()
            valueSpinbox.setMaximum(np.inf)
            valueSpinbox.setMinimum(-np.inf)
            minimumSpinbox.setMaximum(np.inf)
            minimumSpinbox.setMinimum(-np.inf)
            maximumSpinbox.setMaximum(np.inf)
            maximumSpinbox.setMinimum(-np.inf)
            if param.value is not None and not math.isnan(param.value):
                useCheckbox.setChecked(self.paramUseSettings[name])
                valueSpinbox.setValue(param.value)
                minimumSpinbox.setValue(param.min)
                minimumSpinbox.setValue(param.max)
                expressionLineEdit.setText(param.expr)
                varyCheckbox.setChecked(param.vary)

            self._layout.addWidget(useCheckbox, n, 0)
            self._layout.addWidget(parameterNameLabel, n, 1)
            self._layout.addWidget(valueSpinbox, n, 2)
            self._layout.addWidget(minimumSpinbox, n, 3)
            self._layout.addWidget(maximumSpinbox, n, 4)
            self._layout.addWidget(expressionLineEdit, n, 5)
            self._layout.addWidget(varyCheckbox, n, 6)
            n += 1

        # space at the bottom of the list
        self._layout.setRowStretch(n, 1)

    def applyFitParameters(self):
        """ Updates the fit parameters with the new values from the widget.

            @return tuple(Parameters, dict): new lmfit Parameters and a dict indicating their use
        """
        for name, param in self.parameters.items():
            self.paramUseSettings[name] = self.widgets[name + '_use'].checkState()
            param.value = self.widgets[name + '_value'].value()
            param.min = self.widgets[name + '_min'].value()
            param.max = self.widgets[name + '_max'].value()
            param.expr = str(self.widgets[name + '_expr'].displayText())
            param.vary = self.widgets[name + '_vary'].checkState()
        return self.parameters, self.paramUseSettings

    def resetFitParameters(self):
        """ Resets the parameters in the widget to the stored values.

            @return tuple(Parameters, dict): old Parameters and dict indicating their use
        """
        for name, param in self.parameters.items():
            if param.value is not None and not math.isnan(param.value):
                self.widgets[name + '_use'].setChecked(self.paramUseSettings[name])
                self.widgets[name + '_value'].setValue(param.value)
                self.widgets[name + '_min'].setValue(param.min)
                self.widgets[name + '_max'].setValue(param.max)
                self.widgets[name + '_expr'].setText(param.expr)
                self.widgets[name + '_vary'].setChecked(param.vary)
        return self.parameters, self.paramUseSettings

    def updateFitParameters(self, parameters):
        """ Update all the parameter values.
            @param parameters Parameters: lmfit Parameters to update the widget with
        """
        for name, param in parameters.items():
            v = param.value
            if name in self.parameters and v is not None and not math.isnan(v):
                self.widgets[name + '_value'].setValue(v)
                self.widgets[name + '_min'].setValue(param.min)
                self.widgets[name + '_max'].setValue(param.max)
                self.widgets[name + '_expr'].setText(param.expr)
                self.widgets[name + '_vary'].setChecked(param.vary)
                self.parameters[name] = param
        return self.parameters, self.paramUseSettings

