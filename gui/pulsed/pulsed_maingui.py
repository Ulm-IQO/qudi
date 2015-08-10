# -*- coding: utf-8 -*-
"""
Created on Mon Jun 29 17:06:00 2015

@author: astark
"""

from PyQt4 import QtGui, QtCore, uic

import numpy as np
import os
from collections import OrderedDict

from gui.guibase import GUIBase
from core.util.mutex import Mutex

# Rather than import the ui*.py file here, the ui*.ui file itself is loaded by uic.loadUI in the QtGui classes below.

class ComboBoxDelegate(QtGui.QItemDelegate):

    def __init__(self, parent):
        QtGui.QItemDelegate.__init__(self, parent)
#		self.itemslist = itemslist

#    def paint(self, painter, option, index):
#		# Get Item Data
##		value = index.data(QtCore.Qt.DisplayRole).toInt()[0]
#		# fill style options with item data
#        style = QtGui.QApplication.style()
#        opt = QtGui.QStyleOptionComboBox()
###		opt.currentText = str(self.itemslist[value])
#        opt.rect = option.rect
##
##		# draw item data as ComboBox
#        style.drawComplexControl(QtGui.QStyle.CC_ComboBox, opt, painter)


    def createEditor(self, parent, option, index):
         # create the ProgressBar as our editor.
        editor = QtGui.QComboBox(parent)

        editor.addItems(['a','b','c'])
        editor.setCurrentIndex(0)
        editor.installEventFilter(self)
        return editor

#    def setEditorData(self, editor, index):
#        value = index.data(QtCore.Qt.DisplayRole)
#        num = self.items.index(value)
#        editor.setCurrentIndex(num)

    def setEditorData(self, editor, index):
        editor.blockSignals(True)
        editor.setCurrentIndex(editor.currentIndex())
        editor.blockSignals(False)

    def setModelData(self, editor, model, index):
        value = editor.currentIndex()
        model.setData(index, editor.itemText(value))
#        model.setData(index, QtCore.Qt.DisplayRole, QtCore.QVariant(value))

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)



class SpinBoxDelegate(QtGui.QItemDelegate):
    """
    qt help for spinboxes:
    http://doc.qt.io/qt-4.8/qt-itemviews-spinboxdelegate-example.html

    python help for spinboxes:
    http://stackoverflow.com/questions/28017395/how-to-use-delegate-to-control-qtableviews-rows-height
    """
    def __init__(self, parent):
        """
        Since the delegate is a subclass of QItemDelegate, the data it
        retrieves from the model is displayed in a default style, and we do not
        need to provide a custom paintEvent().
        """
        QtGui.QItemDelegate.__init__(self, parent)

    def createEditor(self, parent, option, index):
        """
        The createEditor() function returns an editor widget, in this case a
        spin box that restricts values from the model to integers from 0 to 100
        inclusive.
        """
        editor = QtGui.QSpinBox(parent)
        editor.setMinimum(0)
        editor.setMaximum(10000000)
        editor.installEventFilter(self)
        editor.setValue(100)
        # self.setModelData(editor, QtCore.QAbstractTableModel,QtCore.QModelIndex)
        # QtCore.QAbstractTableModel
        # QtCore.QModelIndex
        return editor

    def setEditorData(self, spinBox, index):
        """
        The setEditorData() function reads data from the model, converts it to
        an integer value, and writes it to the editor widget.
        """

        # value, ok = index.model().data(index, QtCore.Qt.EditRole)
        value = index.model().data(index)
        if value is not int:
            value = 0
        spinBox.setValue(value)


    def setModelData(self, spinBox, model, index):
        """
        The setModelData() function reads the contents of the spin box, and
        writes it to the model.
        """
        # spinBox = spinBox.currentIndex()
        spinBox.interpretText()
        value = spinBox.value()
        self.value = value

        model.setData(index, value, QtCore.Qt.EditRole)
#        model.setData(index, QtCore.QVariant(value))

    def updateEditorGeometry(self, editor, option, index):
        """
        The updateEditorGeometry() function updates the editor widget's
        geometry using the information supplied in the style option. This is
        the minimum that the delegate must do in this case.
        """
        editor.setGeometry(option.rect)

    def sizeHint(self, option, index):
        print('sizeHint', index.row(), index.column())
        return QtCore.QSize(64,64)

    def paint(self, painter, option, index):
        if (option.state & QtGui.QStyle.State_MouseOver):
            painter.fillRect(option.rect, QtCore.Qt.red);
        QtGui.QItemDelegate.paint(self, painter, option, index)



