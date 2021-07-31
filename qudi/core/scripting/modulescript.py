# -*- coding: utf-8 -*-

"""
This file contains a basic script class to run with qudi module dependencies as well as various
helper classes to run and manage these scripts.

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

__all__ = ['ModuleScript', 'ModuleScriptImporter', 'ScriptsTableModel', 'ModuleScriptFactory',
           'ModuleScriptRunner']

import importlib
from PySide2 import QtCore
from logging import getLogger, Logger
from typing import Mapping, Any, Type, Sequence, Optional, Iterable

from qudi.core.connector import Connector
from qudi.core.modulemanager import ModuleManager
from qudi.util.models import DictTableModel


class ModuleScript(QtCore.QObject):
    """
    """
    # Declare all module connectors used in this script here

    sigFinished = QtCore.Signal(object)

    def __new__(cls, *args, **kwargs):
        obj = super().__new__(cls, *args, **kwargs)
        # Create instance copies of all Connector meta objects for this ModuleScript (sub-)class
        connectors = dict()
        for attr_name in [name for name in dir(obj) if not name.startswith('__')]:
            attr = getattr(obj, attr_name)
            if isinstance(attr, Connector):
                conn_name = attr.name
                if conn_name in connectors:
                    raise ValueError(f'Multiple definitions of Connector with name "{conn_name}"')
                setattr(obj, attr_name, attr.copy())
                connectors[conn_name] = getattr(obj, attr_name)
        setattr(obj, '_named_connectors', connectors)
        print(connectors)
        return obj

    def __init__(self, module_instances: Optional[Mapping[str, Any]] = None,
                 args: Optional[Sequence[Any]] = None, kwargs: Optional[Mapping[str, Any]] = None,
                 parent: Optional[QtCore.QObject] = None):
        super().__init__(parent=parent)

        # Connect module connectors as specified in module_instances
        if module_instances is None:
            module_instances = dict()
        self.__connect_modules(module_instances)

        # cache arguments for script (if given)
        self.args = tuple() if args is None else tuple(args)
        self.kwargs = dict() if kwargs is None else dict(kwargs)

        # script result cache
        self.result = None

    def __connect_modules(self, module_instances: Mapping[str, Any]):
        """ Connect all Connector meta objects of this instance to qudi module instances.

        @param dict module_instances: Connector names (keys) and qudi module instances (values) to
                                      connect
        """
        for conn_name, connector in self._named_connectors.items():
            module = module_instances.get(conn_name, None)
            if module is not None:
                connector.connect(module)
            elif not connector.optional:
                raise RuntimeError(f'Mandatory module connection "{conn_name}" missing for '
                                   f'ModuleScript "{self.__class__.__name__}"')

    @property
    def log(self) -> Logger:
        """ Returns a logger object.
        DO NOT OVERRIDE IN SUBCLASS!

        @return Logger: Logger object for this script class
        """
        return getLogger(f'{self.__module__}.{self.__class__.__name__}')

    def __call__(self, *args, **kwargs) -> Any:
        """ Convenience magic method to run this script like a function
        DO NOT OVERRIDE IN SUBCLASS!

        @param args: Positional arguments passed to run method
        @param kwargs: Keyword arguments passed to run method

        @return object: Result of the script method
        """
        self.cache_arguments(*args, **kwargs)
        self.run()
        return self.result

    @QtCore.Slot()
    def run(self) -> None:
        """ Check run prerequisites and execute _run method with pre-cached arguments.
        DO NOT OVERRIDE IN SUBCLASS!
        """
        self.result = None
        self.log.debug(f'Starting to run ModuleScript "{self.__class__.__name__}" with positional '
                       f'arguments {self.args} and keyword arguments {self.kwargs}.')
        self.result = self._run(*self.args, **self.kwargs)
        self.sigFinished.emit(self.result)

    def _run(self, *args, **kwargs) -> Any:
        """ The actual script to be run. Implement only this method in a subclass.

        @return Any: The result of the script
        """
        raise NotImplementedError(
            f'No _run() method implemented for ModuleScript "{self.__class__.__name__}".'
        )


class ModuleScriptImporter:
    """ Helper class to import ModuleScript sub-classes from locations specified in a qudi config
    dict.
    """

    def __init__(self, script_config: Mapping[str, Any]):
        super().__init__()
        self.module, self.object_name = script_config['module.Class'].rsplit('.', 1)

    def import_script(self, reload: bool = True) -> Type[ModuleScript]:
        mod = importlib.import_module(self.module)
        if reload:
            importlib.reload(mod)
        script = getattr(mod, self.object_name)
        if not issubclass(script, ModuleScript):
            raise TypeError(f'Module script to import must be a subclass of '
                            f'{ModuleScript.__module__}.ModuleScript')
        return script


class ScriptsTableModel(DictTableModel):
    """ Qt compatible table model holding all configured and available ModuleScript QRunnables.
    """
    def __init__(self, script_config: Optional[Mapping[str, dict]] = None):
        super().__init__(headers='Module Scripts')
        if script_config is None:
            script_config = dict()
        for name, config in script_config.items():
            self.register_script(name, config)

    def register_script(self, name: str, config: dict) -> None:
        if name in self:
            raise KeyError(f'Multiple module script with name "{name}" configured.')
        self[name] = ModuleScriptImporter(config).import_script()


class ModuleScriptFactory:
    """ This class is responsible for creating ModuleScript instances with active and connected
    qudi modules.
    """

    def __init__(self, module_manager: ModuleManager, scripts_model: ScriptsTableModel,
                 connector_config: Mapping[str, Mapping[str, str]]):
        super().__init__()
        if not isinstance(module_manager, ModuleManager):
            raise TypeError(f'"module_manager" must be an instance of '
                            f'{ModuleManager.__module__}.ModuleManager')
        if not isinstance(scripts_model, ScriptsTableModel):
            raise TypeError(f'"scripts_model" must be an instance of '
                            f'{ScriptsTableModel.__module__}.ScriptsTableModel')
        self._module_manager = module_manager
        self._scripts_model = scripts_model
        self._connector_config = connector_config

    def _activate_modules(self, module_names: Iterable[str]) -> Mapping[str, Any]:
        """ Activate all qudi modules with their configured names listed in module_names.
        """
        modules = dict()
        for name in module_names:
            self._module_manager.activate_module(name)
            modules[name] = self._module_manager[name].instance
        return modules

    def get_script(self, name: str) -> ModuleScript:
        """ Creates an instance of a ModuleScript sub-class by name, activates all necessary
        modules and connects them to the ModuleScript instance.
        """
        script_cls = self._scripts_model.get(name, None)
        if script_cls is None:
            raise KeyError(f'No module script found by name "{name}"')
        # activate all necessary modules and connect them to the ModuleScript instance created
        module_names = list(self._connector_config[name])
        module_instances = self._activate_modules(module_names)
        return script_cls(module_instances=module_instances)


class ModuleScriptRunner:
    """ This class is responsible for running ModuleScript instances.
    """

    def __init__(self, module_script_factory: ModuleScriptFactory):
        super().__init__()
        if not isinstance(module_script_factory, ModuleScriptFactory):
            raise TypeError(f'"module_script_factory" must be an instance of '
                            f'{ModuleScriptFactory.__module__}.ModuleScriptFactory')
        self._scripts_factory = module_script_factory

    def run_script(self, name: str, /, *args, **kwargs) -> Any:
        script = self._scripts_factory.get_script(name)
        return script(*args, **kwargs)
