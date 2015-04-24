# -*- coding: utf-8 -*-





####################
# From Qt designer #
####################


# Form implementation generated from reading ui file 'ConfocalWindowTemplate.ui'
#
# Created: Thu Apr 23 09:28:53 2015
#      by: PyQt4 UI code generator 4.10.4
#
# WARNING! All changes made in this file will be lost!

#from PyQt4 import QtCore, QtGui
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph as pg

from collections import OrderedDict
from core.Base import Base
import numpy as np

# To convert the ui file to a raw ConfocalGui_ui.py file use the python script
# in the Anaconda directory, which you can find in:
#
# "<Installation-dir of Anacona>\Anaconda3\Lib\site-packages\PyQt4\uic\pyuic.py".
#
# Then use that script like
#
# "<Installation-dir of Anacona>\Anaconda3\Lib\site-packages\PyQt4\uic\pyuic.py" ConfocalWindowTemplate.ui > ConfocalGui_ui.py
#
# to convert to ConfocalGui_ui.py.
from gui.Confocal.ConfocalGui_ui import Ui_MainWindow




class CrossROI(pg.ROI):
	def __init__(self, pos, size, **args):
		pg.ROI.__init__(self, pos, size, **args)
		center = [0.5, 0.5]    
		self.addTranslateHandle(center)


class CrossLine(pg.InfiniteLine):
	def __init__(self, **args):
		pg.InfiniteLine.__init__(self, **args)

	def adjust(self, extroi):
		if self.angle == 0:
			self.setValue(extroi.pos()[1] + extroi.size()[1] * 0.5 )
		if self.angle == 90:
			self.setValue(extroi.pos()[0] + extroi.size()[0] * 0.5 )


class ConfocalMainWindow(QtGui.QMainWindow,Ui_MainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.setupUi(self)
        
        

class ConfocalGui(Base,QtGui.QMainWindow,Ui_MainWindow):
    """
    Confocal Class
    """
    sigStartCounter = QtCore.Signal()
    sigStopCounter = QtCore.Signal()

    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        c_dict = {'onactivate': self.initUI}
        Base.__init__(self,
                    manager,
                    name,
                    config,
                    c_dict)
        
        self._modclass = 'ConfocalGui'
        self._modtype = 'gui'
        
        ## declare connectors
        self.connector['in']['confocallogic1'] = OrderedDict()
        self.connector['in']['confocallogic1']['class'] = 'ConfocalLogic'
        self.connector['in']['confocallogic1']['object'] = None

        self.logMsg('The following configuration was found.', 
                    msgType='status')
                            
        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]), 
                        msgType='status')
  
        print ('\n in the Confocal GUI init\n')


                      

    def initUI(self, e=None):
        """ Definition and initialisation of the GUI plus staring the measurement.

        Configure and         
        
        """
         
        self._scanning_logic = self.connector['in']['confocallogic1']['object']
        print("Scanning logic is", self._scanning_logic)
        
        # Use the inherited class 'Ui_ConfocalGuiTemplate' to create now the 
        # GUI element:
        self._mw = ConfocalMainWindow()
        
        arr = np.ones((200, 200), dtype=float)
        arr[45:55, 45:55] = 0
        arr[25, :] = 5
        arr[:, 25] = 5
        arr[75, :] = 5
        arr[:, 75] = 5
        arr[50, :] = 10
        arr[:, 50] = 10
        arr += np.sin(np.linspace(0, 20, 200)).reshape(1, 200)
        arr += np.random.normal(size=(200,200))
#
#        self.xy_image = pg.ImageItem(arr)
#        self._mw.graphicsView.addItem(self.xy_image)
#        
#        # create Region of Interest
#        
#        cr = CrossROI([100, 100], [10, 10], pen={'color': "00F", 'width': 1},removable=True )
#        
#        self._mw.graphicsView.addItem(cr)
#        
#        self._mw.graphicsView.enableMouse = False        
#        
#        ilh = CrossLine(pos=cr.pos()+cr.size()*0.5, angle=0, pen={'color': "00F", 'width': 1} )
#        ilv = CrossLine(pos=cr.pos()+cr.size()*0.5, angle=90, pen={'color': "00F", 'width': 1} )
#
#
#        cr.sigRegionChanged.connect(ilh.adjust)
#        cr.sigRegionChanged.connect(ilv.adjust)
#
#        self._mw.graphicsView.addItem(ilh)
#        self._mw.graphicsView.addItem(ilv)
#
#
#        cr2 = CrossROI([100, 100], [20, 20], pen={'color': "00F", 'width': 1},removable=True )
#
#        self._mw.graphicsView_2.addItem(cr2)
#
#        ilh2 = CrossLine(pos=cr2.pos()+cr.size()*0.5, angle=0, pen={'color': "00F", 'width': 1} )
#        ilv2 = CrossLine(pos=cr2.pos()+cr.size()*0.5, angle=90, pen={'color': "00F", 'width': 1} )
#
#        cr2.sigRegionChanged.connect(ilh2.adjust)
#        cr2.sigRegionChanged.connect(ilv2.adjust)
#
#        self._mw.graphicsView_2.addItem(ilh2)
#        self._mw.graphicsView_2.addItem(ilv2)

        
        print('Main Confocal Windows shown:')
        self._mw.show()
        
        
        
        ## Create image to display
        self.array = np.ones((100, 100), dtype=float)
        self.array[45:55, 45:55] = 0
        self.array[25, :] = 5
        self.array[:, 25] = 5
        self.array[75, :] = 5
        self.array[:, 75] = 5
        self.array[50, :] = 10
        self.array[:, 50] = 10
        self.array += np.sin(np.linspace(0, 20, 100)).reshape(1, 100)
        self.array += np.random.normal(size=(100,100))
        


    def qimage2numpy(qimage, dtype = 'array'):
    	"""Convert QImage to numpy.ndarray.  The dtype defaults to uint8
    	for QImage.Format_Indexed8 or `bgra_dtype` (i.e. a record array)
    	for 32bit color images.  You can pass a different dtype to use, or
    	'array' to get a 3D uint8 array for color images."""
    
    	result_shape = (qimage.height(), qimage.width())
    	temp_shape = (qimage.height(), qimage.bytesPerLine() * 8 / qimage.depth())
    	if qimage.format() in (QtGui.QImage.Format_ARGB32_Premultiplied,
    						   QtGui.QImage.Format_ARGB32,
    						   QtGui.QImage.Format_RGB32):
    		if dtype == 'rec':
    			dtype = bgra_dtype
    		elif dtype == 'array':
    			dtype = np.uint8
    			result_shape += (4, )
    			temp_shape += (4, )
    	elif qimage.format() == QtGui.QImage.Format_Indexed8:
    		dtype = np.uint8
    	else:
    		raise ValueError("qimage2numpy only supports 32bit and 8bit images")
    	# FIXME: raise error if alignment does not match
    	buf = qimage.bits().tobytes()	#.asstring(qimage.numBytes())
    	result = np.frombuffer(buf, dtype).reshape(temp_shape)
    	if result_shape != temp_shape:
    		result = result[:,:result_shape[1]]
    	result = result[...,[2,1,0,3]]
    	if qimage.format() == QtGui.QImage.Format_RGB32 and dtype == np.uint8:
    		result = result[...,:3]
    	return result












    


