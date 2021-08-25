# from qtpy import QtCore

# from core.module import Base
# from core.configoption import ConfigOption

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

    
class PrincetonSpectrometerClient():
    def __init__(self):#, config, **kwargs):
        #super().__init__(config=config, **kwargs)
        #locking for thread safety
        self.wavelength = np.linspace(0, 1339, 1340)
        

    def on_activate(self):
        self.host_ip, self.server_port = '192.168.202.81', 3336
        # self.tcp_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
    @connect
    def send_request(self, request, action=None):
        self.tcp_client.sendall(request.encode())
        received = self.tcp_client.recv(1024)
        response = pickle.loads(received[1:])
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
    def get_spectrum(self):
        return self.send_request("get_spectrum")
    def get_wavelength(self):
        return self.send_request("get_wavelength")