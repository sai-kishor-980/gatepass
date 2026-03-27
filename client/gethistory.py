from PyQt5.QtWidgets import (
    QDialog,
    QDateEdit,
    QDialogButtonBox,
    QLayout,
    QLabel,
    QLineEdit,
    QCheckBox,
    QFormLayout,
    QComboBox
)
from PyQt5.QtGui import QCloseEvent
from PyQt5.QtCore import pyqtSignal, Qt

from datetime import date
from re import fullmatch
from requests import get as urlget, post as urlpost, ConnectionError, Timeout
from srvrcfg import SERVERURL

DATE = date.today()

class GetHistoryDialog(QDialog):
    def __init__(self, parent, type):
        super().__init__(parent=parent)
        self.setWindowTitle(f"{type} History")
    
        parent.setDisabled(True)
        self.setEnabled(True)

        self.type = type

        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok, self)

        self.start = QDateEdit()
        self.start.setDate(DATE)
        self.start.setDisplayFormat("dd-MM-yyyy")
        self.end = QDateEdit()
        self.end.setDate(DATE)
        self.end.setDisplayFormat("dd-MM-yyyy")
        self.startLabel = QLabel()
        self.endLabel = QLabel()
        self.startLabel.setText("From:")
        self.endLabel.setText("To:")
        self.yrLabel = QLabel()
        self.yrLabel.setText("Select the Semester:")
        self.SelectYear = QComboBox()
        active_sems = self.getActiveSemsters()
        # print(active_sems)
        active_sems = [str(i) for i in active_sems]
        self.SelectYear.addItems(active_sems)
        self.SelectYear.setCurrentIndex(-1)

        self.rnoLabel = QLabel()
        self.rnoLabel.setText("Roll No.:")
        self.rno = QLineEdit()
        self.rno.setPlaceholderText("(Optional)")
        self.rno.setMaxLength(10)
        self.rno.editingFinished.connect(
            lambda: self.rno.setText(self.rno.text().upper())
        )
        # self.rno.textChanged.connect(lambda: self.fullHistory.setEnabled(bool(self.rno.text())))

        self.fullHistory = QCheckBox("Get Full History")
        self.fullHistory.setChecked(False)
        # self.fullHistory.setDisabled(True)
        self.fullHistory.toggled.connect(
            lambda state: (self.start.setDisabled(state), self.end.setDisabled(state))
        )

        layout = QFormLayout(self)
        layout.addRow(self.yrLabel,self.SelectYear)
        layout.addRow(self.startLabel, self.start)
        layout.addRow(self.endLabel, self.end)
        layout.addRow(None, self.fullHistory)
        layout.addRow(self.rnoLabel, self.rno)
        self.rno.textChanged.connect(self.roll_changed)
        self.SelectYear.currentIndexChanged.connect(self.year_changed)
        layout.addWidget(buttonBox)

        self.layout().setSizeConstraint(QLayout.SetFixedSize)

        buttonBox.accepted.connect(self.getHistory)
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
    def getHistory(self):
        rno = self.rno.text().upper()
        if (rno != "") and not fullmatch(r"\d{2}BD1A\d{2}[A-HJ-NP-RT-Z0-9]{2}", rno):
            self.parent().error("Provide a valid Roll No. to filter history")
            return
        if (
            (start := self.start.date().toPyDate()) > DATE
            or (end := self.end.date().toPyDate()) > DATE
            or start > end
        ):
            self.parent().error("Provide valid range of Dates")
            return

        start = self.start.date().toString("yyyy-MM-dd")
        end = self.end.date().toString("yyyy-MM-dd")
        semester = None
        if self.SelectYear.currentIndex()>0:
            semester = int(self.SelectYear.currentText())
        from webbrowser import open as open_in_browser

        if self.type == "Issue":
            baseurl = f"{SERVERURL}/get_issued_passes"
        elif self.type == "Scan":
            baseurl = f"{SERVERURL}/get_scan_history"
    
        args = "ret_type=csv"
        if rno:
            args += f"&rollno={rno}"
            if not self.fullHistory.isChecked():
                args += f"&frm={start}&to={end}"
        elif semester:
            args += f"&semester={semester}"
            if not self.fullHistory.isChecked():
                args+=f"&frm={start}&to={end}"
        elif not self.fullHistory.isChecked():
            args += f"&frm={start}&to={end}"    
        open_in_browser(f"{baseurl}?{args}")
        self.parent().success("CSV Download started in browser.")
        self.close()
    def year_changed(self):
        if self.SelectYear.currentText():
            self.rno.setDisabled(True)
        else:
            self.rno.setDisabled(False)
    def roll_changed(self):
        if self.rno.text().strip():
            self.SelectYear.setDisabled(True)
        else:
            self.SelectYear.setDisabled(False)
    def reject(self):
        if self.parent():
            self.parent().setEnabled(True)
        super().reject()

    def closeEvent(self, a0: QCloseEvent) -> None:
        if self.parent():
            self.parent().setEnabled(True)
        return super().closeEvent(a0)
