from PyQt5.QtWidgets import (
    QDialog,
    QTimeEdit,
    QDateEdit,
    QDialogButtonBox,
    QLayout,    
    QComboBox,
    QLabel,
    QHBoxLayout,
    QVBoxLayout,
    QMessageBox,
    QSpinBox,
    QFormLayout
)

from PyQt5.QtGui import QKeyEvent, QCloseEvent
from PyQt5.QtCore import pyqtSignal, Qt , QDate

from datetime import datetime
from typing import List
from requests import get as urlget, post as urlpost, ConnectionError, Timeout

from srvrcfg import SERVERURL, headers, TIMEOUT


class EditSemesterDia(QDialog):
    invalid = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle("Update Details of the Semester: ")
        self.SelectYear = QComboBox()
        active_sems = self.getActiveSemsters()
        # print(active_sems)
        active_sems = [str(i) for i in active_sems]
        self.SelectYear.addItems(active_sems)
        self.SelectYear.setCurrentIndex(-1)

        if parent:
            parent.setDisabled(True)
            self.setEnabled(True)

        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok, self)
        buttonBox.button(QDialogButtonBox.Ok).setText("Update")

        self.error = False
        self.startDate = QDateEdit()
        self.count = QSpinBox()
        self.start= QTimeEdit() 
        self.end= QTimeEdit() 
        # self.year(): QHBoxLayout()
        self.label =  QLabel()
        self.label2 =  QLabel()
        self.label3 = QLabel()
        
        layout = QFormLayout(self)
        self.label.setText("Select the Semester:")
        self.SelectYear.currentIndexChanged.connect(self.getSemesterDetails)
        layout.addRow(self.label,self.SelectYear)
        self.label2.setText("Select the Start Date : ")
        self.startDate.setCalendarPopup(True)
        layout.addRow(self.label2,self.startDate)
        self.layout().setSizeConstraint(QLayout.SetFixedSize)
        self.label3.setText("Update the Lunch Timings (if any) :")
        layout.addWidget(self.label3)
        # self.getLunchTimeByYear()
        self.l1 = QLabel()
        self.l1.setText("From")
        self.l2 = QLabel()
        self.l2.setText("To")
        self.l3 = QLabel()
        self.l3.setText("Late Limit :")
        self.count.setMinimum(1)
        self.count.setMaximum(20)
        # self.count.setValue()
        layout.addRow(self.l1,self.start)
        layout.addRow(self.l2,self.end)
        layout.addRow(self.l3,self.count)
        layout.addRow(buttonBox)
        # self.getLunchTime()

        buttonBox.accepted.connect(self.updateSemesterDetails)
        
    def getActiveSemsters(self):
        try:
            res = urlget(f"{SERVERURL}/get_active_semesters")
            return res.json()
        except(ConnectionError,Timeout):
            self.parent().error("Connection Error!\nCheck Connection & Try again.")
            self.parent().status.setText("Connection Error.")
            self.error = True
            self.reject()
            return
    def updateSemesterDetails(self):
        if self.SelectYear.currentIndex()<0:
            self.parent().error("No Semester Selected!.")
            self.parent().status.setText("Please select a semester")
            return
        semester = int(self.SelectYear.currentText())
        data = {}
        data["startDate"] = self.startDate.date().toString("yyyy-MM-dd")
        data["openingTimeLunch"] = self.start.time().toString("HH:mm")
        data["closingTimeLunch"] = self.end.time().toString("HH:mm")
        if data["openingTimeLunch"]>data["closingTimeLunch"]:
            self.parent().error("Closing Time is greater than the Opening Time.Please Check!")
            self.parent().status.setText("Check the Timings")
            return
        data["lateCount"] = self.count.value()
        try:
            res = urlpost(
                f"{SERVERURL}/edit_semester?semester={semester}",
                headers=headers,
                json=data,
                timeout=TIMEOUT,
            )
        except (ConnectionError, Timeout):
            self.parent().error("Connection Error!\nCheck Connection & Try again.")
            self.parent().status.setText("Connection Error.")
            return
        if res.status_code == 200:
            self.parent().success("Semester Details Modified Successfully")
            self.close()
        else:
            self.parent().status.setText("Unexpected Error.")
            self.parent().error(f"Unexpected Error. {res.content.decode()}")
        
        
    def getSemesterDetails(self):
        semester = int(self.SelectYear.currentText())
        try:
            res = urlget(f"{SERVERURL}/get_semester_details?semester={semester}")
            data = res.json()
            qdate = QDate.fromString(data["Start Date"], "yyyy-MM-dd")
            self.startDate.setDate(qdate)
            self.count.setValue(data["Late Limit"])
            startT = datetime.strptime(data["Lunch Opening Time"], "%H:%M").time()
            endT = datetime.strptime(data["Lunch Closing Time"], "%H:%M").time()
            self.start.setTime(startT)
            self.end.setTime(endT)
        except(ConnectionError,Timeout):
            self.parent().error("Connection Error!\nCheck Connection & Try again.")
            self.parent().status.setText("Connection Error.")
            self.error = True
            self.reject()
            return

    def reject(self):
        if self.parent():
            self.parent().setEnabled(True)
        super().reject()

    def closeEvent(self, a0: QCloseEvent) -> None:
        if self.parent():
            self.parent().setEnabled(True)
        return super().closeEvent(a0)
