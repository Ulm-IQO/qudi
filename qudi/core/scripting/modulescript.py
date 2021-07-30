# -*- coding: utf-8 -*-

"""
This file contains a basic script class to run with qudi module dependencies.
Also contains a Qt TableModel class to store and handle available ModuleScript classes and
compatible generic callables.

Qudi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Qudi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Qudi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

__all__ = ['ModuleScript', 'ModuleScriptImporter', 'ScriptsTableModel']

import logging
import importlib
from PySide2 import QtCore
from typing import Union, Callable

from qudi.core.connector import Connector
from qudi.util.models import DictTableModel


class ModuleScript(QtCore.QRunnable, QtCore.QObject):
    """

    """
    # Declare all module connectors used in this script
    # _my_example_module = Connector(name='example_module', interface='MyModuleClassName')

    sigFinished = QtCore.Signal(object)

    def __init__(self, module_connections=None, run_function=None, args=None, kwargs=None):
        super().__init__()
        self.setAutoDelete(False)  # Application programmer is responsible for ownership/lifetime

        # Create connector copies for this script instance and connect them to the modules
        if module_connections is None:
            module_connections = dict()

        connectors = self.module_connectors()
        conn_name_attr_mapping = {conn.name: attr_name for attr_name, conn in connectors.items()}
        missing_mandatory_conn = {conn.name for conn in connectors.values() if not conn.optional}

        for name, module in module_connections.items():
            attr_name = conn_name_attr_mapping.get(name, None)
            if attr_name is None:
                raise ValueError(f'Unknown module connector "{name}" encountered.\n'
                                 f'Valid connections are: {list(conn_name_attr_mapping)}')
            conn = connectors[attr_name].copy()
            conn.connect(module)
            setattr(self, attr_name, conn)
            if name in missing_mandatory_conn:
                missing_mandatory_conn.remove(name)
        if missing_mandatory_conn:
            raise ValueError(f'Missing mandatory connections:\n{missing_mandatory_conn}')

        # cache arguments for run method (if given)
        self.args = tuple() if args is None else args
        self.kwargs = dict() if kwargs is None else kwargs

        # Set run_function as _run bound method
        if callable(run_function):
            self._run = run_function.__get__(self)

        # run method result cache
        self.result = None

    @classmethod
    def module_connectors(cls):
        """ Returns all Connector objects for this script class.
        DO NOT OVERRIDE IN SUBCLASS!

        @return dict: Dict with all Connector objects (values) and their attribute names (keys)
        """
        connectors = dict()
        for c in reversed(cls.mro()[:-4]):
            connectors.update(
                {name: attr for name, attr in vars(c).items() if isinstance(attr, Connector)}
            )
        return connectors

    @property
    def log(self):
        """ Returns a logger object.
        DO NOT OVERRIDE IN SUBCLASS!

        @return logging.Logger: Logger object for this script class
        """
        return logging.getLogger(f'{self.__module__}.{self.__class__.__name__}')

    def __call__(self, *args, **kwargs):
        """ Convenience magic method to run this script like a function
        DO NOT OVERRIDE IN SUBCLASS!

        @param args: Positional arguments passed to run method
        @param kwargs: Keyword arguments passed to run method

        @return object: Result of the script method
        """
        self.args = args
        self.kwargs = kwargs
        self.run()
        return self.result

    @QtCore.Slot()
    def run(self):
        """ Check run prerequisites and execute _run method with pre-cached arguments.
        DO NOT OVERRIDE IN SUBCLASS!
        """
        self.result = None

        if not self.can_run():
            raise RuntimeError(f'Prerequisites to run ModuleScript "{self.__class__.__name__}" '
                               f'not fulfilled.')

        self.result = self._run(*self.args, **self.kwargs)
        self.sigFinished.emit(self.result)

    def can_run(self):
        """ Implement this method in a subclass if you need to check prerequisites before running.

        @return bool: Indicator if the script can be run (default: True) or not (False)
        """
        return True

    def _run(self, *args, **kwargs):
        """ Implement this method in a subclass or provide a callable to the __init__ argument
        "run_function" to be bound as this method.

        @return object: The result of the script (default: None)
        """
        raise NotImplementedError(
            f'No run method configured for ModuleScript "{self.__class__.__name__}".'
        )


class ModuleScriptImporter:
    def __init__(self, script_config: dict):
        self.module, self.object_name = script_config['module.Class'].rsplit('.', 1)

    def import_script(self, reload: bool = True) -> Union[ModuleScript, Callable]:
        mod = importlib.import_module(self.module)
        if reload:
            importlib.reload(mod)
        script = getattr(mod, self.object_name)
        if not issubclass(script, ModuleScript) and not callable(script):
            raise TypeError('Module script to import must be either a subclass of '
                            'qudi.core.scripting.modulescript.ModuleScript or a callable.')
        return script


class ScriptsTableModel(DictTableModel):
    """ Qt compatible table model holding all configured and available ModuleScript QRunnables.
    """
    def __init__(self, script_configurations: dict = None):
        super().__init__(headers='Module Scripts')
        if script_configurations is None:
            script_configurations = dict()
        for name, config in script_configurations.items():
            self.register_script(name, config)

    def register_script(self, name, config):
        if name in self:
            raise KeyError(f'Multiple module script with name "{name}" configured.')
        self[name] = ModuleScriptImporter(config).import_script()
