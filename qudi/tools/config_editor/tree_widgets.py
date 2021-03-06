# -*- coding: utf-8 -*-
"""

"""

from PySide2 import QtCore, QtGui, QtWidgets
from qudi.util.mutex import Mutex


class AvailableModulesTreeWidget(QtWidgets.QTreeWidget):
    """
    """
    def __init__(self, *args, available_modules, **kwargs):
        super().__init__(*args, **kwargs)
        self.setColumnCount(3)
        self.setHeaderLabels(('Base', 'Module', 'Class'))
        self.setDragEnabled(True)
        top_level_items = dict()
        for disp_base in ('GUI', 'Logic', 'Hardware'):
            item = QtWidgets.QTreeWidgetItem()
            item.setFlags(QtCore.Qt.ItemIsEnabled)
            item.setText(0, disp_base)
            self.addTopLevelItem(item)
            item.setExpanded(True)
            top_level_items[disp_base.lower()] = item
        for module_class_name in available_modules:
            module_name, class_name = module_class_name.rsplit('.', 1)
            base, module_name = module_name.split('.', 1)
            item = QtWidgets.QTreeWidgetItem()
            item.setText(1, module_name)
            item.setText(2, class_name)
            item.setFlags(
                QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsSelectable)
            top_level_items[base].addChild(item)
        for i in range(self.columnCount()):
            self.resizeColumnToContents(i)

    def mimeData(self, items):
        """ Add text to mime data. This is the quick (but not necessarily dirty) way.
        """
        texts = tuple(f'{it.parent().text(0).lower()}.{it.text(1)}.{it.text(2)}' for it in items)
        mime = super().mimeData(items)
        mime.setText(';'.join(texts))
        return mime


class SelectedModulesTreeWidget(QtWidgets.QTreeWidget):
    """
    """
    sigSetValidState = QtCore.Signal(bool)

    def __init__(self, *args, selected_modules=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.setColumnCount(3)
        self.setHeaderLabels(('Base', 'Name', 'Module'))
        self.setAcceptDrops(True)
        self.setSelectionMode(self.ExtendedSelection)
        self.setDropIndicatorShown(False)

        self.top_level_items = dict()
        self.used_names = set()
        self.__currently_edited_name = ''
        for disp_base in ('GUI', 'Logic', 'Hardware', 'Remote'):
            item = QtWidgets.QTreeWidgetItem()
            item.setFlags(QtCore.Qt.ItemIsEnabled)
            item.setText(0, disp_base)
            self.addTopLevelItem(item)
            item.setExpanded(True)
            self.top_level_items[disp_base.lower()] = item
        self._standard_foreground = item.foreground(0)
        self._error_foreground = QtGui.QBrush(QtCore.Qt.red)
        self.setEditTriggers(self.EditTrigger.NoEditTriggers)

        if selected_modules is not None:
            for name, module in selected_modules.items():
                base, module = module.split('.', 1)
                item = QtWidgets.QTreeWidgetItem()
                item.setText(1, name)
                item.setText(2, module)
                item.setFlags(
                    QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable)
                self.top_level_items[base].addChild(item)
                self.used_names.add(name)

        self.itemDoubleClicked.connect(self.edit_column)
        self.itemChanged.connect(self.check_custom_name)

    def dropEvent(self, event):
        if isinstance(event.source(), AvailableModulesTreeWidget):
            full_text = event.mimeData().text()
            for text in full_text.split(';'):
                base, module = text.split('.', 1)
                item = QtWidgets.QTreeWidgetItem()
                item.setText(1, 'unique name')
                item.setForeground(1, self._error_foreground)
                item.setText(2, module)
                item.setFlags(
                    QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable)
                self.top_level_items[base].addChild(item)
                event.accept()
            if text:
                for i in range(self.columnCount()):
                    self.resizeColumnToContents(i)
                self.sigSetValidState.emit(False)
        else:
            event.ignore()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Delete:
            for item in self.selectedItems():
                self.used_names.discard(item.text(1).strip())
                item.parent().removeChild(item)
        else:
            return super().keyPressEvent(event)

    def edit_column(self, item, column):
        if item and column == 1 and item.parent() is not None:
            self.__currently_edited_name = item.text(1).strip()
            self.editItem(item, column)

    def add_remote_module(self):
        item = QtWidgets.QTreeWidgetItem()
        item.setText(1, 'unique name')
        item.setForeground(1, self._error_foreground)
        item.setText(2, 'REMOTE')
        item.setFlags(
            QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable)
        self.top_level_items['remote'].addChild(item)

    def check_custom_name(self, item, column):
        if column == 1 and item.parent() is not None:
            if self.__currently_edited_name:
                if item.foreground(1).color() != QtCore.Qt.red:
                    self.used_names.remove(self.__currently_edited_name)
                self.__currently_edited_name = ''
            text = item.text(1).strip()
            is_valid = False
            if text:
                self.blockSignals(True)
                if text in self.used_names:
                    item.setForeground(1, self._error_foreground)
                else:
                    self.used_names.add(text)
                    item.setForeground(1, self._standard_foreground)
                    is_valid = True
                self.blockSignals(False)
            self.sigSetValidState.emit(is_valid)
            self.resizeColumnToContents(1)

    def get_selected_modules(self):
        selected_modules = dict()
        for disp_base, top_item in self.top_level_items.items():
            base = disp_base.lower()
            for child_index in range(top_item.childCount()):
                child = top_item.child(child_index)
                name = child.text(1)
                module = '{0}.{1}'.format(base, child.text(2))
                selected_modules[name] = module
        return selected_modules

    @property
    def has_invalid_module_names(self):
        number_of_modules = 0
        for top_item in self.top_level_items.values():
            number_of_modules += top_item.childCount()
        return len(self.used_names) != number_of_modules


class ConfigModulesTreeWidget(QtWidgets.QTreeWidget):
    """
    """
    def __init__(self, *args, selected_modules=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._lock = Mutex()
        self.setColumnCount(3)
        self.setHeaderLabels(('Base', 'Name', 'Module'))
        self.setSelectionMode(self.SingleSelection)
        self.top_level_items = dict()
        for disp_base in ('GUI', 'Logic', 'Hardware'):
            item = QtWidgets.QTreeWidgetItem()
            item.setFlags(QtCore.Qt.ItemIsEnabled)
            item.setText(0, disp_base)
            self.addTopLevelItem(item)
            self.top_level_items[disp_base.lower()] = item
        if selected_modules is not None:
            self.set_modules(selected_modules)

    def set_modules(self, modules):
        with self._lock:
            # Clear all modules
            for top_item in self.top_level_items.values():
                for index in range(top_item.childCount()):
                    top_item.removeChild(top_item.child(0))
                top_item.setExpanded(True)
            # Add new modules
            for cfg_name, module in modules.items():
                base, module_name = module.split('.', 1)
                item = QtWidgets.QTreeWidgetItem()
                item.setText(1, cfg_name)
                item.setText(2, module_name)
                item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                self.top_level_items[base].addChild(item)
            # Resize columns
            for i in range(self.columnCount()):
                self.resizeColumnToContents(i)

    def get_modules(self):
        with self._lock:
            modules = dict()
            for disp_base, top_item in self.top_level_items.items():
                base = disp_base.lower()
                for child_index in range(top_item.childCount()):
                    child = top_item.child(child_index)
                    name = child.text(1)
                    module_name = '{0}.{1}'.format(base, child.text(2))
                    modules[name] = module_name
            return modules
