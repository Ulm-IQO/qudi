
import numpy as np
import os
import pyqtgraph as pg
import time
import datetime
import pyqtgraph
import pyqtgraph.exporters
from tkinter import Tk
import tkinter.filedialog as fd

from core.connector import Connector
from gui.colordefs import QudiPalettePale as palette
from gui.guibase import GUIBase
from gui.guiutils import ColorBar
from gui.colordefs import ColorScaleInferno
from qtpy import QtGui
from qtpy import QtCore
from qtpy import QtWidgets
from qtpy import uic



class TTWindow(QtWidgets.QMainWindow):
    """ Create the Main Window based on the *.ui file. """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ttg2.ui')

        # Load it
        super(TTWindow, self).__init__()
        uic.loadUi(ui_file, self)
        self.show()



class TTGui(GUIBase):
    """

    """
    
    # declare connectors
    timetaggerlogic = Connector(interface='TimeTaggerLogic')
    savelogic = Connector(interface='SaveLogic')

    sigUpdatePlotParams = QtCore.Signal(str, int, int)

    def on_deactivate(self):
        """ Reverse steps of activation

        @return int: error code (0:OK, -1:error)
        """
        self._mw.close()
        return 0

    def on_activate(self):
        """ 

        """
        self._timetaggerlogic = self.timetaggerlogic()

        self._savelogic = self.savelogic()
        self._timetaggerlogic.sigUpdate.connect(self.update_plots)
        self.sigUpdatePlotParams.connect(self._timetaggerlogic.update_params)
        self.currentChan = 1
        self.binWidth = 100
        self.numBins = 1000
        self.refreshTime = 1
        self.corrChans = {"start":1, "stop":2}
        self.delayTimes = [0, 0, 0, 0, 0, 0, 0, 0]
        self.chanTrig = 5
        self.apdChands = [1,2,3,4]
        self.allChans = [1,2,3,4,5,6,7,8]
        self.trigChans = [5,6,7,8]
        self.dataChans = [1,2,3,4]
        self.dataDir = ''
        self.saveDir = ''
        self.maxDumps = 1000000000
        self.maxStream = 1000000000

        # list of all the parameter names
        self.list_params = ['currentChan',
                    'binWidth',
                    'numBins',
                    'refreshTime',
                    'corrChans',
                    'delayTimes',
                    'chanTrig',
                    'apdChands',
                    'allChans',
                    'trigChans',
                    'dataChans',
                    'dataDir',
                    'saveDir',
                    'maxDumps',
                    'maxStream'
                ]

        self._mw = TTWindow()
        self.init_connections_ui()
        self.init_params_ui()
        self._timetaggerlogic.init_plots()
        # Add save file tag input box
        self.setup_plots()
        

    def setup_plots(self):
        self.font = QtGui.QFont()
        self.font.setPixelSize(20)
        self.p0 = self._mw.widget_counter.addPlot()
        self.p0 = self.plot_curve(self.p0, return_p=True)
        self.curve_counter = self.p0.plot()

        self.trig_len=150   # in ns
        self.p1 = self._mw.widget_hist.addPlot()
        self.p1 = self.plot_curve(self.p1, return_p=True)
        self.curve_hist = self.p1.plot()

        self.p2 = self._mw.widget_corr.addPlot()
        self.curve_corr = self.plot_curve(self.p2)

        self.p31 = self._mw.widget_freeze.addPlot()
        self.p31 = self.plot_curve(self.p31, return_p=True)
        self.p31.addItem(self.lr41)
        self.curve_freeze_1 = self.p31.plot()

        self._mw.widget_freeze.nextRow()
        self.p32 = self._mw.widget_freeze.addPlot()
        self.p32 = self.plot_curve(self.p32, return_p=True)
        self.p32.addItem(self.lr42)
        self.curve_freeze_2 = self.p32.plot()

    def plot_curve(self, p, return_p = False):
        p.setLabel('left', text='kcps')
        p.setLabel('bottom', text='T, ns')
        p.showGrid(x=True, y=True, alpha=0.2)
        p.getAxis("bottom").tickFont = self.font
        p.getAxis("left").tickFont = self.font
        p.getAxis("bottom").setStyle(tickTextOffset = 20)
        if return_p:
            return p
        else:
            return p.plot()

    def init_params_ui(self):
        self._mw.refreshTextField.setText(str(self.refreshTime))
        self._mw.number_of_bins_ttTextField.setText(str(self.numBins))
        self._mw.bins_width_ttTextField.setText(str(self.binWidth))
        self._mw.delay_TextField.setText(str(self.delayTimes[self.currentChan-1]))
        self._mw.tabsWidget.setCurrentIndex(0)

    def init_connections_ui(self):

        self.lr41 = pg.LinearRegionItem([40,70])
        self.lr41.setZValue(1)
        self.lr42 = pg.LinearRegionItem([40,70])
        self.lr42.setZValue(1)


        # SET BINS
        self._mw.bins_width_ttTextField.returnPressed.connect(self.setBins)
        self._mw.number_of_bins_ttTextField.returnPressed.connect(self.setBins)
        # SET REFRESH TIME
        self._mw.refreshTextField.returnPressed.connect(self.setRefreshTime)

        # SET DELAY TIME
        self._mw.delay_TextField.returnPressed.connect(self.delayTime)

        # DUMP DATA
        # self._mw.saveDumpCheckBox.toggled.connect(self.dumpData)
        # self._mw.actionNew_cooldown.triggered.connect(self.new_cooldown)

        # SAVE DATA
        self._mw.save_g2_pushButton.clicked.connect(self.save_data_g2)

        # SELECT CHANNEL1
        self._mw.hist_channel_ComboBox.setCurrentIndex(self.currentChan - 1)
        self._mw.hist_channel_ComboBox.currentTextChanged.connect(self.setChannel)
        # NEW MEASUREMENT
        self._mw.new_measurement_PushButton.clicked.connect(self.newMeasurement)

        # FREEZE
        self._mw.freeze_PushButton.clicked.connect(self.switch)
        self.freeze = False
        self.lr42.sigRegionChanged.connect(self.regionChanged42)
        self.lr41.sigRegionChanged.connect(self.regionChanged41)

        # SAVE PARAMS
        self._mw.saveParams_PushButton.clicked.connect(self.save_parmas)
        # self._mw.saveButt.clicked.connect(self.save_Params)

        # LOAD PARAMS
        self._mw.loadParams_PushButton.clicked.connect(self.load_params)
        # self._mw.loadButt.clicked.connect(self.load_Params)

        # PLOT DATA
        # self._mw.saveFig.clicked.connect(self.saveFigure)

    
    def regionChanged41(self):
        regionOf41 = self.lr41.getRegion()
        self.lr42.setRegion(regionOf41)

        region = self.lr41.getRegion()
        # print('Regio', region)
        self._mw.pulseLen.setText(str(np.round(abs(region[1] - region[0]), 1)) + ', ns')

    def regionChanged42(self):
        regionOf42 = self.lr42.getRegion()
        self.lr41.setRegion(regionOf42)

    def delayTime(self):
        self.delayTime = int(self.sender().text())
        self.delayTimes[self.currentChan-1] = self.delayTime
        self.tagger.setInputDelay(delay=self.delayTime, channel = self.currentChan)
        self.newMeasurement()

    def setRefreshTime(self):
        self.refreshTime = int(self.sender().text())
        self.moving_average_upper = int(self.sender().text())

    def switch(self):
        self.freeze = not self.freeze

    def setBins(self):
        self.numBins = int(self._mw.number_of_bins_ttTextField.text())
        self.binWidth = int(self._mw.bins_width_ttTextField.text())
        self.update_plot_params(self.numBins, self.binWidth)
        print(f"Number of bins: {self.numBins}\tbin width:{self.binWidth}")


    def setCounterBins(self):
        self.numBinsCounter = int(self._mw.number_of_bins_ttTextField.text())
        self.binWidthCounter = int(self._mw.bins_width_ttTextField.text())
        print(f"Number of bins: {self.numBinsCounter}\tbin width:{self.binWidthCounter}")


    def newMeasurement(self):
        self._timetaggerlogic.new_measurement()

    def setChannel(self):
        ch = self.sender()
        print(ch.currentText())
        if ch.currentText() == "all":
            self.currentChan = [i for i in self.allChans]
            print(self.currentChan)
            self.newMeasurement()
            return
        print("setChannel1", self._mw.hist_channel_ComboBox.currentIndex() + 1)
        self.currentChan = self._mw.hist_channel_ComboBox.currentIndex() + 1
        self.newMeasurement()


    def update_plots(self):
        # t = np.linspace(0, self.numBins*self.binWidth/1000, self.numBins)
        
        def plot_counter():
            self.curve_counter.setData(self._timetaggerlogic.time_counter, self._timetaggerlogic.counter_tt.getData()[1])

        def plot_histog():
            self.curve_hist.setData(self._timetaggerlogic.time_hist, self._timetaggerlogic.hist_tt.getData())

        def plot_correlation():
            self.curve_corr.setData(self._timetaggerlogic.time_corr, self._timetaggerlogic.corr_tt.getData())

        def plot_freeze():
            if self.freeze:
                self.curve_freeze_1.setData(self._timetaggerlogic.time_hist, self._timetaggerlogic.hist_tt.getData())
            else:
                self.curve_freeze_2.setData(self._timetaggerlogic.time_hist, self._timetaggerlogic.hist_tt.getData())
                

        #TODO: plot depending on what tab is open
        graphs = [plot_counter, plot_histog, plot_correlation, plot_freeze]
        graphs[self._mw.tabsWidget.currentIndex()]()

        # if self.m_ui.saveToggle.isChecked():
        #     if self.loop_dump // 20 == 1:
        #         try:
        #             if self.dump.isRunning():
        #                 self.m_ui.dumpSize.setText(f"{round(getsize(self.dumpPath)/1024**2)} MB")
        #         except AttributeError:
        #             print("No Dump yet!")
        #         self.loop_dump = 0
        #     self.loop_dump+=1

        

        # if self.refreshTime > 0:
        #     if self.loop_refresh[0] // (20*self.refreshTime)  == 1:
        #         self.hist.clear()
        #         self.loop_refresh[0] = 0
        #     self.loop_refresh[0]+=1
    def update_plot_params(self, number_of_bins, bin_width):
        ind = self._mw.tabsWidget.currentIndex()
        attr = ["counter", "hist", "corr", "hist"][ind]
        self.sigUpdatePlotParams.emit(attr, number_of_bins, bin_width)



    def save_data_g2(self):
        """Saves the data.
        
        Saves the plot as a figure and the data including axes in a dict.
        """

        # TODO: This should be moved to logic along with the storage of the values.

        # get index of tab for correlation
        page_corr = self._mw.tabsWidget.findChild(QtWidgets.QWidget, 'corr_tab')
        index_corr = self._mw.tabsWidget.indexOf(page_corr)

        # get index of current tab
        index_current = self._mw.tabsWidget.currentIndex()

        # atm only save function for g2 is implemented
        if index_current == index_corr:

            timestamp = datetime.datetime.now()
            filetag = self._mw.save_g2_nametag_lineEdit.text()

            filepath = self._savelogic.get_path_for_module(module_name='timetagger')

            if len(filetag) > 0:
                filename = os.path.join(filepath, '{0}_{1}_g2function'.format(timestamp.strftime('%Y%m%d-%H%M-%S'), filetag))
            else:
                filename = os.path.join(filepath, '{0}_g2function'.format(timestamp.strftime('%Y%m%d-%H%M-%S'),))

            exporter_graph = pyqtgraph.exporters.SVGExporter(self.p2)
            exporter_graph.export(filename  + '.svg')

            data = self.curve_corr.getData()

            # data to save
            data_dict = {}
            data_dict['axis0'] = data[0]
            data_dict['axis1'] = data[1]

            # current params
            param_dict = self.create_param_dict()
            
            filename_ending = filename + '.dat'

            self._savelogic.save_data(data_dict, filepath=filepath, parameters=param_dict,
                                   filename=filename_ending, timestamp=timestamp)
        
        else:
            print('Save functionality for opened tab is not implemented')
            return


    def create_param_dict(self):
        """Takes the parameters specified in self.list_params and returns them as dict.
        """
        # create the dict and store parameter values
        parameters = {}
        for param in self.list_params:
            parameters[param] = eval('self.' + param)

        return parameters


    def save_parmas(self):
        """Saves all parameters as a dict."""
        parameters = self.create_param_dict()

        #create filename and filepath
        timestamp = datetime.datetime.now()
        filetag = self._mw.save_g2_nametag_lineEdit.text()

        filepath = self._savelogic.get_path_for_module(module_name='timetagger')

        if len(filetag) > 0:
            filename = os.path.join(filepath, '{0}_{1}_parameters'.format(timestamp.strftime('%Y%m%d-%H%M-%S'), filetag))
        else:
            filename = os.path.join(filepath, '{0}_parameters'.format(timestamp.strftime('%Y%m%d-%H%M-%S'),))

        self._savelogic.save_dict(dic=parameters,filename=filename, filepath=filepath)

        


    def load_params(self):
        root = Tk()
        root.withdraw() # we don't want a full GUI, so keep the root window from appearing
        root.wm_attributes('-topmost', 1) # push to front
        fname = fd.askopenfilename() # show an "Open" dialog box and return the path to the selected file
        # load parameter dict from file
        parameters = self._savelogic.load_dict(fname)
        # set parameters
        for key in parameters.keys():
            exec('self.' + key + '= parameters[key]')
        # update parameters in gui
        self.init_params_ui()