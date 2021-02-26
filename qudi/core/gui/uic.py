# -*- coding: utf-8 -*-

"""
This file contains a custom .ui file loader since the current (v5.14.1) Pyside2 implementation or
qtpy implementation do not fully allow promotion to a custom widget if the custom widget is not a
direct subclass of the base widget defined in the .ui file. For example you can subclass
QDoubleSpinBox and promote this to your custom class MyDoubleSpinBox but you can not properly
subclass QAbstractSpinBox and promote QDoubleSpinBox (even though QDoubleSpinBox inherits
QAbstractSpinBox).
Funny enough it works if you use Pyside2's ui-to-py-converter and run the generated python code.
This module provides a wrapper to do just that.

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
"""

import os
import re
from importlib.util import spec_from_loader, module_from_spec
from qudi.core.paths import get_artwork_dir, get_appdata_dir

__all__ = ('loadUi',)

__ui_class_pattern = re.compile(r'class (Ui_.*?)\(')
__artwork_path_pattern = re.compile(r'>(.*?/artwork/.*?)</')


def loadUi(file_path, base_widget):
    """ Compiles a given .ui-file at <file_path> into python code. This code will be executed and
    the generated class will be used to initialize the widget given in <base_widget>.

    WARNING: base_widget must be of the same class as the top-level widget in the .ui file.
             Compatible subclasses of the top-level widget in the .ui file will also work.

    @param str file_path: The full path to the .ui-file to load
    @param object base_widget: Instance of the base widget represented by the .ui-file
    """
    # This step is a workaround because Qt Designer will only specify relative paths which is very
    # error prone if the user changes the cwd (e.g. os.chdir)
    file_path = _convert_ui_to_absolute_paths(file_path)

    # Compile .ui-file into python code
    compiled = os.popen('pyside2-uic "{0}"'.format(file_path)).read()
    # Find class name
    match = __ui_class_pattern.search(compiled)
    if match is None:
        raise Exception('Failed to match regexp for finding class name in generated python code.')
    class_name = match.groups()[0]
    # Workaround (again) because pyside2-uic forgot to include objects from PySide2 that can be
    # used by Qt Designer. So we inject import statements here just before the class declaration.
    insert = match.start()
    compiled = compiled[:insert] + 'from PySide2.QtCore import QLocale\n\n' + compiled[insert:]

    # Execute python code in order to obtain a module object from it
    spec = spec_from_loader('ui_module', loader=None)
    ui_module = module_from_spec(spec)
    exec(compiled, ui_module.__dict__)

    loader = getattr(ui_module, class_name, None)()
    if loader is None:
        raise Exception('Unable to locate generated Ui_... class')
    loader.setupUi(base_widget)
    # Merge namespaces manually since this is not done by setupUi.
    to_merge = vars(loader)
    ignore = set(to_merge).intersection(set(base_widget.__dict__))  # Avoid namespace conflicts.
    for key in ignore:
        del to_merge[key]
    base_widget.__dict__.update(to_merge)


def _convert_ui_to_absolute_paths(file_path):
    """ Converts the .ui file in order to change all relative path declarations containing the
    keyword "/artwork/" into absolute paths pointing to the qudi artwork data directory.
    Creates a temporary file "converted.ui" in the qudi appdata directory.
    The original .ui file will remain untouched.

    @param str file_path: The path to the .ui file to change
    @return str: The file path of the (converted) .ui file to use
    """
    path_prefix = get_artwork_dir()
    with open(file_path, 'r') as file:
        ui_content = file.read()
    chunks = __artwork_path_pattern.split(ui_content)
    # Iterate over odd indices. Remember if changes were needed
    has_changed = False
    for ii in range(1, len(chunks), 2):
        path_suffix = chunks[ii].split('/artwork/', 1)[-1]
        chunks[ii] = '>{0}</'.format(os.path.join(path_prefix, path_suffix).replace('\\', '/'))
        has_changed = True
    # Join into single string and write as new .ui file if something has changed
    if has_changed:
        ui_content = ''.join(chunks)
        file_path = os.path.join(get_appdata_dir(), 'converted.ui')
        with open(file_path, 'w') as file:
            file.write(ui_content)
    return file_path
