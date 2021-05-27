
import numpy as np
import os
import pyqtgraph as pg
import time

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

    sigStopScan = QtCore.Signal()

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

        # Use the inherited class 'Ui_VoltagescannerGuiUI' to create now the
        # GUI element:
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

        self._mw = TTWindow()
        self.init_connections_ui()
        self.init_params_ui()
        self.init_hists()
        # Add save file tag input box
        self.setup_plots()
        

    def setup_plots(self):
        self.font = QtGui.QFont()
        self.font.setPixelSize(20)
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
        self._mw.binsTextField.setText(str(self.numBins))
        self._mw.binsWidthTextField.setText(str(self.binWidth))
        self._mw.delayTextField.setText(str(self.delayTimes[self.currentChan-1]))
        self._mw.tabWidget_1.setCurrentIndex(0)

    def init_connections_ui(self):

        self.lr41 = pg.LinearRegionItem([40,70])
        self.lr41.setZValue(1)
        self.lr42 = pg.LinearRegionItem([40,70])
        self.lr42.setZValue(1)


        # SET BINS
        self._mw.binsTextField.returnPressed.connect(self.setBins)
        self._mw.binsWidthTextField.returnPressed.connect(self.setBins)
        # SET REFRESH TIME
        self._mw.refreshTextField.returnPressed.connect(self.setRefreshTime)

        # SET DELAY TIME
        self._mw.delayTextField.returnPressed.connect(self.delayTime)

        # DUMP DATA
        self._mw.saveToggle.toggled.connect(self.dumpData)
        self._mw.actionNew_cooldown.triggered.connect(self.new_cooldown)

        # SELECT CHANNEL1
        self._mw.chSelect.setCurrentIndex(self.currentChan - 1)
        self._mw.chSelect.currentTextChanged.connect(self.setChannel)
        # NEW MEASUREMENT
        self._mw.button.clicked.connect(self.newMeasurement)

        # FREEZE
        self._mw.freeze.clicked.connect(self.switch)
        self.freeze = False
        self.lr42.sigRegionChanged.connect(self.regionChanged42)
        self.lr41.sigRegionChanged.connect(self.regionChanged41)

        # SAVE PARAMS
        self._mw.saveButt.clicked.connect(self.save_Params)

        #LOAD PARAMS
        self._mw.loadButt.clicked.connect(self.load_Params)

        # PLOT DATA
        self._mw.saveFig.clicked.connect(self.saveFigure)

    
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
        self.numBins = int(self._mw.binsTextField.text())
        self.binWidth = int(self._mw.binsWidthTextField.text())
        print(f"Number of bins: {self.numBins}\tbin width:{self.binWidth}")


    def setCounterBins(self):
        self.numBinsCounter = int(self._mw.binsCounterTextField.text())
        self.binWidthCounter = int(self._mw.binsWidthCounterTextField.text())
        print(f"Number of bins: {self.numBinsCounter}\tbin width:{self.binWidthCounter}")

    def setChannel(self):
        ch = self.sender()
        print(ch.currentText())
        if ch.currentText() == "all":
            self.currentChan = [i for i in self.allChans]
            print(self.currentChan)
            self.newMeasurement()
            return
        print("setChannel1", self._mw.chSelect.currentIndex() + 1)
        self.currentChan = self._mw.chSelect.currentIndex() + 1
        self.newMeasurement()




