# -*- coding: utf-8 -*-

from core.Base import Base

class GUIBase(Base):
    """This is the GUI base class. It provides functions that every GUI module should have.
    """
    _modclass = 'GUIBase'
    _modtype = 'Gui'
    
    def __init__(self, manager, name, configuation = {}, callbacks = {}, **kwargs):
        Base.__init__(self, manager, name, configuation, callbacks, **kwargs)

    def show(self):
        self.logMsg('Every GUI module needs to reimplement the show() function!', msgType='error')

