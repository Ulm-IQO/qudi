
from qtpy import QtCore

def delay(delay_sec = 1):
    dieTime = QtCore.QTime.currentTime().addSecs(delay_sec)
    while (QtCore.QTime.currentTime() < dieTime):
        QtCore.QCoreApplication.processEvents(QtCore.QEventLoop.AllEvents, 100)
