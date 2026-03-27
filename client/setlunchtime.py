from PyQt5.QtWidgets import (
    QDialog,
    QTimeEdit,
    QDialogButtonBox,
    QLayout,
    QLabel,
    QHBoxLayout,
    QVBoxLayout,
    QMessageBox,
)
from PyQt5.QtGui import QKeyEvent, QCloseEvent
from PyQt5.QtCore import pyqtSignal, Qt

from datetime import datetime
from typing import List
from requests import get as urlget, post as urlpost, ConnectionError, Timeout

from srvrcfg import SERVERURL, headers


class LunchTimeDialog(QDialog):
    invalid = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle("Set Lunch Time")

        if parent:
            parent.setDisabled(True)
            self.setEnabled(True)

        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok, self)

        self.error = False
        self.start: List[QTimeEdit] = []
        self.end: List[QTimeEdit] = []
        self.years: List[QHBoxLayout] = []
        self.label: List[QLabel] = []
        self.label2: List[QLabel] = []
        for i in range(3):
            self.start.append(QTimeEdit())
            self.end.append(QTimeEdit())
            self.years.append(QHBoxLayout())
            self.label.append(QLabel())
            self.label2.append(QLabel())
            self.label[i].setText(f"{i+1} year: ")
            self.label2[i].setText(" to ")
            self.years[i].addWidget(self.label[i])
            self.years[i].addWidget(self.start[i])
            self.years[i].addWidget(self.label2[i])
            self.years[i].addWidget(self.end[i])

        layout = QVBoxLayout(self)
        for i in range(3):
            layout.addLayout(self.years[i])
        layout.addWidget(buttonBox)

        self.layout().setSizeConstraint(QLayout.SetFixedSize)
        self.getLunchTime()

        buttonBox.accepted.connect(self.setLunchTime)

    def getLunchTime(self):
        res = None
        try:
            res = urlget(f"{SERVERURL}/get_timings", timeout=TIMEOUT).json()
        except (ConnectionError, Timeout):
            self.parent().error("Connection Error!\nCheck Connection & Try again.")
            self.parent().status.setText("Connection Error.")
            self.error = True
            self.reject()
            return

        if res == []:
            QMessageBox.warning(self.parent(), "Warning!", "Lunch Timings not set!")
            res = [
                {"opening_time": "12:00", "closing_time": "13:00"},
                {"opening_time": "13:00", "closing_time": "14:00"},
                {"opening_time": "13:00", "closing_time": "14:00"},
                {"opening_time": "13:00", "closing_time": "14:00"},
            ]

        for i in range(3):
            start = datetime.strptime(res[i]["opening_time"], "%H:%M").time()
            end = datetime.strptime(res[i]["closing_time"], "%H:%M").time()

            self.start[i].setTime(start)
            self.end[i].setTime(end)

    def setLunchTime(self):
        lunchtimes = []
        for i in range(3):
            lunchtimes.append(
                {
                    "opening_time": self.start[i].time().toString("HH:mm"),
                    "closing_time": self.end[i].time().toString("HH:mm"),
                }
            )
            # print("Start", i, ":", start)
            # print("End", i, ":", end)

        try:
            res = urlpost(
                f"{SERVERURL}/edit_timings",
                headers=headers,
                json=lunchtimes,
                timeout=TIMEOUT,
            )
        except (ConnectionError, Timeout):
            self.parent().error("Connection Error!\nCheck Connection & Try again.")
            self.parent().status.setText("Connection Error.")
            return

        if res.status_code == 200:
            self.parent().success("Lunch Time modified successfully.")
            self.close()
        else:
            self.parent().status.setText("Unexpected Error.")
            self.parent().error(f"Unexpected Error. {res.content.decode()}")

    def reject(self):
        if self.parent():
            self.parent().setEnabled(True)
        super().reject()

    def closeEvent(self, a0: QCloseEvent) -> None:
        if self.parent():
            self.parent().setEnabled(True)
        return super().closeEvent(a0)
