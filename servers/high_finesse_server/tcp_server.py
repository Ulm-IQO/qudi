import socketserver
import time, pickle, ctypes, wlm_api, errno
import numpy as np

class Handler_TCPServer(socketserver.BaseRequestHandler):
    """
    The TCP Server class for demonstration.

    Note: We need to implement the Handle method to exchange data
    with TCP client.

    """

    def handle(self):
        # self.request - TCP socket connected to the client
        
        # print("{} sent smth".format(self.client_address[0]))
        self.api_ = {'get_wavelength': self.get_wavelength, 
        'start_measurements': self.start_measurements, 
        'stop_measurements': self.stop_measurements,
        'get_regulation_mode': self.get_regulation_mode,
        'set_regulation_mode': self.set_regulation_mode,
        'get_reference_course': self.get_reference_course,
        'set_reference_course': self.set_reference_course,
        'get_server_time':self.get_server_time,
        'start_trigger': self.start_trigger,
        'stop_trigger': self.stop_trigger
        }
        
        self.data = self.request.recv(1024).strip()
        option = self.data.decode()
        if option in self.api_.keys():
            self.api_[option]()
        else:
            self.unknown()
        
    def start_trigger(self):
        wlm.start_trigger()
        self.send_object("started")
    def stop_trigger(self):
        wlm.stop_trigger()
        self.send_object("stoped")
    def get_wavelength(self):
        self.send_object(np.array([wlm.get_wavelength(units='air'), time.time() - time_]), flag='c')
    def start_measurements(self):
        wlm.start_measurements()
        self.send_object("started")
    def stop_measurements(self):
        wlm.stop_measurements()
        self.send_object("stoped")
    def get_regulation_mode(self):
        mode = wlm.get_regulation_mode()
        self.send_object(mode)
    def set_regulation_mode(self):
        self.send_object("What would be the regulation mode?", flag='k')
        data = self.request.recv(1024).decode()
        mode = True if data == "on" else False if data == "off" else wlm.get_regulation_mode()
        print("Mode", mode)
        wlm.set_regulation_mode(mode)
    def get_reference_course(self):
        course = wlm.get_reference_course()
        self.send_object(course)
    def set_reference_course(self):
        self.send_object("What would be the reference?", flag='k')
        reference = self.request.recv(1024).decode()
        wlm.set_reference_course(reference)
        # self.send_object(reference)

    def get_server_time(self):
        self.send_object(time.time(), flag='u')
    
    def unknown(self):
        self.send_object(f"No command. Try one of these {self.api_.keys()}")
        
    def send_object(self, obj, flag = 'u'):
        msg = pickle.dumps(obj)
        msg = flag.encode() + msg
        self.request.sendall(msg)

if __name__ == "__main__":
    HOST, PORT = "0.0.0.0", 1243
    wlm = wlm_api.WLM()
    wlm_time = np.zeros((1, 2))
    time_ = time.time()
    # Init the TCP server object, bind it to the localhost on 9999 port
    tcp_server = socketserver.TCPServer((HOST, PORT), Handler_TCPServer)

    # Activate the TCP server.
    # To abort the TCP server, press Ctrl-C.
    tcp_server.serve_forever()
