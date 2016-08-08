"""
Configuration file module.

A configuration file is saved in YAML format. This module provides a loader
and a dumper using an OrderedDict instead of the regular dict used by PyYAML.
Additionally, it fixes a bug in PyYAML with scientific notation and allows
to dump numpy dtypes and numpy ndarrays.

The fix of the scientific notation is applied globally at module import.

The idea of the implementation of the OrderedDict was taken from
http://stackoverflow.com/questions/5121931/in-python-how-can-you-load-yaml-mappings-as-ordereddicts
"""

from collections import OrderedDict
import numpy
import re
import yaml

# this fixes a bug in PyYAML with scientific notation
yaml.resolver.Resolver.add_implicit_resolver(
        'tag:yaml.org,2002:float',
        re.compile(
            r'''^(?:[-+]?(?:[0-9][0-9_]*)(?:\.[0-9_]*)?(?:[eE][-+]?[0-9]+)
            |(?:[-+]?(?:[0-9][0-9_]*)\.[0-9_]*)
            |\.[0-9_]+(?:[eE][-+]?[0-9]+)?
            |[-+]?[0-9][0-9_]*(?::[0-5]?[0-9])+\.[0-9_]*
            |[-+]?\.(?:inf|Inf|INF)
            |\.(?:nan|NaN|NAN))$''', re.X),
        list('-+0123456789.'))


def ordered_load(stream, Loader=yaml.Loader):
    """
    Loads a YAML formatted data from stream and puts it into an OrderedDict

    @param stream Stream: stream the data is read from
    @param Loader Loader: Loader base class

    Returns OrderedDict with data. If stream is empty then an empty
    OrderedDict is returned.
    """
    class OrderedLoader(Loader):
        """
        Loader using an OrderedDict
        """
        pass

    def construct_mapping(loader, node):
        """
        The OrderedDict constructor.
        """
        loader.flatten_mapping(node)
        return OrderedDict(loader.construct_pairs(node))

    # add constructor
    OrderedLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        construct_mapping)

    # load config file
    config = yaml.load(stream, OrderedLoader)
    # yaml returns None if the config file was empty
    if config is not None:
        return config
    else:
        return OrderedDict()


def ordered_dump(data, stream=None, Dumper=yaml.Dumper, **kwds):
    """
    dumps (OrderedDict) data in YAML format

    @param data OrderedDict: the data
    @param stream Stream: where the data in YAML is dumped
    @param Dumper Dumper: The dumper that is used as a base class
    """
    class OrderedDumper(Dumper):
        """
        A Dumper using an OrderedDict
        """
        def ignore_aliases(self, data):
            """
            ignore aliases and anchors
            """
            return True

    def ordereddict_representer(dumper, data):
        """
        Representer for OrderedDict
        """
        return dumper.represent_mapping(
            yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
            data.items())

    def int_representer(dumper, data):
        """
        Representer for numpy int dtypes
        """
        return dumper.represent_int(numpy.asscalar(data))

    def float_representer(dumper, data):
        """
        Representer for numpy float dtypes
        """
        return dumper.represent_float(numpy.asscalar(data))

    def ndarray_representer(dumper, data):
        """
        Representer for numpy ndarrays
        """
        return dumper.represent_list(data.tolist())

    # add representers
    OrderedDumper.add_representer(OrderedDict, ordereddict_representer)
    OrderedDumper.add_representer(numpy.uint8, int_representer)
    OrderedDumper.add_representer(numpy.uint16, int_representer)
    OrderedDumper.add_representer(numpy.uint32, int_representer)
    OrderedDumper.add_representer(numpy.uint64, int_representer)
    OrderedDumper.add_representer(numpy.int8, int_representer)
    OrderedDumper.add_representer(numpy.int16, int_representer)
    OrderedDumper.add_representer(numpy.int32, int_representer)
    OrderedDumper.add_representer(numpy.int64, int_representer)
    OrderedDumper.add_representer(numpy.float16, float_representer)
    OrderedDumper.add_representer(numpy.float32, float_representer)
    OrderedDumper.add_representer(numpy.float64, float_representer)
    OrderedDumper.add_representer(numpy.float128, float_representer)
    OrderedDumper.add_representer(numpy.ndarray, ndarray_representer)

    # dump data
    return yaml.dump(data, stream, OrderedDumper, **kwds)


def load(filename):
    """
    Loads a config file

    @param filename str: filename of config file

    Returns OrderedDict
    """
    with open(filename, 'r') as f:
        return ordered_load(f, yaml.SafeLoader)

def save(filename, data):
    """
    saves data to filename in yaml format.

    @param filename str: filename of config file
    @param data OrderedDict: config values
    """
    with open(filename, 'w') as f:
        ordered_dump(data, stream=f, Dumper=yaml.SafeDumper,
                default_flow_style=False)
