import threading
from typing import Iterable, Optional, Union

from PySide6.QtCore import QRect, Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QHBoxLayout,
    QHeaderView,
    QMainWindow,
    QStyle,
    QStyleOptionButton,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

__version__ = "0.0.1a0"


class CheckBoxHeader(QHeaderView):
    select_all_clicked = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(Qt.Horizontal, parent)
        self.setSectionsClickable(True)
        self.isOn = False
        self.mouseDown = False
        self.hover_on_checkbox = False

    def paintSection(self, painter, rect, logicalIndex):
        painter.save()
        super().paintSection(painter, rect, logicalIndex)
        painter.restore()
        if logicalIndex == 0:
            option = QStyleOptionButton()

            checkboxWidth = self.style().pixelMetric(QStyle.PixelMetric.PM_IndicatorWidth)
            checkboxHeight = self.style().pixelMetric(QStyle.PixelMetric.PM_IndicatorHeight)
            dx = (rect.width() - checkboxWidth) / 2
            dy = (rect.height() - checkboxHeight) / 2

            option.rect = QRect(rect.x() + dx, rect.y() + dy, checkboxWidth, checkboxHeight)
            option.state = QStyle.StateFlag.State_Enabled | QStyle.StateFlag.State_Active
            if self.isOn:
                option.state |= QStyle.StateFlag.State_On
            else:
                option.state |= QStyle.StateFlag.State_Off
            if self.mouseDown:
                option.state |= QStyle.StateFlag.State_Sunken
            elif self.hover_on_checkbox:
                option.state |= QStyle.StateFlag.State_MouseOver
            self.style().drawControl(QStyle.ControlElement.CE_CheckBox, option, painter)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.mouseDown = False
            index = self.logicalIndexAt(event.position().toPoint())
            if index == 0:
                self.isOn = not self.isOn
                self.select_all_clicked.emit(self.isOn)
                self.updateSection(0)
        super().mouseReleaseEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.mouseDown = True
            index = self.logicalIndexAt(event.position().toPoint())
            if index == 0:
                self.updateSection(0)
        super().mousePressEvent(event)

    def setOn(self, isOn):
        if self.isOn != isOn:
            self.isOn = isOn
            self.updateSection(0)


class QTableWidgetWithCheckBox(QTableWidget):
    def __init__(self, rows: int = 0, columns: int = 0, parent: Optional[QWidget] = None):
        """QTableWidget with a checkbox column. The checkbox column is always the first column."""
        super().__init__(rows, columns + 1, parent)
        self.super = super()

        self.super.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.header = CheckBoxHeader()
        self.super.setHorizontalHeader(self.header)
        self.header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.super.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.header.select_all_clicked.connect(self.selectAll)

        self.lock = threading.RLock()

    def addRow(self, items: Iterable, state: bool = False) -> None:
        with self.lock:
            row = self.super.rowCount()
            self.super.insertRow(row)

            checkbox = QCheckBox()
            checkbox.stateChanged.connect(self.onCheckboxStateChanged)
            if state:
                checkbox.setCheckState(Qt.CheckState.Checked)
            else:
                checkbox.setCheckState(Qt.CheckState.Unchecked)

            widget = QWidget()
            layout = QHBoxLayout()
            layout.addWidget(checkbox)
            layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.setContentsMargins(0, 0, 0, 0)
            widget.setLayout(layout)

            self.super.setCellWidget(row, 0, widget)

            for i, item in enumerate(items):
                self.super.setItem(row, i + 1, QTableWidgetItem(str(item)))

    def getCheckState(self, row: int) -> Union[bool, None]:
        with self.lock:
            widget = self.super.cellWidget(row, 0)
            if widget is not None:
                checkbox = widget.layout().itemAt(0).widget()  # type: QCheckBox
                if checkbox is not None:
                    return checkbox.isChecked()

    def selectAll(self, isOn: bool) -> None:
        with self.lock:
            for row in range(self.super.rowCount()):
                widget = self.super.cellWidget(row, 0)
                if widget is not None:
                    checkbox = widget.layout().itemAt(0).widget()  # type: QCheckBox
                    if checkbox is not None:
                        checkbox.setChecked(isOn)

    def onCheckboxStateChanged(self, state: int) -> None:
        with self.lock:
            checkbox = self.super.sender()
            selected_rows = self.super.selectionModel().selectedRows()
            if any(checkbox.parent() == self.super.cellWidget(selected_row.row(), 0) for selected_row in selected_rows):
                for selected_row in selected_rows:
                    widget = self.super.cellWidget(selected_row.row(), 0)
                    if widget is not None:
                        checkbox = widget.layout().itemAt(0).widget()  # type: QCheckBox
                        if checkbox is not None:
                            checkbox.setChecked(state == Qt.CheckState.Checked.value)

            if state == Qt.Unchecked:
                self.header.setOn(False)
            else:
                self.checkHeader()

    def checkHeader(self) -> None:
        with self.lock:
            for row in range(self.super.rowCount()):
                widget = self.super.cellWidget(row, 0)
                if widget is not None:
                    checkbox = widget.layout().itemAt(0).widget()  # type: QCheckBox
                    if checkbox is not None and checkbox.checkState() == Qt.CheckState.Unchecked:
                        return
            self.header.setOn(True)

    def item(self, row: int, column: int) -> QTableWidgetItem:
        return self.super.item(row, column + 1)

    def setItem(self, row: int, column: int, item: QTableWidgetItem) -> None:
        self.super.setItem(row, column + 1, item)

    def setHorizontalHeaderLabels(self, labels: Iterable[str]) -> None:
        with self.lock:
            labels = [""] + list(labels)
            super().setHorizontalHeaderLabels(labels)

    def columnCount(self) -> int:
        return super().columnCount() - 1

    def setSelectionBehavior(self, *_) -> None:
        pass


if __name__ == "__main__":

    class MainWindow(QMainWindow):
        def __init__(self):
            super().__init__()

            self.table_widget = QTableWidgetWithCheckBox(0, 3)

            for i in range(5):
                self.table_widget.addRow([f"Item {i}-{j}" for j in range(3)])

            self.table_widget.setHorizontalHeaderLabels([f"Column {i}" for i in range(self.table_widget.columnCount())])

            self.setCentralWidget(self.table_widget)

    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()
