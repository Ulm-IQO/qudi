from qtpy import QtWidgets
import os
from qtpy import uic
import logging
import json


class ConfocalStepperLabBookWindow(QtWidgets.QMainWindow):
    """ The settings dialog for ODMR measurements.
    """

    def __init__(self, stepper_logic):
        """
        :param stepper_logic:  (ConfocalStepperLogic)
        """
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_lab_book.ui')

        # Load it
        super(ConfocalStepperLabBookWindow, self).__init__()
        uic.loadUi(ui_file, self)
        self._stepper_logic = stepper_logic

        self.refresh_pushButton.clicked.connect(self.load)
        self.save_pushButton.clicked.connect(self.save)
        self.clear_action.triggered.connect(self.clear)

        self.save_pushButton.setEnabled(False)
        self.errors_plainTextEdit.textChanged.connect(self.text_changed)
        self.reasons_plainTextEdit.textChanged.connect(self.text_changed)
        self.measurment_info_plainTextEdit.textChanged.connect(self.text_changed)

        self.location = None

    def load(self):
        logging.info("Loading data from file")
        location = self._stepper_logic.filepath
        if location is None:
            return
            #this_dir = os.path.dirname(__file__)
            #location = os.path.join(this_dir)
        self.location = os.path.join(location, "labbook.json")
        self.path_label.setText(self.location)
        if os.path.exists(self.location):
            with open(self.location, "r") as file_obj:
                data = json.load(file_obj)
            self.errors_plainTextEdit.setPlainText(data["errors"])
            self.reasons_plainTextEdit.setPlainText(data["reasons"])
            self.measurment_info_plainTextEdit.setPlainText(data["measurment_info"])

    def clear(self):
        self.errors_plainTextEdit.setPlainText("")
        self.reasons_plainTextEdit.setPlainText("")
        self.measurment_info_plainTextEdit.setPlainText("")

    def text_changed(self):
        self.save_pushButton.setEnabled(True)

    def save(self):
        if self.location is None:
            # No refresh was done since the save button. Force the user to
            logging.error("Please refresh.")
            return
        data = {"reasons": self.reasons_plainTextEdit.toPlainText(),
                "errors": self.errors_plainTextEdit.toPlainText(),
                "measurment_info": self.measurment_info_plainTextEdit.toPlainText()
                }
        with open(self.location, "w") as fileobj:
            json.dump(data, fileobj, sort_keys=True, indent=2)
        self.save_pushButton.setEnabled(False)

    def focusInEvent(self, event):
        logging.info("Hallo focusInEvent")
        self.go()

        pass

    def focusOutEvent(self, event):
        logging.info("Hallo focusOutEvent")

        pass
