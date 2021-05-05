# -*- coding: utf-8 -*-
"""

"""

__all__ = ('AvailableModulesTreeWidget', 'SelectedModulesTreeWidget', 'ConfigModulesTreeWidget')

from PySide2 import QtCore, QtGui, QtWidgets


class AvailableModulesTreeWidget(QtWidgets.QTreeWidget):
    """
    """
    def __init__(self, *args, modules=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.setColumnCount(2)
        self.setHeaderLabels(('Base', 'module.Class'))
        self.setSelectionMode(self.ExtendedSelection)
        self.setEditTriggers(self.EditTrigger.NoEditTriggers)
        self.setDragEnabled(True)

        self.top_level_items = dict()
        self.clear_modules()
        if modules is not None:
            self.set_modules(modules)

    def set_modules(self, modules):
        # Clear all modules
        self.clear_modules()
        # Add new modules
        for module in modules:
            self.add_module(module, False)
        # Resize columns
        self.resize_columns_to_content()

    def add_module(self, module, resize=True):
        base, module_class = module.split('.', 1)
        item = QtWidgets.QTreeWidgetItem()
        item.setText(1, module_class)
        item.setFlags(
            QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDragEnabled
        )
        self.top_level_items[base].addChild(item)
        if resize:
            self.resize_columns_to_content()

    def remove_module(self, module, resize=True):
        base, module_class = module.split('.', 1)
        top_level_item = self.top_level_items[base]
        for index in range(top_level_item.childCount()):
            child = top_level_item.child(index)
            if child.text(1) == module_class:
                top_level_item.removeChild(child)
                break
        if resize:
            self.resize_columns_to_content()

    def clear_modules(self):
        self.clear()
        for disp_base in ('GUI', 'Logic', 'Hardware'):
            item = QtWidgets.QTreeWidgetItem()
            item.setFlags(QtCore.Qt.ItemIsEnabled)
            item.setText(0, disp_base)
            self.addTopLevelItem(item)
            item.setExpanded(True)
            self.top_level_items[disp_base.lower()] = item

    def get_modules(self):
        modules = list()
        for base, top_item in self.top_level_items.items():
            items = [top_item.child(index) for index in range(top_item.childCount())]
            modules.extend(f'{base}.{it.text(1)}' for it in items)
        return modules

    def resize_columns_to_content(self):
        for i in range(self.columnCount()):
            self.resizeColumnToContents(i)

    def mimeData(self, items):
        """ Add text to mime data. This is the quick (but not necessarily dirty) way.
        """
        texts = tuple(f'{it.parent().text(0).lower()}.{it.text(1)}' for it in items)
        mime = super().mimeData(items)
        mime.setText(';'.join(texts))
        return mime


class SelectedModulesTreeWidget(AvailableModulesTreeWidget):
    """
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setDragEnabled(False)
        self.setDropIndicatorShown(False)
        self.setAcceptDrops(True)

    def dropEvent(self, event):
        if isinstance(event.source(), AvailableModulesTreeWidget):
            full_text = event.mimeData().text()
            for module in full_text.split(';'):
                self.add_module(module, False)
            self.resize_columns_to_content()
            event.accept()
        else:
            event.ignore()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Delete:
            for item in self.selectedItems():
                if item.parent() is not None:
                    item.parent().removeChild(item)
            event.accept()
        else:
            super().keyPressEvent(event)


class ConfigModulesTreeWidget(QtWidgets.QTreeWidget):
    """
    """

    _error_foreground = QtGui.QBrush(QtCore.Qt.red)

    def __init__(self, *args, named_modules=None, unnamed_modules=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.setColumnCount(3)
        self.setHeaderLabels(('Base', 'Name', 'module.Class'))
        self.setSelectionMode(self.SingleSelection)
        self.setEditTriggers(self.EditTrigger.NoEditTriggers)
        self.top_level_items = dict()
        self.set_modules(named_modules, unnamed_modules)
        self._valid_foreground = next(iter(self.top_level_items.values())).foreground(0)
        self.itemDoubleClicked.connect(self.edit_item_column)

    def set_modules(self, named_modules=None, unnamed_modules=None):
        # Clear all modules
        self.clear_modules()
        # Add new modules
        if named_modules is not None:
            for name, module in named_modules.items():
                self.add_module(module, name, resize=False)
        if unnamed_modules is not None:
            for module in unnamed_modules:
                self.add_module(module, resize=False)
        # Resize columns
        self.resize_columns_to_content()

    def add_module(self, module, name=None, resize=True):
        base, module_class = module.split('.', 1)
        item = QtWidgets.QTreeWidgetItem()
        item.setText(1, '<enter unique name>' if name is None else name)
        item.setText(2, module_class)
        item.setFlags(
            QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable
        )
        self.top_level_items[base].addChild(item)
        if resize:
            self.resize_columns_to_content()

    # def add_remote_module(self):
    #     item = QtWidgets.QTreeWidgetItem()
    #     item.setText(1, 'unique name')
    #     item.setForeground(1, self._error_foreground)
    #     item.setText(2, 'REMOTE')
    #     item.setFlags(
    #         QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable)
    #     self.top_level_items['remote'].addChild(item)

    def remove_module(self, name, resize=True):
        found = False
        for base, top_item in self.top_level_items.items():
            for index in range(top_item.childCount()):
                child = top_item.child(index)
                if child.text(1) == name:
                    top_item.removeChild(child)
                    found = True
                    break
            if found:
                break
        if found and resize:
            self.resize_columns_to_content()

    def clear_modules(self):
        self.clear()
        for disp_base in ('GUI', 'Logic', 'Hardware'):
            item = QtWidgets.QTreeWidgetItem()
            item.setFlags(QtCore.Qt.ItemIsEnabled)
            item.setText(0, disp_base)
            self.addTopLevelItem(item)
            item.setExpanded(True)
            self.top_level_items[disp_base.lower()] = item

    def resize_columns_to_content(self):
        for i in range(self.columnCount()):
            self.resizeColumnToContents(i)

    def get_modules(self):
        named_modules = dict()
        unnamed_modules = list()
        for base, top_item in self.top_level_items.items():
            items = [top_item.child(index) for index in range(top_item.childCount())]
            for it in items:
                name = it.text(1)
                module = f'{base}.{it.text(2)}'
                if not name or name == '<enter unique name>' or name in named_modules:
                    unnamed_modules.append(module)
                else:
                    named_modules[name] = module
        return named_modules, unnamed_modules

    @QtCore.Slot(QtWidgets.QTreeWidgetItem, int)
    def edit_item_column(self, item, column):
        if item and column == 1 and item.parent() is not None:
            self.editItem(item, column)
