#
import rpyc

class QuDi(object):

    def __init__(self):
        self.host = 'localhost'
        self.port = 12346
        self.conn_config = {'allow_all_attrs': True}

    def connect(self, **kwargs):
        self.connection = rpyc.connect(self.host, self.port, config=self.conn_config)

    def getModule(self, name):
        self.connection.root.getModule(name)

