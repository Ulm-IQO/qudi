from logic.generic_logic import GenericLogic
import threading

class UserGlobals(GenericLogic):
    """
    This class defines some usefull global variables.
    After loading the module via the config file, the qudi console
    and every module importing this file can access these variables.

    eg. in config.cfg:
    userglobals:
        module.Class: 'user_globals.UserGlobals'

    access in console:
        userglobals.<varname>
    access in module:
        from from logic.user_globals import UserGlobals as as userglobals
        userglobals.<varname>

    """

    _modclass = 'userglobals'
    _modtype = 'logic'

    # experiment control flow
    abort = threading.Event()
    abort.clear()
    next = threading.Event()
    next.clear()


    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        pass

    def on_deactivate(self):
        """ """
        pass