class ComboDelegate(QtGui.QItemDelegate):
    editorItems=['Combo_Zero', 'Combo_One','Combo_Two']
    height = 25
    width = 200
    def createEditor(self, parent, option, index):
        editor = QtGui.QListWidget(parent)
        # editor.addItems(self.editorItems)
        # editor.setEditable(True)
        editor.currentItemChanged.connect(self.currentItemChanged)
        return editor

    def setEditorData(self,editor,index):
        z = 0
        for item in self.editorItems:
            ai = QtGui.QListWidgetItem(item)
            editor.addItem(ai)
            if item == index.data():
                editor.setCurrentItem(editor.item(z))
            z += 1
        editor.setGeometry(0,index.row()*self.height,self.width,self.height*len(self.editorItems))

    def setModelData(self, editor, model, index):
        editorIndex=editor.currentIndex()
        text=editor.currentItem().text()
        model.setData(index, text)
        # print '\t\t\t ...setModelData() 1', text

    @QtCore.pyqtSlot()
    def currentItemChanged(self):
        self.commitData.emit(self.sender())

class CheckBoxDelegate(QtGui.QItemDelegate):
    """
    A delegate that places a fully functioning QCheckBox in every
    cell of the column to which it's applied
    """

    def __init__(self, parent):
        """
        Since the delegate is a subclass of QItemDelegate, the data it
        retrieves from the model is displayed in a default style, and we do not
        need to provide a custom paintEvent().
        """
        QtGui.QItemDelegate.__init__(self, parent)

    def createEditor(self, parent, option, index):
        """
        The createEditor() function returns an editor widget, in this case a
        spin box that restricts values from the model to integers from 0 to 100
        inclusive.
        """
        editor = QtGui.QCheckBox(parent)
        editor.setCheckState(QtCore.Qt.Unchecked)

        editor.installEventFilter(self)

        # self.setModelData(editor, QtCore.QAbstractTableModel,QtCore.QModelIndex)
        # QtCore.QAbstractTableModel
        # QtCore.QModelIndex
        return editor

    def setEditorData(self, editor, index):
        value = index.model().data(index, QtCore.Qt.CheckStateRole)
        if value == 0:
            checkState = QtCore.Qt.Unchecked
        else:
            checkState = QtCore.Qt.Checked
        editor.setCheckState(checkState)


    def setModelData(self, editor, model, index):
        """
        The setModelData() function reads the contents of the spin box, and
        writes it to the model.
        """
        # checkBox = checkBox.currentIndex()
        # checkBox.interpretText()
        # value = checkBox.isChecked()
        # self.value = value
        value = editor.checkState()
        model.setData(index, value, QtCore.Qt.CheckStateRole)
#        model.setData(index, QtCore.QVariant(value))

    def updateEditorGeometry(self, editor, option, index):
        """
        The updateEditorGeometry() function updates the editor widget's
        geometry using the information supplied in the style option. This is
        the minimum that the delegate must do in this case.
        """
        editor.setGeometry(option.rect)

    def sizeHint(self, option, index):
        print('sizeHint', index.row(), index.column())
        return QtCore.QSize(64,64)

    def paint(self, painter, option, index):
        if (option.state & QtGui.QStyle.State_MouseOver):
            painter.fillRect(option.rect, QtCore.Qt.red);
        QtGui.QItemDelegate.paint(self, painter, option, index)

class PulsedMeasurementMainWindow(QtGui.QMainWindow):
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_pulsed_maingui.ui')

        # Load it
        super(PulsedMeasurementMainWindow, self).__init__()
        uic.loadUi(ui_file, self)
        self.show()

class BlockSettingDialog(QtGui.QDialog):
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_pulsed_main_gui_settings_block_gen.ui')

        # Load it
        super(BlockSettingDialog, self).__init__()
        uic.loadUi(ui_file, self)

class PulsedMeasurementGui(GUIBase):
    """
    This is the GUI Class for pulsed measurements
    """
    _modclass = 'PulsedMeasurementGui'
    _modtype = 'gui'

    ## declare connectors
    _in = { 'pulseanalysislogic': 'PulseAnalysisLogic',
            'sequencegeneratorlogic': 'SequenceGeneratorLogic',
            'savelogic': 'SaveLogic'
            }

    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        c_dict = {'onactivate': self.activation, 'ondeactivate': self.deactivation}
        super().__init__(manager, name, config, c_dict)

        self.logMsg('The following configuration was found.',
                    msgType='status')

        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]),
                        msgType='status')

        #locking for thread safety
        self.threadlock = Mutex()

    def activation(self, e=None):
        """ Definition, configuration and initialisation of the pulsed measurement GUI.

          @param class e: event class from Fysom

        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules.
        """

        self._pulse_analysis_logic = self.connector['in']['pulseanalysislogic']['object']
        self._sequence_generator_logic = self.connector['in']['sequencegeneratorlogic']['object']
        self._save_logic = self.connector['in']['savelogic']['object']

        self._activted_main_ui(e)
        self._activated_block_settings_ui(e)

        self.count_analog_channels()
        self.count_digital_channels()

        # set up the types of the columns and create a pattern based on
        # the desired settings:

        #FIXME: Make the analog channel parameter chooseable in the settings.


        # the attributes are assigned to function an the desired argument one
        # wants to pass to these functions.
        self._param_a_ch = OrderedDict()
        self._param_a_ch['Function'] = [self._create_combobox, '()']
        self._param_a_ch['Freq (GHz)'] = [self._create_doublespinbox, '(min_val=0)']
        self._param_a_ch['Ampl. (V)'] = [self._create_doublespinbox, '(min_val=0,max_val=1.5)']
        self._param_a_ch['Phase(°)'] = [self._create_doublespinbox, '()']

        self._param_d_ch = OrderedDict()
        self._param_d_ch['CheckBox'] = [self._create_checkbox,'()']

        self._param_block = OrderedDict()
        self._param_block['Length (ns)'] = [self._create_doublespinbox, '(min_val=0)']
        self._param_block['Inc. (ns)'] = [self._create_doublespinbox,'(min_val=0)']
        self._param_block['Repeat?'] = [self._create_checkbox,'()']
        self._param_block['Use as tau?'] = [self._create_checkbox,'()']

        # This method should be executed when the tablewidget is subclassed in
        # an extra file:
