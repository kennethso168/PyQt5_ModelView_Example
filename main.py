from enum import IntEnum, unique
from pathlib import Path
import sys
from typing import Any
from main_ui import Ui_MainWindow

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt

AVAILABLE_ITEMS = ('Apple', 'Orange', 'Banana', 'Grapes', 'Strawberry', 'Mango', 'Watermelon', 'Plum')

class PrefStore():
    """
    An example repository of data, implemented where values are simply stored as lines in a file.
    """
    @unique
    class Keys(IntEnum):
        """
        Keys of of the preference, which corresponds to the line in file.
        """
        OPTION1 = 0
        OPTION2 = 1
        LINE1 = 2
        LINE2 = 3
        ENABLED_ITEMS = 4

    def __init__(self):
        pass

    def write_defaults(self):
        """
        Write a default pref file.
        """
        with open("pref.txt", mode='w', encoding="utf8") as f:
            f.write("True\n")
            f.write("False\n")
            f.write("Hello World\n")
            f.write("Bye\n")
            f.write("Apple,Orange,Banana\n")

    def get_pref(self, key: int) -> Any:
        """
        Get a preference. If a preference file doesn't exist, a default one is written and loaded.

        This is intended to be a simple example so no extensive checking of the values stored in files
        
        :param key: Key of the preference
        :returns: The preference in the appropriate type
        :raises KeyError: When the key is invalid
        """
        if not Path("pref.txt").exists():
            self.write_defaults()
        with open("pref.txt", mode='r', encoding="utf8") as f:
            lines = f.readlines() # Note that the lines with contain '\n' which needs to be stripped
            if key in (self.Keys.OPTION1, self.Keys.OPTION2):
                line = lines[key].strip()
                return line == 'True' # Conversion of the strings 'True' and 'False' to boolean
            elif key in (self.Keys.ENABLED_ITEMS,):
                line = lines[key].strip()
                return line.split(",") # Conversion of a comma-separated list
            elif key in (self.Keys.LINE1, self.Keys.LINE2):
                return lines[key].strip() # Return the key as is
            else:
                raise KeyError(f"Invalid Key {key}")

    """
    Set a preference.

    This is intended to be a simple example so no type checking or key checking is done
    
    :param key: Key of the preference
    :param value: The value
    """
    def set_pref(self, key: int, value: Any):
        lines = None
        with open("pref.txt", mode='r', encoding="utf8") as f:
            lines = f.readlines()
        if lines is not None:
            if key in (self.Keys.ENABLED_ITEMS,):
                lines[key] = ','.join(value) + '\n'
            else:
                lines[key] = str(value) + '\n'
            with open("pref.txt", mode='w', encoding='utf8') as f:
                f.writelines(lines)

class SimplePrefModel(QtCore.QAbstractListModel):
    """
    The Qt Model that handles the data for views other than the QListViews.

    This shows a way to use Qt Models for simple views (with QDataWidgetMapper and final data as "rows" in the QAbstractListModel)
    Also the views should not handle the data store directly. This class adapts the data from data store for viewing
    and also provides methods for altering the data.
    """
    @unique
    class Items(IntEnum):
        OPTION1 = PrefStore.Keys.OPTION1
        OPTION2 = PrefStore.Keys.OPTION2
        LINE1 = PrefStore.Keys.LINE1
        LINE2 = PrefStore.Keys.LINE2
        ENABLED_ITEMS = PrefStore.Keys.ENABLED_ITEMS

    def __init__(self):
        super().__init__()
        self._pref_store = PrefStore()

    def rowCount(self, _) -> int:
        """
        Return number of rows in the model.

        This is one of the methods ncessary to be overriden.
        """
        return max(self.Items)+1
    
    def data(self, index: QtCore.QModelIndex, role: int):
        """
        Get data from the model.

        This is one of the methods ncessary to be overriden.
        By observation, if mapped directly to a property of widget, the role Qt.EditRole is 
        passed whenever data is requested
        """
        if role == Qt.EditRole:
            return self._pref_store.get_pref(index.row())

    def setData(self, index: QtCore.QModelIndex, value: Any, role: int = ...) -> bool:
        """
        Set a data from the model.

        This is one of the methods ncessary to be overriden if data of the model will be changed by the view
        """
        print(index.row(), index.column(), value, role)
        if role == Qt.EditRole:
            if not self.hasIndex(index.row(), index.column(), index.parent()):
                return False
            # Note that this function is called even outside of changes made by user
            # So added this to guard against unnecessary calls to setting value in data store
            if value != self._pref_store.get_pref(index.row()):
                self._pref_store.set_pref(index.row(),value)
                # Notify data at top-right and bottom-left index is changed
                # Note that as a single value is changed in this method
                # top-right and bottom-left will be the same
                self.dataChanged.emit(index, index, [role])
            return True
        return super().setData(index, value, role)

