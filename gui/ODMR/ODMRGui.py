# -*- coding: utf-8 -*-
"""
This file contains the QuDi GUI module base class.

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

Copyright (C) 2015 Florian S. Frank florian.frank@uni-ulm.de
"""

#from PyQt4 import QtCore, QtGui
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph as pg
import numpy as np

from collections import OrderedDict
from gui.GUIBase import GUIBase
from gui.ODMR.ODMRGuiUI import Ui_MainWindow
from gui.ODMR.ODMRSettingsUI import Ui_SettingsDialog

# To convert the *.ui file to a raw ODMRGuiUI.py file use the python script
# in the Anaconda directory, which you can find in:
#
# "<Installation-dir of Anacona>\Anaconda3\Lib\site-packages\PyQt4\uic\pyuic.py".
#
# Then use that script like
#
# "<Installation-dir of Anacona>\Anaconda3\Lib\site-packages\PyQt4\uic\pyuic.py"ODMRGuiUI.ui > ODMRGuiUI.py


class ODMRMainWindow(QtGui.QMainWindow,Ui_MainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.setupUi(self)
        
class ODMRSettingDialog(QtGui.QDialog,Ui_SettingsDialog):
    def __init__(self):
        QtGui.QDialog.__init__(self)
        self.setupUi(self)

            
class ODMRGui(GUIBase):
    """
    This is the GUI Class for ODMR
    """
    _modclass = 'ODMRGui'
    _modtype = 'gui'

    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        c_dict = {'onactivate': self.initUI}
        super().__init__(
                    manager,
                    name,
                    config,
                    c_dict)
        
        ## declare connectors
        self.connector['in']['odmrlogic1'] = OrderedDict()
        self.connector['in']['odmrlogic1']['class'] = 'ODMRLogic'
        self.connector['in']['odmrlogic1']['object'] = None
        self.connector['in']['savelogic'] = OrderedDict()
        self.connector['in']['savelogic']['class'] = 'SaveLogic'
        self.connector['in']['savelogic']['object'] = None

        self.logMsg('The following configuration was found.', 
                    msgType='status')
                            
        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]), 
                        msgType='status')  
                        
    def initUI(self, e=None):
        """ Definition, configuration and initialisation of the ODMR GUI.
          
          @param class e: event class from Fysom


        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules.
        
        """
        
        self._odmr_logic = self.connector['in']['odmrlogic1']['object']
        print("ODMR logic is", self._odmr_logic)
        
        self._save_logic = self.connector['in']['savelogic']['object']
        print("Save logic is", self._save_logic)  
        
        # Use the inherited class 'Ui_ODMRGuiUI' to create now the 
        # GUI element:
        self._mw = ODMRMainWindow()
        self._sd = ODMRSettingDialog()
        
        
        # Get the image from the logic
        self.odmr_matrix_image = pg.ImageItem(self._odmr_logic.ODMR_plot_xy.transpose())
        self.odmr_matrix_image.setRect(QtCore.QRectF(self._odmr_logic.MW_start,0,self._odmr_logic.MW_stop-self._odmr_logic.MW_start,self._odmr_logic.NumberofLines))
        self.odmr_image = pg.PlotDataItem(self._odmr_logic.ODMR_plot_x,self._odmr_logic.ODMR_plot_y)
        self.odmr_fit_image = pg.PlotDataItem(self._odmr_logic.ODMR_fit_x,self._odmr_logic.ODMR_fit_y,
                                                    pen=QtGui.QPen(QtGui.QColor(255,0,255,255)))
        
        
        # Add the display item to the xy and xz VieWidget, which was defined in
        # the UI file.
        self._mw.odmr_ViewWidget.addItem(self.odmr_image)
        self._mw.odmr_ViewWidget.addItem(self.odmr_fit_image)
        self._mw.odmr_matrix_ViewWidget.addItem(self.odmr_matrix_image)
        self._mw.odmr_ViewWidget.showGrid(x=True, y=True, alpha=0.8)
        
        
        # create a color map that goes from dark red to dark blue:

        # Absolute scale relative to the expected data not important. This 
        # should have the same amount of entries (num parameter) as the number
        # of values given in color. 
        pos = np.linspace(0.0, 1.0, num=10)
        color = np.array([[127,  0,  0,255], [255, 26,  0,255], [255,129,  0,255],
                          [254,237,  0,255], [160,255, 86,255], [ 66,255,149,255],
                          [  0,204,255,255], [  0, 88,255,255], [  0,  0,241,255],
                          [  0,  0,132,255]], dtype=np.ubyte)
                          
        color_inv = np.array([ [  0,  0,132,255], [  0,  0,241,255], [  0, 88,255,255],
                               [  0,204,255,255], [ 66,255,149,255], [160,255, 86,255],
                               [254,237,  0,255], [255,129,  0,255], [255, 26,  0,255],
                               [127,  0,  0,255] ], dtype=np.ubyte)
                          
        colmap = pg.ColorMap(pos, color_inv)        
        self.colmap_norm = pg.ColorMap(pos, color/255)
        
        # get the LookUpTable (LUT), first two params should match the position
        # scale extremes passed to ColorMap(). 
        # I believe last one just has to be >= the difference between the min and max level set later
        lut = colmap.getLookupTable(0, 1, 2000)
            
        self.odmr_matrix_image.setLookupTable(lut)
        
        # Set the state button as ready button as default setting.
        self._mw.idle_StateWidget.click()
        
        # Configuration of the comboWidget
        self._mw.mode_ComboWidget.addItem('Off')
        self._mw.mode_ComboWidget.addItem('CW')
        
        #######################################################################
        ##                Configuration of the InputWidgets                  ##
        #######################################################################
        
        # Add Validators to InputWidgets 
        validator = QtGui.QDoubleValidator()
        validator2 = QtGui.QIntValidator()
        
        self._mw.frequency_InputWidget.setValidator(validator)
        self._mw.start_freq_InputWidget.setValidator(validator)
        self._mw.step_freq_InputWidget.setValidator(validator)
        self._mw.stop_freq_InputWidget.setValidator(validator)
        self._mw.power_InputWidget.setValidator(validator)
        self._mw.runtime_InputWidget.setValidator(validator2)
        self._sd.matrix_lines_InputWidget.setValidator(validator)
        self._sd.clock_frequency_InputWidget.setValidator(validator2)
        
        # Take the default values from logic:
        self._mw.frequency_InputWidget.setText(str(self._odmr_logic.MW_frequency))     
        self._mw.start_freq_InputWidget.setText(str(self._odmr_logic.MW_start))
        self._mw.step_freq_InputWidget.setText(str(self._odmr_logic.MW_step))
        self._mw.stop_freq_InputWidget.setText(str(self._odmr_logic.MW_stop))
        self._mw.power_InputWidget.setText(str(self._odmr_logic.MW_power))
        self._mw.runtime_InputWidget.setText(str(self._odmr_logic.RunTime))
        self._mw.elapsed_time_DisplayWidget.display(int(self._odmr_logic.ElapsedTime))      
        self._sd.matrix_lines_InputWidget.setText(str(self._odmr_logic.NumberofLines))
        self._sd.clock_frequency_InputWidget.setText(str(self._odmr_logic._clock_frequency))
        
        # Update the inputed/displayed numbers if return key is hit:

        self._mw.frequency_InputWidget.returnPressed.connect(self.change_frequency)
        self._mw.start_freq_InputWidget.returnPressed.connect(self.change_start_freq)
        self._mw.step_freq_InputWidget.returnPressed.connect(self.change_step_freq)
        self._mw.stop_freq_InputWidget.returnPressed.connect(self.change_stop_freq)
        self._mw.power_InputWidget.returnPressed.connect(self.change_power)
        self._mw.runtime_InputWidget.returnPressed.connect(self.change_runtime)
        
        # Update the inputed/displayed numbers if the cursor has left the field:

        self._mw.frequency_InputWidget.editingFinished.connect(self.change_frequency)
        self._mw.start_freq_InputWidget.editingFinished.connect(self.change_start_freq)
        self._mw.step_freq_InputWidget.editingFinished.connect(self.change_step_freq)
        self._mw.stop_freq_InputWidget.editingFinished.connect(self.change_stop_freq)
        self._mw.power_InputWidget.editingFinished.connect(self.change_power)
        self._mw.runtime_InputWidget.editingFinished.connect(self.change_runtime)
        
        #######################################################################
        ##                      Connect signals                              ##
        #######################################################################
       
        # Connect the RadioButtons and connect to the events if they are clicked:
        self._mw.idle_StateWidget.toggled.connect(self.idle_clicked)
        self._mw.run_StateWidget.toggled.connect(self.run_clicked)
                
        self._odmr_logic.signal_ODMR_plot_updated.connect(self.refresh_plot)
        self._odmr_logic.signal_ODMR_matrix_updated.connect(self.refresh_matrix)
        self._odmr_logic.signal_ODMR_elapsedtime_changed.connect(self.refresh_elapsedtime)
        # connect settings signals
        self._mw.action_Settings.triggered.connect(self.menue_settings)
        self._sd.accepted.connect(self.update_settings)
        self._sd.rejected.connect(self.reject_settings)
        self._sd.buttonBox.button(QtGui.QDialogButtonBox.Apply).clicked.connect(self.update_settings)        
        # Connect stop odmr
        self._odmr_logic.signal_ODMR_finished.connect(self._mw.idle_StateWidget.click)
        # Combo Widget
        self._mw.mode_ComboWidget.activated[str].connect(self.mw_stop)
        
         # Show the Main ODMR GUI:
        self._mw.show()

    def show(self):
        """Make window visible and put it above all other windows.
        """
        QtGui.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

    def idle_clicked(self):
        """ Stopp the scan if the state has switched to idle. """
        self._odmr_logic.stop_ODMR_scan()
