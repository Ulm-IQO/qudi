from qtpy import QtCore
from interface.spectrometer_interface import SpectrometerInterface
from core.module import Base
from core.configoption import ConfigOption

import socket
import numpy as np
import pickle
import time

def connect(func):
    def wrapper(self, *arg, **kw):
        try:
            # Establish connection to TCP server and exchange data
            self.tcp_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_client.connect((self.host_ip, self.server_port))
            res = func(self, *arg, **kw)
        finally:
            self.tcp_client.close()
        return res
    return wrapper

    
class PrincetonSpectrometerClient(Base, SpectrometerInterface):
    _integration_time = 10
    _shift_wavelength = 0.57274
    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
        #locking for thread safety
        self.wavelength = np.linspace(0, 1339, 1340)
        

    def on_activate(self):
        self.host_ip, self.server_port = '192.168.202.20', 3336
        self._integration_time = self.getExposure()
        # self.tcp_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
    @connect
    def send_request(self, request, action=None, recv_bytes = 1024):
        self.tcp_client.sendall(request.encode())
        received = self.tcp_client.recv(recv_bytes)
        response = pickle.loads(received[1:], encoding="latin1")
        flag = received[:1].decode()
        
        if flag == 'k':
            if action != None:
                self.tcp_client.sendall(action.encode())
            else:
                print("Set action! ")
        elif flag == 'u':
            return response
    
    def on_deactivate(self):
        self.tcp_client.close()

    def recordSpectrum(self):
        wavelengths = self.send_request("get_wavelength", recv_bytes = 32768)
        specdata = np.empty((2, len(wavelengths)), dtype=np.double)
        specdata[0] = wavelengths + self._shift_wavelength
        specdata[1] = self.send_request("get_spectrum", recv_bytes = 32768)
        return specdata

    def setExposure(self, exposureTime):
        return self.send_request("set_exposure_time", action=str(exposureTime* 1000))
    def getExposure(self):
        return self.send_request("get_exposure_time") / 1000
    
    def clearBuffer(self):
        pass
