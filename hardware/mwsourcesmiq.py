
from pyqtgraph.Qt import QtCore, QtGui
from core.Base import Base
from hardware.mwsourceinterface import MWInterface
from visa import instrument

class MWSMIQ(Base,MWInterface):
    """This is the Interface class to define the controls for the simple 
    microwave hardware.
    """
    
    def __init__(self, manager, name, config = {}, **kwargs):
        Base.__init__(self, manager, name, configuation=config, callback_dict = {})
        self._gpib_address = "dummy"
        self._gpib_timeout = 20
        try: 
            self._gpib_connetion = instrument(self._gpib_address, 
                                              timeout=self._gpib_timeout)
        except:
            self.logMsg("This is MWSMIQ: could not connect to the GPIB address >>{}<<.".format(self._gpib_address), messageType='error')
            raise
        
    def on(self):
        """ Switches on any preconfigured microwave output. 
        <blank line>
        @return int: error code (0:OK, -1:error)
        """ 
        self.logMsg("This is MWInterface>on: Please implement this function.", messageType='status')
        return 0
    
    def off(self):
        """ Switches off any microwave output. 
        <blank line>
        @return int: error code (0:OK, -1:error)
        """
        self.logMsg("This is MWInterface>off: Please implement this function.", messageType='status')
        return -1
        
    def power(self,power=None):
        """ Sets and gets the microwave output power. 
        <blank line>
        @param float power: if defined, this power is set at the device
        <blank line>
        @return float: the power set at the device
        """
        # This is not a good way to implement it!
        self.logMsg("This is MWInterface>power: Please implement this function.", messageType='status')
        return 0.0
    
    def get_power(self):
        """ Gets the microwave output power. 
        <blank line>
        @return float: the power set at the device
        """
        # This is not a good way to implement it!
        self.logMsg("This is MWInterface>get_power: Please implement this function.", messageType='status')
        return 0.0
        
    def set_power(self,power=None):
        """ Sets the microwave output power. 
        <blank line>
        @param float power: this power is set at the device
        <blank line>
        @return int: error code (0:OK, -1:error)
        """
        # This is not a good way to implement it!
        self.logMsg("This is MWInterface>set_power: Please implement this function.", messageType='status')
        return -1