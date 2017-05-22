
import copy
from qtpy import QtCore
from collections import OrderedDict

class StatusVar:

    def __init__(self, name=None, default=None, var_name=None, **kwargs):
        self.var_name = var_name
        if name is None and var_name is None:
            self.name = ''
        elif name is None:
            self.name = var_name
        else:
            self.name = name

        self.default = default

    def copy(self, **kwargs):
        """ Create a new instance of StatusVar with copied values and update """
        newargs = {}
        newargs['name'] = copy.copy(self.name)
        newargs['default'] = copy.copy(self.default)
        newargs['var_name'] = copy.copy(self.var_name)
        newargs.update(kwargs)
        return StatusVar(**newargs)

    def type_check(self, check_this):
        return True


class ConfigOption:

    def __init__(self, name=None, default=None, var_name=None, **kwargs):
        self.var_name = var_name
        if name is None and var_name is None:
            self.name = ''
        elif name is None:
            self.name = var_name
        else:
            self.name = name
 
        self.default = default

    #def __repr__(self):
    #    return '<{0}: {1}>'.format(self.__class__, self.name)

    def copy(self, **kwargs):
        """ Create a new instance of ConfigOption with copied values and update """
        newargs = {}
        newargs['name'] = copy.copy(self.name)
        newargs['default'] = copy.copy(self.default)
        newargs['var_name'] = copy.copy(self.var_name)
        newargs.update(kwargs)
        return ConfigOption(**newargs)


class Connector:

    def __init__(self, name=None, interface_name=None, **kwargs):
        self.name = name
        self.ifname = interface_name
        self.obj = None

    #def __repr__(self):
    #    return '<{0}: name={1}, interface={2}, object={3}>'.format(self.__class__, self.name, self.ifname, self.obj)

    def copy(self, **kwargs):
        """ Create a new instance of Connector with copied values and update """
        newargs = {}
        newargs['name'] = copy.copy(self.name)
        newargs['interface_name'] = copy.copy(self.ifname)
        newargs.update(kwargs)
        return Connector(**newargs)


class ModuleMeta(type(QtCore.QObject)):
    """
    Metaclass for Qudi modules
    """

    def __new__(mcs, name, bases, attrs):
        """
        Parse declared connectors and config options into the usual dictionary structures.
        """

        # collect meta info in dicts
        connectors = OrderedDict()
        config_options = OrderedDict()
        status_vars = OrderedDict()

        # Accumulate metas info from parent classes
        for base in reversed(bases):
            if hasattr(base, '_connectors'):
                connectors.update(copy.deepcopy(base._connectors))
            if hasattr(base, '_config_options'):
                config_options.update(copy.deepcopy(base._config_options))
            if hasattr(base, '_stat_var'):
                status_vars.update(copy.deepcopy(base._stat_var))

        # Parse this class's attributes into connector and config_option structures
        for key, value in attrs.items():
            if isinstance(value, Connector):
                connectors[key] = value.copy(name=key)
            elif isinstance(value, ConfigOption):
                config_options[key] = value.copy(var_name=key)
            elif isinstance(value, StatusVar):
                status_vars[key] = value.copy(var_name=key)

        attrs.update(connectors)
        attrs.update(config_options)
        attrs.update(status_vars)

        new_class = type.__new__(mcs, name, bases, attrs)
        new_class._conn = connectors
        new_class._config_options = config_options
        new_class._stat_vars = status_vars

        return new_class

