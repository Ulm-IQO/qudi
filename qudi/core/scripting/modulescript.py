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

__all__ = ['import_module_script', 'ModuleScript', 'ModuleScriptsTableModel', 'ModuleScriptFactory',
           'ModuleScriptRunner']

import importlib
from uuid import uuid4
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

    sigFinished = QtCore.Signal(object, str, bool)  # result, ID, success

    def __init__(self, module_instances: Optional[Mapping[str, Any]] = None,
                 parent: Optional[QtCore.QObject] = None):
        super().__init__(parent=parent)

        # Connect module connectors as specified in module_instances
        if module_instances is None:
            module_instances = dict()
        self.__connect_modules(module_instances)

        # Create unique ID string
        self.__id = str(uuid4())

        # script arguments and result cache
        self.result = None
        self.args = tuple()
        self.kwargs = dict()

        # Status flags
        self.success = False
        self.is_running = False

    def __connect_modules(self, module_instances: Mapping[str, Any]):
        """ Connect all Connector meta objects of this instance to qudi module instances.

        @param dict module_instances: Connector names (keys) and qudi module instances (values) to
                                      connect
        """
        used_connector_names = set()
        for attr_name in [name for name in dir(self) if not name.startswith('__')]:
            attr = getattr(self, attr_name)
            if isinstance(attr, Connector):
                conn_name = attr.name
                if conn_name in used_connector_names:
                    raise KeyError(f'Multiple definitions of Connector with name "{conn_name}"')
                used_connector_names.add(conn_name)
                connector = attr.copy()
                setattr(self, attr_name, connector)
                module = module_instances.get(conn_name, None)
                if module is not None:
                    connector.connect(module)
                elif not connector.optional:
                    raise RuntimeError(f'Mandatory module connection "{conn_name}" missing for '
                                       f'ModuleScript "{self.__class__.__name__}"')

    @property
    def id(self):
        """ Read-only unique id (uuid4) of this script instance.

        @return str: ID of this script instance
        """
        return self.__id

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
        self.args = args
        self.kwargs = kwargs
        self.run()
        return self.result

    @QtCore.Slot()
    def run(self) -> None:
        """ Check run prerequisites and execute _run method with pre-cached arguments.
        DO NOT OVERRIDE IN SUBCLASS!
        """
        self.result = None
        self.success = False
        self.is_running = True
        self.log.debug(f'Starting to run ModuleScript "{self.__class__.__name__}" with positional '
                       f'arguments {self.args} and keyword arguments {self.kwargs}.')
        # Emit finished signal even if script execution fails. Check success flag.
        try:
            self.result = self._run(*self.args, **self.kwargs)
            self.success = True
        finally:
            self.is_running = False
            self.sigFinished.emit(self.result, self.id, self.success)

    def _run(self, *args, **kwargs) -> Any:
        """ The actual script to be run. Implement only this method in a subclass.

        @return Any: The result of the script
        """
        raise NotImplementedError(
            f'No _run() method implemented for ModuleScript "{self.__class__.__name__}".'
        )


def import_module_script(module: str, cls: str,
                         reload: Optional[bool] = True) -> Type[ModuleScript]:
    """ Helper function to import ModuleScript sub-classes by name from a given module.
    Reloads the module to import from by default.
    """
    mod = importlib.import_module(module)
    if reload:
        importlib.reload(mod)
    script = getattr(mod, cls)
    if not issubclass(script, ModuleScript):
        raise TypeError(f'Module script to import must be a subclass of {__name__}.ModuleScript')
    return script


class ModuleScriptsTableModel(DictTableModel):
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
        module, cls = config['module.Class'].rsplit('.', 1)
        self[name] = import_module_script(module, cls, reload=True)


class ModuleScriptFactory:
    """ This class is responsible for creating ModuleScript instances with active and connected
    qudi modules.
    """

    def __init__(self, module_manager: ModuleManager,
                 module_scripts: Mapping[str, Type[ModuleScript]],
                 connector_configs: Mapping[str, Mapping[str, str]]):
        super().__init__()
        if not isinstance(module_manager, ModuleManager):
            raise TypeError(f'"module_manager" must be an instance of '
                            f'{ModuleManager.__module__}.ModuleManager')
        self._module_manager = module_manager
        self._module_scripts = module_scripts
        self._connector_configs = connector_configs

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
        script_cls = self._module_scripts.get(name, None)
        if script_cls is None:
            raise KeyError(f'No module script found by name "{name}"')
        # activate all necessary modules and connect them to the ModuleScript instance created
        module_names = list(self._connector_configs[name].values())
        module_instances = self._activate_modules(module_names)
        return script_cls(module_instances=module_instances)


class ModuleScriptRunner(QtCore.QObject):
    """ This class is responsible for running ModuleScript instances.
    """

    def __init__(self, module_manager: ModuleManager,
                 module_scripts: Mapping[str, Type[ModuleScript]],
                 connector_configs: Mapping[str, Mapping[str, str]],
                 parent: Optional[QtCore.QObject] = None):
        super().__init__(parent=parent)
        self._scripts_factory = ModuleScriptFactory(module_manager=module_manager,
                                                    module_scripts=module_scripts,
                                                    connector_configs=connector_configs)

    def run_script(self, name: str, /, *args, **kwargs) -> Any:
        script = self._scripts_factory.get_script(name)
        script.setParent(self)
        return script(*args, **kwargs)
