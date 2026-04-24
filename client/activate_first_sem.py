
from PyQt5.QtWidgets import (
    QDialog,
    QLabel,
    QFormLayout,
    QDialogButtonBox,
    QDateEdit,
    QTimeEdit,
    QSpinBox,
    QMessageBox
)

from PyQt5.QtCore import Qt, QDate, QTime
from datetime import datetime

from requests import get as urlget, post as urlpost

from srvrcfg import SERVERURL, headers, TIMEOUT


class ActivateFirstSemDialog(QDialog):

    # ------------------------------------------------------
    # edit_mode = False  -> Activate
    # edit_mode = True   -> Update existing details
    # ------------------------------------------------------
    def __init__(self, parent=None, edit_mode=False):
        super().__init__(parent)

        self.edit_mode = edit_mode

        self.setWindowTitle("1st Semester Settings")
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        # --------------------------------------------------
        # Widgets
        # --------------------------------------------------
        self.startDate = QDateEdit()
        self.startDate.setCalendarPopup(True)
        self.startDate.setDate(QDate.currentDate())

        self.start = QTimeEdit()
        self.end = QTimeEdit()

        self.count = QSpinBox()
        self.count.setMinimum(1)
        self.count.setMaximum(20)

        # --------------------------------------------------
        # Buttons
        # --------------------------------------------------
        self.buttonBox = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )

        if self.edit_mode:
            self.buttonBox.button(
                QDialogButtonBox.Ok
            ).setText("Update")
        else:
            self.buttonBox.button(
                QDialogButtonBox.Ok
            ).setText("Activate")

        # --------------------------------------------------
        # Layout
        # --------------------------------------------------
        layout = QFormLayout(self)

        layout.addRow("Start Date :", self.startDate)
        layout.addRow("Lunch Opening :", self.start)
        layout.addRow("Lunch Closing :", self.end)
        layout.addRow("Late Limit :", self.count)
        layout.addRow(self.buttonBox)

        # --------------------------------------------------
        # Signals
        # --------------------------------------------------
        self.buttonBox.accepted.connect(self.submit)
        self.buttonBox.rejected.connect(self.reject)

        # --------------------------------------------------
        # Load old semester 1 details
        # --------------------------------------------------
        self.load_old_details()

    # ======================================================
    # LOAD EXISTING DETAILS OF SEM 1
    # ======================================================
    def load_old_details(self):

        try:
            res = urlget(
                SERVERURL + "/get_semester_details?semester=1",
                timeout=TIMEOUT
            )

            data = res.json()

            # Start Date
            qdate = QDate.fromString(
                data["Start Date"],
                "yyyy-MM-dd"
            )
            self.startDate.setDate(qdate)

            # Times
            t1 = datetime.strptime(
                data["Lunch Opening Time"],
                "%H:%M"
            ).time()

            t2 = datetime.strptime(
                data["Lunch Closing Time"],
                "%H:%M"
            ).time()

            self.start.setTime(
                QTime(t1.hour, t1.minute)
            )

            self.end.setTime(
                QTime(t2.hour, t2.minute)
            )

            # Late Limit
            self.count.setValue(
                int(data["Late Limit"])
            )

        except:
            # If old details fail, ignore silently
            pass

    # ======================================================
    # SUBMIT
    # ======================================================
    def submit(self):

        opening = self.start.time().toString("HH:mm")
        closing = self.end.time().toString("HH:mm")

        t1 = datetime.strptime(opening, "%H:%M")
        t2 = datetime.strptime(closing, "%H:%M")

        if t1 >= t2:
            QMessageBox.critical(
                self,
                "Error",
                "Closing time must be greater than Opening time."
            )
            return

        payload = {
            "startDate":
                self.startDate.date().toString("yyyy-MM-dd"),

            "openingTimeLunch": opening,
            "closingTimeLunch": closing,
            "lateCount": self.count.value()
        }

        try:
            res = urlpost(
                SERVERURL + "/activate_first_semester",
                headers=headers,
                json=payload,
                timeout=TIMEOUT
            )

            QMessageBox.information(
                self,
                "Success",
                res.text
            )

            self.accept()

        except:
            QMessageBox.critical(
                self,
                "Error",
                "Server Error."
            )
