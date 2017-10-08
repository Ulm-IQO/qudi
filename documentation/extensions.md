# Extensions {#extensions}

With a Qudi extension it is possible to add custom gui, logic and hardware modules as well as interfaces.

A Qudi extension is a python package with gui, logic and hardware subpackages. All modules in those subpackages are combined in qudi's gui, logic and hardware namespaces, respectively.

Example:

Folder structure:

* `my_qudi_extension`
    * `hardware`
        * `my_hardware_module.py`

After addition of the extension to qudi the module `my_hardware_module` will be available in the `hardware` namespace, i.e. as `hardware.my_hardware_module`. You can import it by

```
import hardware.my_hardware_module
```

Please note:

* The shared gui, logic and hardware namespaces mean that if a module with the same name is defined twice, only the one that is found first, will be loaded. For the search order please see below.
* You are not allowed to use `__init__.py` files within the qudi extension. This is a requirement posed by the implicit namespaces introduced in python 3.3 which we use for extensions.

## Adding extensions to Qudi

There are two ways to add an extension to Qudi:

1. In the configuration file
2. `PYTHONPATH` environment variable

In a configuration file an extension can be added by defining its directory to the `extensions` key in the `global` section.

```
global:
    extensions:
        - "path_to_extension_1"
        - "path_to_extension_2"
```

The path to the extension can be absolute or relative to the location of the configuration file. If the directory cannot be found an error is thrown and it is ignored.


An extension can also be added by defining its path to the `PYTHONPATH` environment variable. One way to do this is to start Qudi by `PYTHONPATH="path_to_extension_1" python qudi/start.py`

The search order is

1. Qudi directory (gui, logic, hardware)
2. Paths defined in the configuration file in the specified order 
3. Paths defined in PYTHONPATH in the specified order