class EnabledItemsModel(QtCore.QAbstractListModel):
    """
    The Qt Model that handles the data the lvEnabledItems QListView.

    The views should not handle the data store directly. This class adapts the data from data store for viewing
    and also provides methods for altering the data.
    """
    def __init__(self, parent_model: SimplePrefModel):
        super().__init__()
        self._parent_model = parent_model
        #self._parent_model.dataChanged.connect()

    def _get_list(self):
        index = self._parent_model.index(SimplePrefModel.Items.ENABLED_ITEMS)
        return self._parent_model.data(index, Qt.EditRole)

    def _set_list(self, my_list: list):
        index = self._parent_model.index(SimplePrefModel.Items.ENABLED_ITEMS)
        return self._parent_model.setData(index, my_list, Qt.EditRole)

    def data(self, index, role):
        if role == Qt.DisplayRole:
            return self._get_list()[index.row()]

    def rowCount(self, parent: QtCore.QModelIndex = ...) -> int:
        return len(self._get_list())

    def swap(self, row1: int, row2: int):
        """
        Swap two rows in this model
        """
        items = self._get_list()
        items[row1], items[row2] = items[row2], items[row1]
        self._set_list(items)
        # Notify that the data in the two rows are changed
        # Note that to get a QModelIndex, you call the index method of the model
        first_index = self.index(row1)
        second_index = self.index(row2)
        self.dataChanged.emit(first_index, first_index)
        self.dataChanged.emit(second_index, second_index)

    def add(self, item):
        """
        Add a row to this model
        """
        self.layoutAboutToBeChanged.emit()
        items = self._get_list()
        items.append(item)
        self._set_list(items)
        # Note that layoutChanged is needed as the number of items in the model become different
        self.layoutChanged.emit()

    def remove(self, item):
        """
        Remove a row to this model
        """
        self.layoutAboutToBeChanged.emit()
        items = self._get_list()
        items.remove(item)
        self._set_list(items)
        self.layoutChanged.emit()

class DisabledItemsModel(QtCore.QAbstractListModel):
    """
    The Qt Model that handles the data the lvDisabledItems QListView.
    """
    def __init__(self, parent_model: SimplePrefModel):
        super().__init__()
        self._parent_model = parent_model

    def _get_disabled_items(self):
        index = self._parent_model.index(SimplePrefModel.Items.ENABLED_ITEMS)
        enabled_items = self._parent_model.data(index, Qt.EditRole)
        # All available items that are not enabled are disabled
        return list(set(AVAILABLE_ITEMS) - set(enabled_items))

    def data(self, index, role):
        if role == Qt.DisplayRole:
            return self._get_disabled_items()[index.row()]

    def rowCount(self, parent: QtCore.QModelIndex = ...) -> int:
        return len(self._get_disabled_items())