#        self._odmr_logic.kill_ODMR()


    def run_clicked(self, enabled):
        """ Manages what happens if odmr scan is started.
        
        @param bool enabled: start scan if that is possible
        """
        
        #Firstly stop any scan that might be in progress
        self._odmr_logic.stop_ODMR_scan()
#        self._odmr_logic.kill_ODMR()
        #Then if enabled. start a new odmr scan.
        if enabled:
            self._odmr_logic.start_ODMR_scan()
            
    def menue_settings(self):
        ''' This method opens the settings menue
        '''
        self._sd.exec_()

    def refresh_plot(self):
        ''' This method refreshes the xy-plot image
        '''
        self.odmr_image.setData(self._odmr_logic.ODMR_plot_x,self._odmr_logic.ODMR_plot_y)
        self.odmr_fit_image.setData(self._odmr_logic.ODMR_fit_x,self._odmr_logic.ODMR_fit_y)
        
    def refresh_matrix(self):
        ''' This method refreshes the xy-matrix image
        '''       
        self.odmr_matrix_image.setImage(self._odmr_logic.ODMR_plot_xy.transpose())
        self.odmr_matrix_image.setRect(QtCore.QRectF(self._odmr_logic.MW_start,0,self._odmr_logic.MW_stop-self._odmr_logic.MW_start,self._odmr_logic.NumberofLines))
     
    def refresh_elapsedtime(self):
        self._mw.elapsed_time_DisplayWidget.display(int(self._odmr_logic.ElapsedTime))
     
    def update_settings(self):
        ''' This method writes the new settings from the gui to the file
        '''
        self._odmr_logic.NumberofLines = int(self._sd.matrix_lines_InputWidget.text())
        self._odmr_logic.set_clock_frequency(int(self._sd.clock_frequency_InputWidget.text()))

                
    def reject_settings(self):
        ''' This method keeps the old settings and restores the old settings in the gui
        '''
        self._sd.matrix_lines_InputWidget.setText(str(self._odmr_logic.NumberofLines))
        
    def mw_stop(self, txt):
        if txt == 'Off':
            self._odmr_logic.MW_off()
        if txt == 'CW':
            self._odmr_logic.MW_on()
            

        
    ###########################################################################
    ##                         Change Methods                                ##
    ###########################################################################
    
    def change_frequency(self):
        self._odmr_logic.set_frequency(frequency = float(self._mw.frequency_InputWidget.text()))
        
    def change_start_freq(self):
        self._odmr_logic.MW_start = float(self._mw.start_freq_InputWidget.text())
        
    def change_step_freq(self):
        self._odmr_logic.MW_step = float(self._mw.step_freq_InputWidget.text())
        
    def change_stop_freq(self):
        self._odmr_logic.MW_stop = float(self._mw.stop_freq_InputWidget.text())
        
    def change_power(self):
        self._odmr_logic.MW_power = float(self._mw.power_InputWidget.text())
        self._odmr_logic.set_power(power = self._odmr_logic.MW_power)
        
    def change_runtime(self):
        self._odmr_logic.RunTime = float(self._mw.runtime_InputWidget.text())

        
        

