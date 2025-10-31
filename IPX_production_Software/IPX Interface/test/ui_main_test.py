# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'initial_designer_file.ui'
##
## Created by: Qt User Interface Compiler version 6.9.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QLineEdit,
    QMainWindow, QMenuBar, QProgressBar, QPushButton,
    QSizePolicy, QStatusBar, QTextEdit, QVBoxLayout,
    QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1114, 855)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.widget = QWidget(self.centralwidget)
        self.widget.setObjectName(u"widget")
        self.widget.setGeometry(QRect(150, 91, 258, 368))
        self.verticalLayout = QVBoxLayout(self.widget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.COMPort_selec = QComboBox(self.widget)
        self.COMPort_selec.addItem("")
        self.COMPort_selec.addItem("")
        self.COMPort_selec.addItem("")
        self.COMPort_selec.addItem("")
        self.COMPort_selec.addItem("")
        self.COMPort_selec.setObjectName(u"COMPort_selec")

        self.verticalLayout.addWidget(self.COMPort_selec)

        self.NUM_Sensor = QLineEdit(self.widget)
        self.NUM_Sensor.setObjectName(u"NUM_Sensor")

        self.verticalLayout.addWidget(self.NUM_Sensor)

        self.Configuration_progres = QProgressBar(self.widget)
        self.Configuration_progres.setObjectName(u"Configuration_progres")
        self.Configuration_progres.setValue(24)

        self.verticalLayout.addWidget(self.Configuration_progres)

        self.Verbose_check_bo = QCheckBox(self.widget)
        self.Verbose_check_bo.setObjectName(u"Verbose_check_bo")

        self.verticalLayout.addWidget(self.Verbose_check_bo)

        self.get_uids_butto = QPushButton(self.widget)
        self.get_uids_butto.setObjectName(u"get_uids_butto")

        self.verticalLayout.addWidget(self.get_uids_butto)

        self.Log_for_message = QTextEdit(self.widget)
        self.Log_for_message.setObjectName(u"Log_for_message")

        self.verticalLayout.addWidget(self.Log_for_message)

        self.Start_config_butto = QPushButton(self.widget)
        self.Start_config_butto.setObjectName(u"Start_config_butto")

        self.verticalLayout.addWidget(self.Start_config_butto)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 1114, 33))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.COMPort_selec.setItemText(0, QCoreApplication.translate("MainWindow", u"Select Com port", None))
        self.COMPort_selec.setItemText(1, QCoreApplication.translate("MainWindow", u"New Item", None))
        self.COMPort_selec.setItemText(2, QCoreApplication.translate("MainWindow", u"New Item", None))
        self.COMPort_selec.setItemText(3, QCoreApplication.translate("MainWindow", u"New Item", None))
        self.COMPort_selec.setItemText(4, QCoreApplication.translate("MainWindow", u"New Item", None))

        self.NUM_Sensor.setText(QCoreApplication.translate("MainWindow", u"How many sensors are connected?", None))
        self.Verbose_check_bo.setText(QCoreApplication.translate("MainWindow", u"Verbose mode", None))
        self.get_uids_butto.setText(QCoreApplication.translate("MainWindow", u"Get UIDs", None))
        self.Log_for_message.setHtml(QCoreApplication.translate("MainWindow", u"<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><meta charset=\"utf-8\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"hr { height: 1px; border-width: 0; }\n"
"li.unchecked::marker { content: \"\\2610\"; }\n"
"li.checked::marker { content: \"\\2612\"; }\n"
"</style></head><body style=\" font-family:'Segoe UI'; font-size:9pt; font-weight:400; font-style:normal;\">\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Displays live log messages:</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p></body></html>", None))
        self.Start_config_butto.setText(QCoreApplication.translate("MainWindow", u"Start Configuration", None))
    # retranslateUi

