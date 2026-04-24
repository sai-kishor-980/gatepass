from PyQt5.QtWidgets import (
    QDialog, QDialogButtonBox, QLayout, QLabel, QPushButton,
    QFormLayout, QLineEdit, QFileDialog, QApplication,
    QVBoxLayout, QMessageBox, QComboBox
)
import json
import pandas as pd
import os
import tempfile
import zipfile

from PyQt5.QtGui import QCloseEvent
from PyQt5.QtCore import pyqtSignal, Qt, pyqtSlot

from requests import post as urlpost, get as urlget

from srvrcfg import SERVERURL, TIMEOUT


class UploadDialog(QDialog):
    invalid = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.setWindowTitle("Add / Update Student Data")

        if parent:
            parent.setDisabled(True)
            self.setEnabled(True)

        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        # -------------------------------
        # MODE
        # -------------------------------
        self.modeLabel = QLabel("Select Mode :")
        self.modeBox = QComboBox()
        self.modeBox.addItems(["Upload", "Update"])
        self.modeBox.setCurrentIndex(-1)

        # -------------------------------
        # Upload type
        # -------------------------------
        self.typeLabel = QLabel("Admission Type :")
        self.typeBox = QComboBox()
        self.typeBox.addItems([
            "1st Year Regular",
            "2nd Year LE"
        ])
        self.typeBox.setCurrentIndex(-1)

        # -------------------------------
        # Semester for update
        # -------------------------------
        self.semLabel = QLabel("Select Semester :")
        self.semBox = QComboBox()
        self.semBox.setCurrentIndex(-1)

        # -------------------------------
        # Files
        # -------------------------------
        self.file_label = QLabel("Select Excel or CSV File:")
        self.file_input = QLineEdit()
        self.file_input.setReadOnly(True)
        self.file_btn = QPushButton("Browse File")
        self.file_btn.clicked.connect(self.select_file)

        self.zip_label = QLabel("Upload Images ZIP:")
        self.zip_input = QLineEdit()
        self.zip_input.setReadOnly(True)
        self.zip_btn = QPushButton("Browse ZIP")
        self.zip_btn.clicked.connect(self.select_zip)

        # -------------------------------
        # Button
        # -------------------------------
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok, self)
        buttonBox.button(QDialogButtonBox.Ok).setText("Process")

        # -------------------------------
        # Layout
        # -------------------------------
        layout = QFormLayout(self)

        layout.addRow(self.modeLabel, self.modeBox)
        layout.addRow(self.typeLabel, self.typeBox)
        layout.addRow(self.semLabel, self.semBox)

        layout.addRow(self.file_label)
        layout.addRow(self.file_input, self.file_btn)

        layout.addRow(self.zip_label)
        layout.addRow(self.zip_input, self.zip_btn)

        layout.addRow(buttonBox)

        self.layout().setSizeConstraint(QLayout.SetFixedSize)

        # -------------------------------
        # Signals
        # -------------------------------
        self.modeBox.currentIndexChanged.connect(self.mode_changed)
        buttonBox.accepted.connect(self.process)

        self.mode_changed()

    # ---------------------------------------
    # UI Mode Change
    # ---------------------------------------
    def mode_changed(self):

        mode = self.modeBox.currentText()

        if mode == "Upload":
            self.typeLabel.show()
            self.typeBox.show()

            self.semLabel.hide()
            self.semBox.hide()

            self.zip_label.setText("Upload Images ZIP:")

        elif mode == "Update":
            self.typeLabel.hide()
            self.typeBox.hide()

            self.semLabel.show()
            self.semBox.show()

            self.zip_label.setText("Upload Images ZIP: (Optional)")

            self.load_active_semesters()

        else:
            self.typeLabel.hide()
            self.typeBox.hide()
            self.semLabel.hide()
            self.semBox.hide()

    # ---------------------------------------
    # Load Active Semesters
    # ---------------------------------------
    def load_active_semesters(self):

        self.semBox.clear()

        try:
            res = urlget(
                SERVERURL + "/get_active_semesters",
                timeout=TIMEOUT
            )

            arr = res.json()

            for x in arr:
                self.semBox.addItem(str(x))

            self.semBox.setCurrentIndex(-1)

        except:
            pass

    # ---------------------------------------
    # File Picker
    # ---------------------------------------
    def select_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select File",
            "",
            "Data Files (*.csv *.xlsx *.xls)"
        )

        if path:
            self.file_input.setText(path)

    # ---------------------------------------
    # Zip Picker
    # ---------------------------------------
    def select_zip(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select ZIP File",
            "",
            "ZIP Files (*.zip)"
        )

        if path:
            self.zip_input.setText(path)

    # ---------------------------------------
    # Main Process
    # ---------------------------------------
    def process(self):

        mode = self.modeBox.currentText()

        if mode == "":
            self.error("Please Select Mode")
            return

        file_path = self.file_input.text().strip()
        zip_path = self.zip_input.text().strip()

        if not os.path.exists(file_path):
            self.error("Data File not found.")
            return

        if mode == "Upload":
            if self.typeBox.currentIndex() < 0:
                self.error("Select Admission Type")
                return

            if not os.path.exists(zip_path):
                self.error("Images ZIP compulsory for Upload")
                return

        if mode == "Update":
            if self.semBox.currentIndex() < 0:
                self.error("Select Semester")
                return

        processing = ProcessingDialog()
        processing.show()
        QApplication.processEvents()

        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".csv":
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)

        cols = [
            "Roll No.",
            "Adm. No.",
            "Sec",
            "Name of the Student",
            "Department"
        ]

        for col in cols:
            if col not in df.columns:
                processing.close()
                self.error(f"Missing Column : {col}")
                return

        df = df[cols].copy()
        df["Roll No."] = df["Roll No."].astype(str).str.strip()

        temp_dir = tempfile.mkdtemp()
        image_map = {}

        if os.path.exists(zip_path):

            rolls = set(df["Roll No."].tolist())

            with zipfile.ZipFile(zip_path, "r") as zf:

                for name in zf.namelist():

                    if name.lower().endswith(
                        (".png", ".jpg", ".jpeg")
                    ):

                        roll = os.path.splitext(
                            os.path.basename(name)
                        )[0].strip()

                        if roll in rolls:
                            p = zf.extract(name, temp_dir)
                            image_map[roll] = p

        # Upload mode = image compulsory
        if mode == "Upload":
            valid = df[
                df["Roll No."].isin(image_map.keys())
            ]
            invalid = df[
                ~df["Roll No."].isin(image_map.keys())
            ]
        else:
            valid = df
            invalid = pd.DataFrame()

        self.valid_df = valid
        self.image_map = image_map
        self.mode = mode

        if mode == "Upload":
            self.admission_type = self.typeBox.currentText()
            self.semester = ""
        else:
            self.admission_type = ""
            self.semester = self.semBox.currentText()

        report = (
            f"✅ Valid : {len(valid)}\n"
            f"❌ Invalid : {len(invalid)}"
        )

        processing.close()

        dlg = ResultDialog(report, self)
        dlg.exec_()

    # ---------------------------------------
    # Error Popup
    # ---------------------------------------
    @pyqtSlot(str)
    def error(self, msg):
        QMessageBox.critical(self, "Error", msg)

    def reject(self):
        if self.parent():
            self.parent().setEnabled(True)
        super().reject()

    def closeEvent(self, a0: QCloseEvent):
        if self.parent():
            self.parent().setEnabled(True)
        return super().closeEvent(a0)


