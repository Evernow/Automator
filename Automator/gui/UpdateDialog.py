from PyQt6 import QtCore, QtWidgets
import os
import sys

Started = 0 # To avoid duplicate exits
class UpdateDialog():
    def setupUi(self, Dialog: QtWidgets.QDialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(500, 100)
        self.label = QtWidgets.QLabel(Dialog)
        self.label.setGeometry(QtCore.QRect(40, 20, 411, 31))
        self.label.setObjectName("label")
        self.pushButton = QtWidgets.QPushButton(Dialog)
        self.pushButton.setGeometry(QtCore.QRect(210, 60, 75, 23))
        self.pushButton.setObjectName("pushButton")
        
        self.pushButton.clicked.connect(lambda :self.PressedOk())
        

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)
        
        
        
        
    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Outdated"))
        self.label.setText(_translate("Dialog", "This version of Automator is out of date. Click Ok to download latest version."))
        self.pushButton.setText(_translate("Dialog", "Ok"))
        
        
    def PressedOk(self):
        global Started
        if (Started == 0):
            Started = 1
            os.startfile('https://github.com/24HourSupport/Automator/releases/latest/download/24HS-Automator.exe')
            QtCore.QCoreApplication.quit()
            sys.exit()
    
        