# -*- coding: utf-8 -*-
"""

"""

__all__ = ('ModuleFinder', 'QudiModules')

import os
import sys
import importlib
import inspect
import logging
from qudi.util.paths import get_main_dir
from qudi.core.module import Base, LogicBase, GuiBase


log = logging.getLogger(__package__)


class ModuleFinder:
    """
    """
    @staticmethod
    def _remove_search_paths_from_path(module_search_paths):
        for path in module_search_paths:
            try:
                sys.path.remove(path)
            except ValueError:
                pass

    @staticmethod
    def _add_search_paths_to_path(module_search_paths):
        for path in module_search_paths:
            try:
                sys.path.remove(path)
            except ValueError:
                pass
        try:
            insert_index = sys.path.index(get_main_dir())
        except ValueError:
            insert_index = 0
        for path in reversed(module_search_paths):
            sys.path.insert(insert_index, path)

    @staticmethod
    def is_qudi_module(obj):
        base_classes = (Base, LogicBase, GuiBase)
        return inspect.isclass(obj) and not inspect.isabstract(obj) and issubclass(obj, Base) and \
            obj not in base_classes

    @classmethod
    def get_qudi_classes_in_module(cls, module):
        return dict(m for m in inspect.getmembers(module, cls.is_qudi_module) if
                    m[1].__module__ == module.__name__)

    @classmethod
    def get_qudi_modules(cls, search_paths):
        if isinstance(search_paths, str):
            search_paths = [search_paths]

        invalid_paths = {path for path in search_paths if not os.path.isdir(path)}
        if invalid_paths:
            log.error(f'Non-existent paths found to search in. Ignoring: {invalid_paths}.')
        search_paths = [path for path in search_paths if path not in invalid_paths]

        cls._add_search_paths_to_path(search_paths)
        try:
            found_modules = dict()
            for path in search_paths:
                # Find qudi modules
                for base in ('gui', 'logic', 'hardware'):
                    for root, _, files in os.walk(os.path.join(path, base)):
                        for file in (f for f in files if f.endswith('.py')):
                            module_name_comp = os.path.normpath(root).split(os.sep)
                            index = module_name_comp.index(base)
                            module_name_comp.append(file[:-3])
                            module_name = '.'.join(module_name_comp[index:])
                            try:
                                module = importlib.import_module(module_name)
                            except:
                                log.exception(f'Error during import of module "{module_name}".')
                                continue
                            classes = cls.get_qudi_classes_in_module(module)
                            found_modules.update(
                                {f'{module_name}.{c_name}': c for c_name, c in classes.items()}
                            )
        finally:
            cls._remove_search_paths_from_path(search_paths)
        return found_modules


class QudiModules:
    """
    """

    def __init__(self, additional_search_paths=None):
        # Import all modules available in qudi installation directory and additional search paths
        module_search_paths = [get_main_dir()]
        if additional_search_paths:
            module_search_paths.extend(module_search_paths)

        # import all qudi module classes from search paths
        self._qudi_module_classes = ModuleFinder.get_qudi_modules(module_search_paths)
        # Collect all connectors for all modules
        self._module_connectors = {
            mod: tuple(cls._meta['connectors'].values()) for mod, cls in
            self._qudi_module_classes.items()
        }
        # Get for each connector in each module compatible modules to connect to
        self._module_connectors_compatible_modules = {
            mod: self._modules_for_connectors(mod) for mod in self._qudi_module_classes
        }
        # Get all ConfigOptions for all modules
        self._module_config_options = {
            mod: tuple(cls._meta['config_options'].values()) for mod, cls in
            self._qudi_module_classes.items()
        }

    def _modules_for_connectors(self, module):
        return {
            conn.name: self._modules_for_connector(conn) for conn in self._module_connectors[module]
        }

    def _modules_for_connector(self, connector):
        interface = connector.interface
        bases = {
            mod: {c.__name__ for c in cls.mro()} for mod, cls in self._qudi_module_classes.items()
        }
        return tuple(mod for mod, base_names in bases.items() if interface in base_names)

    @property
    def available_modules(self):
        return tuple(self._qudi_module_classes)

    def module_connectors(self, module):
        return self._module_connectors[module]

    def module_connector_targets(self, module):
        return self._module_connectors_compatible_modules[module].copy()

    def module_config_options(self, module):
        return self._module_config_options[module]