#        model = QtGui.QStandardItemModel(4, 2)
#        self._mw.init_block_TableWidget.setModel(model)

        # emit a trigger event when for all mouse click and keyboard click events:
        # compare the C++ references:
        self._mw.init_block_TableWidget.setEditTriggers(QtGui.QAbstractItemView.AllEditTriggers)

        # replace also the combobox through a QListWidget have a look on:
        # http://stackoverflow.com/questions/28037126/how-to-use-qcombobox-as-delegate-with-qtableview


        # Modified by me
        self._mw.init_block_TableWidget.viewport().setAttribute(QtCore.Qt.WA_Hover);


        comboDelegate = ComboBoxDelegate(self._mw.init_block_TableWidget)
        self._mw.init_block_TableWidget.setItemDelegateForColumn(0, comboDelegate)

        spinDelegate = SpinBoxDelegate(self._mw.init_block_TableWidget)
        self._mw.init_block_TableWidget.setItemDelegateForColumn(1,spinDelegate)

        comboDelegate2= ComboDelegate(self._mw.init_block_TableWidget)
        self._mw.init_block_TableWidget.setItemDelegateForColumn(2,comboDelegate2)

        checkDelegate = CheckBoxDelegate(self._mw.init_block_TableWidget)
        self._mw.init_block_TableWidget.setItemDelegateForColumn(3,checkDelegate)

    def _create_doublespinbox(self, min_val=None, max_val=None, num_digits=None):
        dspinbox = QtGui.QDoubleSpinBox()
        dspinbox.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        dspinbox.setButtonSymbols(QtGui.QAbstractSpinBox.NoButtons)
        if min_val is None:
            min_val = -100000
        if max_val is None:
            max_val = 100000
        if num_digits is None:
            num_digits = 3
        dspinbox.setMinimum(min_val)
        dspinbox.setMaximum(max_val)
        dspinbox.setDecimals(num_digits)
        return dspinbox

    def _create_checkbox(self):
        #http://stackoverflow.com/questions/17748546/pyqt-column-of-checkboxes-in-a-qtableview
        checkbox = QtGui.QCheckBox()
        checkbox.setLayoutDirection(QtCore.Qt.RightToLeft)
        return checkbox

    def _create_combobox(self):
        combobox = QtGui.QComboBox()
        return combobox


    def deactivation(self, e):
        """ Undo the Definition, configuration and initialisation of the pulsed measurement GUI.

          @param class e: event class from Fysom

        This deactivation disconnects all the graphic modules, which were
        connected in the initUI method.
        """

        self._deactivat_main_ui(e)
        self._deactivate_block_ui(e)


    def _activted_main_ui(self, e):
        """ Initialize, connect and configure the main UI. """

        self._mw = PulsedMeasurementMainWindow()

        self._mw.add_init_row_selected_PushButton.clicked.connect(self.add_init_row_before_selected)
        self._mw.del_init_row_selected_PushButton.clicked.connect(self.del_init_row_selected)
        self._mw.add_init_row_last_PushButton.clicked.connect(self.add_init_row_after_last)
        self._mw.del_init_row_last_PushButton.clicked.connect(self.del_init_row_last)
        self._mw.clear_init_table_PushButton.clicked.connect(self.clear_init_table)


        self._mw.add_repeat_row_selected_PushButton.clicked.connect(self.add_repeat_row_before_selected)
        self._mw.del_repeat_row_selected_PushButton.clicked.connect(self.del_repeat_row_selected)
        self._mw.add_repeat_row_last_PushButton.clicked.connect(self.add_repeat_row_after_last)
        self._mw.del_repeat_row_last_PushButton.clicked.connect(self.del_repeat_row_last)
        self._mw.clear_repeat_table_PushButton.clicked.connect(self.clear_repeat_table)

        # connect the menue to the actions:
        self._mw.action_Settings_Block_Generation.triggered.connect(self.show_block_settings)
        self.show()


    def _deactivat_main_ui(self, e):
        """ Disconnects the main ui and deactivates the window. """

        self._mw.add_init_row_selected_PushButton.clicked.disconnect()
        self._mw.del_init_row_selected_PushButton.clicked.disconnect()
        self._mw.add_init_row_last_PushButton.clicked.disconnect()
        self._mw.del_init_row_last_PushButton.clicked.disconnect()
        self._mw.clear_init_table_PushButton.clicked.disconnect()

        self._mw.add_repeat_row_selected_PushButton.clicked.disconnect()
        self._mw.del_repeat_row_selected_PushButton.clicked.disconnect()
        self._mw.add_repeat_row_last_PushButton.clicked.disconnect()
        self._mw.del_repeat_row_last_PushButton.clicked.disconnect()
        self._mw.clear_repeat_table_PushButton.clicked.disconnect()

        self._mw.close()

    def _activated_block_settings_ui(self, e):
        """ Initialize, connect and configure the block settings UI. """

        self._bs = BlockSettingDialog() # initialize the block settings
        self._bs.accepted.connect(self.update_block_settings)
        self._bs.rejected.connect(self.keep_former_block_settings)
        self._bs.buttonBox.button(QtGui.QDialogButtonBox.Apply).clicked.connect(self.update_block_settings)

    def _deactivate_block_ui(self, e):
        """ Deactivate the Block settings """
        self._bs.accepted.disconnect()
        self._bs.rejected.disconnect()
        self._bs.buttonBox.button(QtGui.QDialogButtonBox.Apply).clicked.disconnect()

        self._bs.close()

    def show(self):
        """Make main window visible and put it above all other windows. """
        QtGui.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

    def show_block_settings(self):
        """ Opens the block settings menue. """
        self._bs.exec_()

    def update_block_settings(self):
        """ Write new block settings from the gui to the file. """

        self._use_digital_ch(self._bs.digital_channels_SpinBox.value())
        self._use_analog_channel(self._bs.analog_channels_SpinBox.value())

    def keep_former_block_settings(self):
        """ Keep the old block settings and restores them in the gui. """

        self._bs.digital_channels_SpinBox.setValue(self._num_d_ch)
        self._bs.analog_channels_SpinBox.setValue(self._num_a_ch)






    def add_init_row_before_selected(self):
        """
        """
        selected_row = self._mw.init_block_TableWidget.currentRow()

        self._mw.init_block_TableWidget.insertRow(selected_row)



    def add_n_rows(self, row_pos, ):
        pass



    def add_init_row_after_last(self):
        """

        """
        pass


    def del_init_row_selected(self):
        """
        """
        # get the row number of the selected item(s). That will return the
        # lowest selected row
        row_to_remove = self._mw.init_block_TableWidget.currentRow()
        self._mw.init_block_TableWidget.removeRow(row_to_remove)
        #self.update_sequence_parameters()
        pass

    def del_init_row_last(self):
        """
        """
        number_of_rows = self._mw.init_block_TableWidget.rowCount()
        # remember, the row index is started to count from 0 and not from 1,
        # therefore one has to reduce the value by 1:
        self._mw.init_block_TableWidget.removeRow(number_of_rows-1)
        #self.update_sequence_parameters()
        pass

    def clear_init_table(self):
        """
        """

        self._mw.init_block_TableWidget.setRowCount(1)
        self._mw.init_block_TableWidget.clearContents()



    def add_repeat_row_after_last(self):
        """
        """
        pass

    def add_repeat_row_before_selected(self):
        """
        """

        pass


    def del_repeat_row_selected(self):
        """
        """

        row_to_remove = self._mw.repeat_block_TableWidget.currentRow()
        self._mw.repeat_block_TableWidget.removeRow(row_to_remove)
        #self.update_sequence_parameters()
        pass

    def del_repeat_row_last(self):
        """
        """
        number_of_rows = self._mw.repeat_block_TableWidget.rowCount()
        # remember, the row index is started to count from 0 and not from 1,
        # therefore one has to reduce the value by 1:
        self._mw.repeat_block_TableWidget.removeRow(number_of_rows-1)
        #self.update_sequence_parameters()
        pass

    def clear_repeat_table(self):
        """
        """

        self._mw.repeat_block_TableWidget.setRowCount(1)
        self._mw.repeat_block_TableWidget.clearContents()

    def count_digital_channels(self):
        """ Get the number of currently displayed digital channels.

        @return int: number of digital channels

        The number of digital channal are counted and return and additionally
        the internal counter variable _num_d_ch is updated. The counting
        procedure is based on the init_block_TableWidget since it is assumed
        that all operation on the init_block_TableWidget is also applied on
        repeat_block_TableWidget.
        """
        count_dch = 0
        for column in range(self._mw.init_block_TableWidget.columnCount()):
            if 'DCh' in self._mw.init_block_TableWidget.horizontalHeaderItem(column).text():
                count_dch = count_dch + 1

        self._num_d_ch = count_dch
        return count_dch

    def _use_digital_ch(self, num_d_ch):
        """

        @param int num_d_ch:

        This method is based on the idea that digital channels are added or
        removed subsequently and not at once, therefore you have to ensure that
        this function is called by changing num_digital_channels
        subsequentially. It should also be ensured that the number of channels
        are not falling below 2 (that number is more or less arbitrary).
        """


        if (self._num_a_ch == 1) and (num_d_ch != 2):
            self.logMsg('For one analog channel the number of digital '
                        'channels must be set to 2!\nTherefore the number of '
                        'digital channels is set to 2 in the following.',
                        msgType='warning')
            num_d_ch = 2

        if (self._num_a_ch == 2) and (num_d_ch != 4):
            self.logMsg('For two analog channels the number of digital '
                        'channels must be set to 4!\nTherefore the number of '
                        'digital channels is set to 4 in the following.',
                        msgType='warning')
            num_d_ch = 4

        # if more digital channels are needed then are currently used, create
        # as much as digital channels are desired.
        if self._num_d_ch < num_d_ch:
            position_list = []  # use a position list, which is essentially
                                # needed not to be confused with the analog
                                # channels. In this it is specified on which
                                # positions the channels are created.

            if self._num_a_ch == 0:
                for channel in range(self._num_d_ch, num_d_ch):
                    position_list.append(channel)

            if self._num_a_ch == 1:
                for channel in range(self._num_d_ch, num_d_ch):
                    position_list.append(channel+len(self._param_a_ch))

            if self._num_a_ch == 2:
                for channel in range(self._num_d_ch, num_d_ch):
                    if channel < 2:
                        position_list.append(len(self._param_a_ch) + channel)
                    else:
                        position_list.append(len(self._param_a_ch)*2 + channel)

            for appended_channel, channel_pos in enumerate(position_list):

                # create the channels for the initial block
                self._mw.init_block_TableWidget.insertColumn(channel_pos)
                self._mw.init_block_TableWidget.setHorizontalHeaderItem(channel_pos, QtGui.QTableWidgetItem())
                self._mw.init_block_TableWidget.horizontalHeaderItem(channel_pos).setText('DCh{0}'.format(self._num_d_ch+appended_channel) )
                self._mw.init_block_TableWidget.setColumnWidth(channel_pos, 40)

                # add the new properties to the whole column
                for row_num in range(self._mw.init_block_TableWidget.rowCount()):
                    cellobject = eval('self.'+self._param_d_ch['CheckBox'][0].__name__ + self._param_d_ch['CheckBox'][1] )
                    self._mw.init_block_TableWidget.setCellWidget(row_num, channel_pos, cellobject)

                # create the channels for the repeated block
                self._mw.repeat_block_TableWidget.insertColumn(channel_pos)
                self._mw.repeat_block_TableWidget.setHorizontalHeaderItem(channel_pos, QtGui.QTableWidgetItem())
                self._mw.repeat_block_TableWidget.horizontalHeaderItem(channel_pos).setText('DCh{0}'.format(self._num_d_ch+appended_channel) )
                self._mw.repeat_block_TableWidget.setColumnWidth(channel_pos, 40)

                # add the new properties to the whole column
                for row_num in range(self._mw.repeat_block_TableWidget.rowCount()):
                    cellobject = eval('self.'+self._param_d_ch['CheckBox'][0].__name__ + self._param_d_ch['CheckBox'][1] )
                    self._mw.repeat_block_TableWidget.setCellWidget(row_num, channel_pos, cellobject)

            self._num_d_ch = self._num_d_ch + len(position_list)

        # if less digital channels are needed then are currently displayed,
        # then remove the unneeded ones.
        elif self._num_d_ch > num_d_ch:
            position_list = []
            #if self._num_a_ch == 0:

            for column in range(self._num_d_ch, num_d_ch-1, -1):
                position_list.append(column)


            for channel_pos in position_list:
                aimed_ch = 'DCh{0}'.format(channel_pos)

                for column in range(self._mw.init_block_TableWidget.columnCount()-1, -1, -1):
                    if aimed_ch in self._mw.init_block_TableWidget.horizontalHeaderItem(column).text():
                        self._mw.init_block_TableWidget.removeColumn(column)
                        break

                for column in range(self._mw.repeat_block_TableWidget.columnCount()-1, -1, -1):
                    if aimed_ch in self._mw.repeat_block_TableWidget.horizontalHeaderItem(column).text():
                        self._mw.repeat_block_TableWidget.removeColumn(column)
                        break

            self._num_d_ch = num_d_ch

    def count_analog_channels(self):
        """ Get the number of currently displayed analog channels.

        @return int: number of analog channels

        The number of analog channal are counted and return and additionally
        the internal counter variable _num_a_ch is updated. The counting
        procedure is based on the init_block_TableWidget since it is assumed
        that all operation on the init_block_TableWidget is also applied on
        repeat_block_TableWidget.
        """
        ana1 = 0
        ana2 = 0
        for column in range(self._mw.init_block_TableWidget.columnCount()):
            if 'ACh0' in self._mw.init_block_TableWidget.horizontalHeaderItem(column).text():
                ana1 = 1
            if 'ACh1' in self._mw.init_block_TableWidget.horizontalHeaderItem(column).text():
                ana2 = 1

        self._num_a_ch = ana1 + ana2     # count the found channels together
        return self._num_a_ch

    def _use_analog_channel(self, num_a_ch):
        """

        @param int num_a_ch: number of analog channels. Possible values are
                             0, 1 and 2, where 0 specifies no channels.
        """


        if not ((type(num_a_ch) is int) and (0 <= num_a_ch) and (num_a_ch <= 2)):
            self.logMsg('The number for the analog channels was expected to '
                        'be either 0, 1 or 2, but a number of {0} was '
                        'passed.'.format(num_a_ch), msgType='warning')

        # If no analog channels are needed, remove all if they are available:
        if num_a_ch == 0:
            # count backwards and remove from the back the analog parameters:
            # go through the initial block of the table widget first:
            for column in range(self._mw.init_block_TableWidget.columnCount()-1, -1, -1):
                if 'ACh0' in self._mw.init_block_TableWidget.horizontalHeaderItem(column).text():
                   self._mw.init_block_TableWidget.removeColumn(column)
                if 'ACh1' in self._mw.init_block_TableWidget.horizontalHeaderItem(column).text():
                   self._mw.init_block_TableWidget.removeColumn(column)

            # apply now the same for the repeated block:
            for column in range(self._mw.repeat_block_TableWidget.columnCount()-1, -1, -1):
                if 'ACh0' in self._mw.repeat_block_TableWidget.horizontalHeaderItem(column).text():
                   self._mw.repeat_block_TableWidget.removeColumn(column)
                if 'ACh1' in self._mw.repeat_block_TableWidget.horizontalHeaderItem(column).text():
                   self._mw.repeat_block_TableWidget.removeColumn(column)

            self._num_a_ch = 0

        # if two analog channels are already created and one is desired, then
        # remove the second one.
        elif (num_a_ch == 1) and (self._num_a_ch == 2):

            for column in range(self._mw.init_block_TableWidget.columnCount()-1, -1, -1):
                if 'ACh1' in self._mw.init_block_TableWidget.horizontalHeaderItem(column).text():
                   self._mw.init_block_TableWidget.removeColumn(column)

            for column in range(self._mw.repeat_block_TableWidget.columnCount()-1, -1, -1):
                if 'ACh1' in self._mw.repeat_block_TableWidget.horizontalHeaderItem(column).text():
                   self._mw.repeat_block_TableWidget.removeColumn(column)

            self._num_a_ch = 1
            self._use_digital_ch(2)

        # if less then 2 analog channels are visible but one or two analog
        # channels are desired, then insert them in the table:
        elif (num_a_ch > 0) and (self._num_a_ch < 2):
            # repeat the channel creating for the number of channels:
            column_pos = 0

            for channel in range(self._num_a_ch, num_a_ch):

                column_pos = (len(self._param_a_ch) + 2)*channel # for two digital marker channels of the AWG
                # append each parameter like specified in the _param_a_ch list:
                for column, parameter in enumerate(self._param_a_ch):
                    self._mw.init_block_TableWidget.insertColumn(column_pos+column)
                    self._mw.init_block_TableWidget.setHorizontalHeaderItem(column_pos+column, QtGui.QTableWidgetItem())
                    self._mw.init_block_TableWidget.horizontalHeaderItem(column_pos+column).setText('ACh{0}\n'.format(channel) + parameter)
                    self._mw.init_block_TableWidget.setColumnWidth(column_pos+column, 70)

                    # add the new properties to the whole column
                    for row_num in range(self._mw.init_block_TableWidget.rowCount()):
                        cellobject = eval('self.'+self._param_a_ch[parameter][0].__name__ + self._param_a_ch[parameter][1] )
                        self._mw.init_block_TableWidget.setCellWidget(row_num, column_pos+column, cellobject)

                    self._mw.repeat_block_TableWidget.insertColumn(column_pos+column)
                    self._mw.repeat_block_TableWidget.setHorizontalHeaderItem(column_pos+column, QtGui.QTableWidgetItem())
                    self._mw.repeat_block_TableWidget.horizontalHeaderItem(column_pos+column).setText('ACh{0}\n'.format(channel) + parameter)
                    self._mw.repeat_block_TableWidget.setColumnWidth(column_pos+column, 70)

                    # add the new properties to the whole column
                    for row_num in range(self._mw.repeat_block_TableWidget.rowCount()):
                        cellobject = eval('self.'+self._param_a_ch[parameter][0].__name__ + self._param_a_ch[parameter][1] )
                        self._mw.repeat_block_TableWidget.setCellWidget(row_num, column_pos+column, cellobject)

                self._num_a_ch = channel+1 # tell how many analog channel has been created
                self._use_digital_ch(2)



    def idle_clicked(self):
        """ Stopp the scan if the state has switched to idle. """
        self._pulse_analysis_logic.stop_pulsed_measurement()


    def run_clicked(self, enabled):
        """ Manages what happens if odmr scan is started.

        @param bool enabled: start scan if that is possible
        """

        #Firstly stop any scan that might be in progress
        self._pulse_analysis_logic.stop_pulsed_measurement()
        #Then if enabled. start a new odmr scan.
        if enabled:
            self._pulse_analysis_logic.start_pulsed_measurement()





    def refresh_lasertrace_plot(self):
        ''' This method refreshes the xy-plot image
        '''
        self.lasertrace_image.setData(self._pulse_analysis_logic.laser_plot_x, self._pulse_analysis_logic.laser_plot_y)

    def refresh_signal_plot(self):
        ''' This method refreshes the xy-matrix image
        '''
        self.signal_image.setData(self._pulse_analysis_logic.signal_plot_x, self._pulse_analysis_logic.signal_plot_y)


    def create_row(self):
        ''' This method creates a new row in the TableWidget at the current cursor position.
        '''
        # block all signals from the TableWidget
        self._mw.sequence_tableWidget.blockSignals(True)
        # insert empty row after current cursor position
        current_row = self._mw.sequence_tableWidget.currentRow()+1
        if current_row == 0:
            current_row = self._mw.sequence_tableWidget.rowCount()

        self._mw.sequence_tableWidget.insertRow(current_row)

        # create the checkbox item to fill the channel rows and the "use as tau" row with
        chkBoxItem  = QtGui.QTableWidgetItem()
        chkBoxItem.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
        chkBoxItem.setCheckState(QtCore.Qt.Unchecked)

        # fill channel rows with the checkbox item
        for i in range(8):
            self._mw.sequence_tableWidget.setItem(current_row, i, chkBoxItem.clone())

        # create text field item and put it in the "length" and "increment" column
        textItem = QtGui.QTableWidgetItem('0')
        textItem.setFlags(QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled)
        self._mw.sequence_tableWidget.setItem(current_row, 8, textItem)
        self._mw.sequence_tableWidget.setItem(current_row, 9, textItem.clone())

        # put checkbox items into "repeat?" and "use as tau?" column
        self._mw.sequence_tableWidget.setItem(current_row, 10, chkBoxItem.clone())
        self._mw.sequence_tableWidget.setItem(current_row, 11, chkBoxItem.clone())

        # increment current row
        self._mw.sequence_tableWidget.setCurrentCell(current_row, 0)
        # unblock all signals from the TableWidget
        self._mw.sequence_tableWidget.blockSignals(False)
        return


    def delete_row(self):
        ''' This method deletes a row in the TableWidget at the current cursor position.
        '''
        # block all signals from the TableWidget
        self._mw.sequence_tableWidget.blockSignals(True)

        # check if a current row is selected. Select last row if not.
        current_row = self._mw.sequence_tableWidget.currentRow()
        if current_row == -1:
            current_row = self._mw.sequence_tableWidget.rowCount()

        # delete current row and all its items
        self._mw.sequence_tableWidget.removeRow(current_row)

        # decrement current row
        self._mw.sequence_tableWidget.setCurrentCell(current_row-1, 8)

        # unblock all signals from the TableWidget
        self._mw.sequence_tableWidget.blockSignals(False)
        return


    def clear_list(self):
        ''' This method deletes all rows in the TableWidget.
        '''
        # block all signals from the TableWidget
        self._mw.sequence_tableWidget.blockSignals(True)

        # clear the TableWidget
        number_of_rows = self._mw.sequence_tableWidget.rowCount()

        while number_of_rows >= 0:
            self._mw.sequence_tableWidget.removeRow(number_of_rows)
            number_of_rows -= 1

        # unblock all signals from the TableWidget
        self._mw.sequence_tableWidget.blockSignals(False)
        return


    def sequence_parameters_changed(self, item):
        ''' This method calculates and updates all parameters (size, length etc.) upon a change of a sequence entry.

        @param QTableWidgetItem item: Table item that has been changed
        '''
        # Check if the changed item is of importance for the parameters
        if (item.column() in [0,8,9,10]):
            # calculate the current sequence parameters
            self.update_sequence_parameters()
        return


    def update_sequence_parameters(self):
        """ Initialize the matrix creation and update the logic. """
        # calculate the current sequence parameters
        repetitions = int(self._mw.repetitions_lineEdit.text())
        matrix = self.get_matrix()
        self._sequence_generator_logic.update_sequence_parameters(matrix, repetitions)

        # get updated values from SequenceGeneratorLogic
        length_bins = self._sequence_generator_logic._current_sequence_parameters['length_bins']
        length_ms = self._sequence_generator_logic._current_sequence_parameters['length_ms']
        number_of_lasers = self._sequence_generator_logic._current_sequence_parameters['number_of_lasers']

        # update the DisplayWidgets
        self._mw.length_bins_lcdNumber.display(length_bins)
        self._mw.length_s_lcdNumber.display(length_ms)
        self._mw.laser_number_lcdNumber.display(number_of_lasers)
        return