# =====================================
# Processing Dialog
# =====================================
class ProcessingDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Processing")

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Please wait..."))

        self.setFixedSize(200, 100)


# =====================================
# Result Dialog
# =====================================
class ResultDialog(QDialog):
    def __init__(self, txt, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Result")

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(txt))

        self.submit_btn = QPushButton("Submit")
        self.close_btn = QPushButton("Close")

        layout.addWidget(self.submit_btn)
        layout.addWidget(self.close_btn)

        self.submit_btn.clicked.connect(self.submit_data)
        self.close_btn.clicked.connect(self.close_all)

    def close_all(self):
        parent = self.parent()

        self.close()

        if parent:
            parent.close()

            if parent.parent():
                parent.parent().setEnabled(True)
                parent.parent().show()

    def submit_data(self):

        parent = self.parent()

        processing = ProcessingDialog()
        processing.show()
        QApplication.processEvents()

        files = []

        for roll, path in parent.image_map.items():

            f = open(path, "rb")

            ext = os.path.splitext(path)[1].lower()

            mime = "image/png" if ext == ".png" else "image/jpeg"

            files.append(
                ("images", (os.path.basename(path), f, mime))
            )

        payload = {
            "students": json.dumps(
                parent.valid_df.to_dict(orient="records")
            ),
            "mode": parent.mode,
            "admission_type": parent.admission_type,
            "semester": parent.semester
        }

        try:
            res = urlpost(
                SERVERURL + "/upload_data",
                data=payload,
                files=files,
                timeout=TIMEOUT
            )

            resp = res.json()

            summary = resp.get("summary", {})

            created = summary.get("created", 0)
            updated = summary.get("updated", 0)
            failed = summary.get("failed", 0)

            # Better message handling
            if created == 0 and updated == 0 and failed > 0:
                msg = "No changes made.\nAll selected students already exist."
            else:
                msg = (
                    f"Created : {created}\n"
                    f"Updated : {updated}\n"
                    f"Failed : {failed}"
                )

            QMessageBox.information(self, "Result", msg)


            processing.close()
            self.close_all()

        except Exception as e:
            processing.close()
            QMessageBox.critical(
                self,
                "Error",
                str(e)
            )

        finally:
            for _, (_, f, _) in files:
                f.close()