class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)
        self.setupUi(self)

        # Map SimplePrefModel to relevant widgets using a QDataWidgetMapper

        self.simple_pref_mapper = QtWidgets.QDataWidgetMapper()
        # By default, QDataWidgetMapper map each widget to a column
        # This changes the mapping to rows
        self.simple_pref_mapper.setOrientation(Qt.Vertical)
        self.simple_pref_model = SimplePrefModel()
        self.simple_pref_mapper.setModel(self.simple_pref_model)
        self.simple_pref_mapper.addMapping(self.cbOption1, SimplePrefModel.Items.OPTION1)
        self.simple_pref_mapper.addMapping(self.cbOption2, SimplePrefModel.Items.OPTION2)
        self.simple_pref_mapper.addMapping(self.lineEdit1, SimplePrefModel.Items.LINE1)
        self.simple_pref_mapper.addMapping(self.lineEdit2, SimplePrefModel.Items.LINE2)
        # By default, the AutoSubmit Policy submits when widgets lose focus
        # This is a sensible default for EditTexts but not the expected behaviour for checkboxes
        # Therefore, change the policy to ManualSubmit and manually connect the signals from the widgets
        # to submitting changes to the mapper
        self.simple_pref_mapper.setSubmitPolicy(QtWidgets.QDataWidgetMapper.ManualSubmit)
        self.cbOption1.stateChanged.connect(self.simple_pref_mapper.submit)
        self.cbOption2.stateChanged.connect(self.simple_pref_mapper.submit)
        self.lineEdit1.editingFinished.connect(self.simple_pref_mapper.submit)
        self.lineEdit2.editingFinished.connect(self.simple_pref_mapper.submit)
        # Set the index of the mapper to the first column (so rows of the first column will be shown)
        # QDataWidgetMapper was probably designed for showing a single record into a form of normal widgets
        # However, our model always only have one record, so just set it to the first one
        self.simple_pref_mapper.toFirst()

        self.enabled_items_model = EnabledItemsModel(self.simple_pref_model)
        self.lvEnabled.setModel(self.enabled_items_model)
        self.btnMoveItemUp.clicked.connect(self.moveUp)
        self.btnMoveItemDown.clicked.connect(self.moveDown)

        self.disabled_items_model = DisabledItemsModel(self.simple_pref_model)
        self.lvDisabled.setModel(self.disabled_items_model)
        self.btnMoveItemLeft.clicked.connect(self.enable)
        self.btnMoveItemRight.clicked.connect(self.disable)

    def moveUp(self, _):
        '''
        Called when the move-up button is clicked
        '''
        indexes = self.lvEnabled.selectedIndexes()
        # Only perform action when at least one row is selected
        # A empty list is falsy
        if indexes:
            # We only get one index here as the list is single-selection
            index = indexes[0]
            row = index.row()
            if row > 0:
                self.enabled_items_model.swap(row, row-1)
                # Set selection to the new position of the moved-up item
                # So that the same item can be moved repeatedly
                self.lvEnabled.setCurrentIndex(self.enabled_items_model.index(row-1))
    
    def moveDown(self, _):
        '''
        Called when the move-down button is clicked
        '''
        indexes = self.lvEnabled.selectedIndexes()
        if indexes:
            index = indexes[0]
            row = index.row()
            if 1 + row < self.enabled_items_model.rowCount():
                self.enabled_items_model.swap(row, row+1)
                self.lvEnabled.setCurrentIndex(self.enabled_items_model.index(row+1))

    def enable(self, _):
        '''
        Called when the move-left button is clicked
        '''
        indexes = self.lvDisabled.selectedIndexes()
        if indexes:
            index = indexes[0]
            target = self.disabled_items_model.data(index, Qt.DisplayRole)
            self.enabled_items_model.add(target)
            # Refresh the DisabledItemsModel
            self.disabled_items_model.layoutChanged.emit()
            # Clear the selection of the disabled items (as the selected items has already been moved away)
            self.lvDisabled.clearSelection()

    def disable(self, _):
        '''
        Called when the move-right button is clicked
        '''
        indexes = self.lvEnabled.selectedIndexes()
        if indexes:
            index = indexes[0]
            target = self.enabled_items_model.data(index, Qt.DisplayRole)
            self.enabled_items_model.remove(target)
            self.disabled_items_model.layoutChanged.emit()
            self.lvEnabled.clearSelection()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec_()