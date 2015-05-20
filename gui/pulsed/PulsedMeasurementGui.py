#from PyQt4 import QtCore, QtGui
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph as pg
import numpy as np

from collections import OrderedDict
from core.Base import Base
from gui.pulsed.PulsedMeasurementGuiUI import Ui_MainWindow

# To convert the *.ui file to a raw ODMRGuiUI.py file use the python script
# in the Anaconda directory, which you can find in:
#
# "<Installation-dir of Anacona>\Anaconda3\Lib\site-packages\PyQt4\uic\pyuic.py".
#
# Then use that script like
#
# "<Installation-dir of Anacona>\Anaconda3\Lib\site-packages\PyQt4\uic\pyuic.py"ODMRGuiUI.ui > ODMRGuiUI.py


# set manually the background color in hex code according to our color scheme: 
pg.setConfigOption('background', QtGui.QColor('#222'))


class PulsedMeasurementMainWindow(QtGui.QMainWindow,Ui_MainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.setupUi(self)

            
               
            
class PulsedMeasurementGui(Base,QtGui.QMainWindow,Ui_MainWindow):
    """
    This is the GUI Class for pulsed measurements
    """
    
    

    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        c_dict = {'onactivate': self.initUI}
        Base.__init__(self,
                    manager,
                    name,
                    config,
                    c_dict)
        
        self._modclass = 'PulsedMeasurementGui'
        self._modtype = 'gui'
        
        ## declare connectors
        self.connector['in']['pulseanalysislogic'] = OrderedDict()
        self.connector['in']['pulseanalysislogic']['class'] = 'PulseAnalysisLogic'
        self.connector['in']['pulseanalysislogic']['object'] = None
#        self.connector['in']['savelogic'] = OrderedDict()
#        self.connector['in']['savelogic']['class'] = 'SaveLogic'
#        self.connector['in']['savelogic']['object'] = None

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
        
        self._pulse_analysis_logic = self.connector['in']['pulseanalysislogic']['object']
#        print("ODMR logic is", self._odmr_logic)
        
#        self._save_logic = self.connector['in']['savelogic']['object']
#        print("Save logic is", self._save_logic)  
        
        # Use the inherited class 'Ui_ODMRGuiUI' to create now the 
        # GUI element:
        self._mw = PulsedMeasurementMainWindow()
        
        
        # Get the image from the logic
        self.signal_image = pg.PlotDataItem(self._pulse_analysis_logic.signal_plot_x, self._pulse_analysis_logic.signal_plot_y)
        self.lasertrace_image = pg.PlotDataItem(self._pulse_analysis_logic.laser_plot_x, self._pulse_analysis_logic.laser_plot_y)
        
        
        # Add the display item to the xy and xz VieWidget, which was defined in
        # the UI file.
        self._mw.lasertrace_plot_ViewWidget.addItem(self.signal_image)
        self._mw.lasertrace_plot_ViewWidget_2.addItem(self.lasertrace_image)
        
        
        # create a color map that goes from dark red to dark blue:

        # Absolute scale relative to the expected data not important. This 
        # should have the same amount of entries (num parameter) as the number
        # of values given in color. 
#        pos = np.linspace(0.0, 1.0, num=10)
#        color = np.array([[127,  0,  0,255], [255, 26,  0,255], [255,129,  0,255],
#                          [254,237,  0,255], [160,255, 86,255], [ 66,255,149,255],
#                          [  0,204,255,255], [  0, 88,255,255], [  0,  0,241,255],
#                          [  0,  0,132,255]], dtype=np.ubyte)
#                          
#        color_inv = np.array([ [  0,  0,132,255], [  0,  0,241,255], [  0, 88,255,255],
#                               [  0,204,255,255], [ 66,255,149,255], [160,255, 86,255],
#                               [254,237,  0,255], [255,129,  0,255], [255, 26,  0,255],
#                               [127,  0,  0,255] ], dtype=np.ubyte)
#                          
#        colmap = pg.ColorMap(pos, color_inv)        
#        self.colmap_norm = pg.ColorMap(pos, color/255)
        
        # get the LookUpTable (LUT), first two params should match the position
        # scale extremes passed to ColorMap(). 
        # I believe last one just has to be >= the difference between the min and max level set later
#        lut = colmap.getLookupTable(0, 1, 2000)
            
#        self.odmr_matrix_image.setLookupTable(lut)
        
        # Set the state button as ready button as default setting.
        self._mw.radioButton.click()
        
        # Configuration of the comboWidget
#        self._mw.mode_ComboWidget.addItem('Off')
#        self._mw.mode_ComboWidget.addItem('CW')
        
        
        #######################################################################
        ##                Configuration of the InputWidgets                  ##
        #######################################################################
        
#        # Add Validators to InputWidgets 
#        validator = QtGui.QDoubleValidator()
#        validator2 = QtGui.QIntValidator()
#        
#        self._mw.frequency_InputWidget.setValidator(validator)
#        self._mw.start_freq_InputWidget.setValidator(validator)
#        self._mw.step_freq_InputWidget.setValidator(validator)
#        self._mw.stop_freq_InputWidget.setValidator(validator)
#        self._mw.power_InputWidget.setValidator(validator)
#        self._mw.runtime_InputWidget.setValidator(validator2)
#        self._sd.matrix_lines_InputWidget.setValidator(validator)
#        
#        # Take the default values from logic:
#        self._mw.frequency_InputWidget.setText(str(self._odmr_logic.MW_frequency))     
#        self._mw.start_freq_InputWidget.setText(str(self._odmr_logic.MW_start))
#        self._mw.step_freq_InputWidget.setText(str(self._odmr_logic.MW_step))
#        self._mw.stop_freq_InputWidget.setText(str(self._odmr_logic.MW_stop))
#        self._mw.power_InputWidget.setText(str(self._odmr_logic.MW_power))
#        self._mw.runtime_InputWidget.setText(str())
#        self._sd.matrix_lines_InputWidget.setText(str(self._odmr_logic.NumberofLines))
#        self._sd.clock_frequency_InputWidget.setText(str(self._odmr_logic._clock_frequency))
#        
#        # Update the inputed/displayed numbers if return key is hit:
#
#        self._mw.frequency_InputWidget.returnPressed.connect(self.change_frequency)
#        self._mw.start_freq_InputWidget.returnPressed.connect(self.change_start_freq)
#        self._mw.step_freq_InputWidget.returnPressed.connect(self.change_step_freq)
#        self._mw.stop_freq_InputWidget.returnPressed.connect(self.change_stop_freq)
#        self._mw.power_InputWidget.returnPressed.connect(self.change_power)
#        self._mw.runtime_InputWidget.returnPressed.connect(self.change_runtime)
#        
#        # Update the inputed/displayed numbers if the cursor has left the field:
#
#        self._mw.frequency_InputWidget.editingFinished.connect(self.change_frequency)
#        self._mw.start_freq_InputWidget.editingFinished.connect(self.change_start_freq)
#        self._mw.step_freq_InputWidget.editingFinished.connect(self.change_step_freq)
#        self._mw.stop_freq_InputWidget.editingFinished.connect(self.change_stop_freq)
#        self._mw.power_InputWidget.editingFinished.connect(self.change_power)
#        self._mw.runtime_InputWidget.editingFinished.connect(self.change_runtime)
        
        
        
        #######################################################################
        ##                      Connect signals                              ##
        #######################################################################
       
       # Connect the RadioButtons and connect to the events if they are clicked:
        self._mw.radioButton.toggled.connect(self.idle_clicked)
        self._mw.radioButton_2.toggled.connect(self.run_clicked)
                
        self._pulse_analysis_logic.signal_laser_plot_updated.connect(self.refresh_lasertrace_plot)
        self._pulse_analysis_logic.signal_signal_plot_updated.connect(self.refresh_signal_plot)
        
        
        
         # Show the Main ODMR GUI:
        self._mw.show()



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

#            
#
#        
#    ###########################################################################
#    ##                         Change Methods                                ##
#    ###########################################################################
#    
#    def change_frequency(self):
#        self._odmr_logic.MW_frequency = float(self._mw.frequency_InputWidget.text())
#        
#    def change_start_freq(self):
#        self._odmr_logic.MW_start = float(self._mw.start_freq_InputWidget.text())
#        
#    def change_step_freq(self):
#        self._odmr_logic.MW_step = float(self._mw.step_freq_InputWidget.text())
#        
#    def change_stop_freq(self):
#        self._odmr_logic.MW_stop = float(self._mw.stop_freq_InputWidget.text())
#        
#    def change_power(self):
#        self._odmr_logic.MW_power = float(self._mw.power_InputWidget.text())
#        
#    def change_runtime(self):
#        pass