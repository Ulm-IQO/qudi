class MWInterface():
    """This is the Interface class to define the controls for the simple 
    microwave hardware.
    """
    
    def on(self):
        """ Switches on any preconfigured microwave output. 
        <blank line>
        @return int: error code (0:OK, -1:error)
        """ 
        self.logMsg("This is MWInterface>on: Please implement this function.", messageType='status')
        return -1
    
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