#    def reset_parameters(self):
#        ''' This method resets all GUI parameters to the default state.
#        '''
#        # update the DisplayWidgets
#        self._mw.length_bins_lcdNumber.display(0)
#        self._mw.length_s_lcdNumber.display(0)
#        self._mw.laser_number_lcdNumber.display(0)


    def save_sequence(self):
        ''' This method encodes the currently edited sequence into a matrix for passing it to the logic module.
            There the sequence will be created and saved.
        '''
        # Create matrix to pass the data to the logic module where it will be saved
        name = str(self._mw.sequence_name_lineEdit.text())
        # update current sequence parameters in the logic
        self.update_sequence_parameters()
        # save current sequence under name "name"
        self._sequence_generator_logic.save_sequence(name)
        # update sequence combo boxes
        self.sequence_list_changed()
        return


    def get_matrix(self):
        """ Create a Matrix from the GUI's TableWidget.

        This method creates a matrix out of the current TableWidget to be
        further processed by the logic module.
        """
        # get the number of rows and columns
        num_of_rows = self._mw.sequence_tableWidget.rowCount()
        num_of_columns = self._mw.sequence_tableWidget.columnCount()

        #FIXME: the matrix should not be in the future not an integer type
        #       since the length of a pulse can and have sometimes to be an
        #       float value.

        # Initialize a matrix of proper size and integer data type
        matrix = np.empty([num_of_rows, num_of_columns], dtype=int)
        # Loop through all matrix entries and fill them with the data of the TableWidgetItems
        for row in range(num_of_rows):
            for column in range(num_of_columns):
                # Get the item of the current row and column
                item = self._mw.sequence_tableWidget.item(row, column)
                # check if the current column is a checkbox or a textfield
                if (int(item.flags()) & 16):
                    matrix[row, column] = int(bool(item.checkState()))
                else:
                    matrix[row, column] = int(item.data(0))
        return matrix


    def create_table(self):
        ''' This method creates a TableWidget out of the current matrix passed from the logic module.
        '''
        # get matrix from the sequence generator logic
        matrix = self._sequence_generator_logic._current_matrix
        # clear current table widget
        self.clear_list()
        # create as many rows in the table widget as the matrix has and fill them with entries
        for row_number, row in enumerate(matrix):
            # create the row
            self.create_row()
            # block all signals from the TableWidget
            self._mw.sequence_tableWidget.blockSignals(True)
            # edit all items in the row
            for column_number in range(matrix.shape[1]):
                item = self._mw.sequence_tableWidget.item(row_number, column_number)
                # is the current item a checkbox or a number?
                if (int(item.flags()) & 16):
                    # check ckeckbox if the corresponding matrix entry is "1"
                    if matrix[row_number, column_number] == 1:
                        item.setCheckState(QtCore.Qt.Checked)
                else:
                    item.setText(str(matrix[row_number, column_number]))
        # unblock all signals from the TableWidget
        self._mw.sequence_tableWidget.blockSignals(False)
        return


    def delete_sequence(self):
        ''' This method completely removes the currently selected sequence.
        '''
        # call the delete method in the sequence generator logic
        name = self._mw.sequence_list_comboBox.currentText()
        self._sequence_generator_logic.delete_sequence(name)
        # update the combo boxes
        self.sequence_list_changed()
        self.clear_list()
        return


    def sequence_list_changed(self):
        ''' This method updates the Seqeuence combo boxes upon the adding or removal of a sequence
        '''
        # get the names of all saved sequences from the sequence generator logic
        names = self._sequence_generator_logic.get_sequence_names()
        # clear combo boxes
        self._mw.sequence_name_comboBox.clear()
        self._mw.sequence_list_comboBox.clear()
        # fill combo boxes with current names
        self._mw.sequence_name_comboBox.addItems(names)
        self._mw.sequence_list_comboBox.addItems(names)
        return


    def current_sequence_changed(self):
        ''' This method updates the current sequence variables in the sequence generator logic.
        '''
        name = self._mw.sequence_list_comboBox.currentText()
        self._sequence_generator_logic.set_current_sequence(name)
        self.create_table()
        repetitions = self._sequence_generator_logic._current_sequence_parameters['repetitions']
        self._mw.repetitions_lineEdit.setText(str(repetitions))
        return


    def sequence_to_run_changed(self):
        ''' This method updates the parameter set of the sequence to run in the PulseAnalysisLogic.
        '''
        name = self._mw.sequence_name_comboBox.currentText()
        self._pulse_analysis_logic.update_sequence_parameters(name)
        return


    def clear_list_clicked(self):
        ''' This method clears the current tableWidget, inserts a single empty row and updates the sequence parameters in the GUI and SequenceGeneratorLogic
        '''
        self.clear_list()
        self.create_row()
        self.update_sequence_parameters()
        return





    def test(self):
        print('called test function!')
        print(str(self._mw.sequence_list_comboBox.currentText()))
        return
#
#
#
#    ###########################################################################
#    ##                         Change Methods                                ##
#    ###########################################################################
#
#    def change_frequency(self):
#        self._pulse_analysis_logic.MW_frequency = float(self._mw.frequency_InputWidget.text())
#
#    def change_power(self):
#        self._pulse_analysis_logic.MW_power = float(self._mw.power_InputWidget.text())
#
#    def change_pg_frequency(self):
#        self._pulse_analysis_logic.pulse_generator_frequency = float(self._mw.pg_frequency_lineEdit.text())
#
#    def change_runtime(self):
#        pass
