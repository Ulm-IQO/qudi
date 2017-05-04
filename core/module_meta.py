
from collections import OrderedDict
import copy

class ConfigOption:

    def __init__(self, name=None, **kwargs):
        if name is None:
            self.name = ''
        else:
            self.name = name

    #def __repr__(self):
    #    return '<{0}: {1}>'.format(self.__class__, self.name)

class Connector:

    def __init__(self, name=None, interface_name=None, **kwargs):
        self.name = name
        self.ifname = interface_name
        self.obj = None

    #def __repr__(self):
    #    return '<{0}: name={1}, interface={2}, object={3}>'.format(self.__class__, self.name, self.ifname, self.obj)


class ModuleMeta(type):
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

        # Accumulate metas info from parent classes
        for base in reversed(bases):
            if hasattr(base, '_connectors'):
                connectors.update(copy.deepcopy(base._connectors))
            if hasattr(base, '_config_options'):
                config_options.update(copy.deepcopy(base._config_options))

        # Parse this class's attributes into connector and config_option structures
        for key, value in attrs.items():
            if isinstance(value, Connector):
                connectors[key] = Connector(name=key)
            elif isinstance(value, ConfigOption):
                config_options[key] = ConfigOption(name=key)

        attrs.update(connectors)
        attrs.update(config_options)

        new_class = type.__new__(mcs, name, bases, attrs)
        new_class._connectors = connectors
        new_class._config_options = config_options

        return new_class

