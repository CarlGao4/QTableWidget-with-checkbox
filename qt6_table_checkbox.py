import threading
import warnings
from typing import Iterable, Optional, Union

from PyQt6.QtCore import (
    QItemSelectionModel,
    QModelIndex,
    QPersistentModelIndex,
    QPoint,
    QRect,
    Qt,
    pyqtSignal as Signal,
)
from PyQt6.QtWidgets import (
    QAbstractItemDelegate,
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QHBoxLayout,
    QHeaderView,
    QMainWindow,
    QStyle,
    QStyleOptionButton,
    QTableWidget,
    QTableWidgetItem,
    QTableWidgetSelectionRange,
    QWidget,
)

__version__ = "0.0.1a0"


class NotImplementedWarning(Warning):
    pass


class _CheckBoxHeader(QHeaderView):
    select_all_clicked = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(Qt.Orientation.Horizontal, parent)
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
            dx = (rect.width() - checkboxWidth) // 2
            dy = (rect.height() - checkboxHeight) // 2

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
                return
        super().mousePressEvent(event)

    def setOn(self, isOn):
        if self.isOn != isOn:
            self.isOn = isOn
            self.updateSection(0)


class _QCheckBoxWithoutFocus(QCheckBox):
    def focusInEvent(self, event):
        self.parent().parent().setFocus(Qt.FocusReason.OtherFocusReason)


class QTableWidgetWithCheckBox(QTableWidget):
    def __init__(self, rows: int = 0, columns: int = 0, parent: Optional[QWidget] = None):
        """QTableWidget with a checkbox column. The checkbox column is always the first column."""
        super().__init__(rows, columns + 1, parent)
        self.super = super()

        self._header = _CheckBoxHeader()
        self.super.setHorizontalHeader(self._header)
        self._header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._header.select_all_clicked.connect(self.checkAll)

        self._lock = threading.RLock()
        self._checkboxStateChangedLock = threading.Lock()

    # Reimplement QTableWidget functions

    def cellWidget(self, row: int, column: int) -> QWidget:
        return self.super.cellWidget(row, column + 1)

    def clear(self) -> None:
        with self._lock:
            for _ in range(1, self.super.columnCount()):
                self.super.removeColumn(1)
            for _ in range(self.super.rowCount()):
                self.super.removeRow(0)

    def clearContents(self) -> None:
        with self._lock:
            for row in range(self.super.rowCount()):
                for column in range(1, self.super.columnCount()):
                    self.super.setItem(row, column, None)

    def column(self, column: Optional[QTableWidgetItem]) -> int:
        return self.super.column(column) - 1

    def columnCount(self) -> int:
        return self.super.columnCount() - 1

    def currentColumn(self) -> int:
        return self.super.currentColumn() - 1

    def horizontalHeaderItem(self, column: int) -> QTableWidgetItem:
        return self.super.horizontalHeaderItem(column + 1)

    def indexFromItem(self, item: Optional[QTableWidgetItem]) -> QModelIndex:
        warnings.warn("indexFromItem() is not overridden", NotImplementedWarning)
        return self.super.indexFromItem(item)

    def insertColumn(self, column: int) -> None:
        self.super.insertColumn(column + 1)

    def item(self, row: int, column: int) -> QTableWidgetItem:
        return self.super.item(row, column + 1)

    def itemAt(  # type: ignore[override]
        self, _arg0: Union[QPoint, int], _arg1: Optional[int] = None
    ) -> Union[QTableWidgetItem, None]:
        """
        ```Python
        @overload
        def itemAt(self, pos: QPoint) -> Union[QTableWidgetItem, None]:
            ...

        @overload
        def itemAt(self, x: int, y: int) -> Union[QTableWidgetItem, None]:
            ...
        ```
        """
        if _arg1 is None:
            if isinstance(_arg0, QPoint):
                x, y = _arg0.x(), _arg0.y()
            else:
                raise TypeError("itemAt() requires a QPoint or two integers")
        else:
            if isinstance(_arg0, int) and isinstance(_arg1, int):
                x, y = _arg0, _arg1
            else:
                raise TypeError("itemAt() requires a QPoint or two integers")
        item = self.super.itemAt(x, y)
        if item is not None and item.column() == 0:
            return None
        return item

    def itemFromIndex(self, index: Union[QModelIndex, QPersistentModelIndex]) -> QTableWidgetItem:
        warnings.warn("itemFromIndex() is not overridden", NotImplementedWarning)
        return self.super.itemFromIndex(index)

    def removeCellWidget(self, row: int, column: int) -> None:
        self.super.removeCellWidget(row, column + 1)

    def removeColumn(self, column: int) -> None:
        self.super.removeColumn(column + 1)

    def removeRow(self, row: int) -> None:
        with self._lock:
            widget = self.super.cellWidget(row, 0)
            if widget is not None:
                checkbox = widget.layout().itemAt(0).widget()  # type: QCheckBox
                if checkbox is not None:
                    checkbox.stateChanged.disconnect(self.onCheckboxStateChanged)
            self.super.removeRow(row)

    def selectedRanges(self) -> list[QTableWidgetSelectionRange]:
        ret = []
        for selected_range in self.super.selectedRanges():
            if selected_range.leftColumn() == 0:
                ret.append(
                    QTableWidgetSelectionRange(
                        selected_range.topRow(), 0, selected_range.bottomRow(), selected_range.rightColumn() - 1
                    )
                )
            else:
                ret.append(
                    QTableWidgetSelectionRange(
                        selected_range.topRow(),
                        selected_range.leftColumn() - 1,
                        selected_range.bottomRow(),
                        selected_range.rightColumn() - 1,
                    )
                )
        return ret

    def setCellWidget(self, row: int, column: int, widget: Optional[QWidget]) -> None:
        self.super.setCellWidget(row, column + 1, widget)

    def setColumnCount(self, columns: int) -> None:
        self.super.setColumnCount(columns + 1)

    def setCurrentCell(
        self,
        _arg0: Union[int, QTableWidgetItem],
        _arg1: Optional[Union[int, QItemSelectionModel.SelectionFlag]] = None,
        _arg2: Optional[QItemSelectionModel.SelectionFlag] = None,
    ) -> None:
        """
        ```Python
        @overload
        def setCurrentCell(self, row: int, column: int) -> None:
            ...

        @overload
        def setCurrentCell(self, row: int, column: int, command: QItemSelectionModel.SelectionFlag) -> None:
            ...

        @overload
        def setCurrentItem(self, item: QTableWidgetItem) -> None:
            ...

        @overload
        def setCurrentItem(self, item: QTableWidgetItem, command: QItemSelectionModel.SelectionFlag) -> None:
            ...
        ```
        """
        if _arg1 is None:
            if isinstance(_arg0, QTableWidgetItem):
                return self.super.setCurrentCell(_arg0)
        elif _arg2 is None:
            if isinstance(_arg0, int) and isinstance(_arg1, int):
                return self.super.setCurrentCell(_arg0, _arg1 + 1)
            elif isinstance(_arg0, QTableWidgetItem) and isinstance(_arg1, QItemSelectionModel.SelectionFlag):
                return self.super.setCurrentCell(_arg0, _arg1)
        elif isinstance(_arg0, int) and isinstance(_arg1, int) and isinstance(_arg2, QItemSelectionModel.SelectionFlag):
            return self.super.setCurrentCell(_arg0, _arg1 + 1, _arg2)
        return self.super.setCurrentCell(_arg0, _arg1, _arg2)  # This will raise an error!

    def setHorizontalHeaderItem(self, column: int, item: Optional[QTableWidgetItem]) -> None:
        self.super.setHorizontalHeaderItem(column + 1, item)

    def setItem(self, row: int, column: int, item: Optional[QTableWidgetItem]) -> None:
        self.super.setItem(row, column + 1, item)

    def setHorizontalHeaderLabels(self, labels: Iterable[Optional[str]]) -> None:
        with self._lock:
            labels = [""] + list(labels)
            self.super.setHorizontalHeaderLabels(labels)

    def setRangeSelected(self, range: QTableWidgetSelectionRange, select: bool) -> None:
        self.super.setRangeSelected(
            QTableWidgetSelectionRange(
                range.topRow(), range.leftColumn() + 1, range.bottomRow(), range.rightColumn() + 1
            ),
            select,
        )

    def sortItems(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder) -> None:
        self.super.sortItems(column + 1, order)

    def takeItem(self, row: int, column: int) -> QTableWidgetItem:
        return self.super.takeItem(row, column + 1)

    def takeHorizontalHeaderItem(self, column: int) -> QTableWidgetItem:
        return self.super.takeHorizontalHeaderItem(column + 1)

    def visualColumn(self, column: int) -> int:
        return self.super.visualColumn(column + 1)

    # Reimplement QTableView functions

    def clearSpans(self) -> None:
        self.clear()

    def columnAt(self, x: int) -> int:
        return self.super.columnAt(x + 1)

    def columnSpan(self, row: int, column: int) -> int:
        return self.super.columnSpan(row, column + 1)

    def columnViewportPosition(self, column: int) -> int:
        return self.super.columnViewportPosition(column + 1)

    def columnWidth(self, column: int) -> int:
        return self.super.columnWidth(column + 1)

    def hideColumn(self, column: int) -> None:
        self.super.hideColumn(column + 1)

    def isColumnHidden(self, column: int) -> bool:
        return self.super.isColumnHidden(column + 1)

    def isIndexHidden(self, index: Union[QModelIndex, QPersistentModelIndex]) -> bool:
        warnings.warn("isIndexHidden() is not overridden", NotImplementedWarning)
        return self.super.isIndexHidden(index)

    def resizeColumnToContents(self, column: int) -> None:
        self.super.resizeColumnToContents(column + 1)

    def rowSpan(self, row: int, column: int) -> int:
        return self.super.rowSpan(row, column + 1)

    def scrollTo(
        self,
        index: Union[QModelIndex, QPersistentModelIndex],
        hint: QAbstractItemView.ScrollHint = QAbstractItemView.ScrollHint.EnsureVisible,
    ) -> None:
        warnings.warn("scrollTo() is not overridden", NotImplementedWarning)
        return self.super.scrollTo(index, hint)

    def selectColumn(self, column: int) -> None:
        self.super.selectColumn(column + 1)

    def selectedIndexes(self) -> list[QModelIndex]:
        warnings.warn("selectedIndexes() is not overridden", NotImplementedWarning)
        return self.super.selectedIndexes()

    def setColumnHidden(self, column: int, hide: bool) -> None:
        self.super.setColumnHidden(column + 1, hide)

    def setColumnWidth(self, column: int, width: int) -> None:
        self.super.setColumnWidth(column + 1, width)

    def setSpan(self, row: int, column: int, rowSpan: int, columnSpan: int) -> None:
        self.super.setSpan(row, column + 1, rowSpan, columnSpan)

    def showColumn(self, column: int) -> None:
        self.super.showColumn(column + 1)

    def sizeHintForColumn(self, column: int) -> int:
        warnings.warn("sizeHintForColumn() is not overridden", NotImplementedWarning)
        return self.super.sizeHintForColumn(column)

    def sortByColumn(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder) -> None:
        self.super.sortByColumn(column + 1, order)

    # Reimplement QAbstractItemView functions

    def indexAt(self, point: QPoint) -> QModelIndex:
        warnings.warn("indexAt() is not overridden", NotImplementedWarning)
        return self.super.indexAt(point)

    def setItemDelegateForColumn(self, column: int, delegate: Optional[QAbstractItemDelegate]) -> None:
        self.super.setItemDelegateForColumn(column + 1, delegate)

    # More functions for QTableWidgetWithCheckBox

    def addRow(self, items: Iterable, state: bool = False, row: Optional[int] = None) -> None:
        with self._lock:
            if row is None:
                row = self.super.rowCount()
            self.super.insertRow(row)

            checkbox = _QCheckBoxWithoutFocus()
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

            self._checkHeader()

    def getCheckState(self, row: int) -> Union[bool, None]:
        with self._lock:
            widget = self.super.cellWidget(row, 0)
            if widget is not None:
                checkbox = widget.layout().itemAt(0).widget()  # type: QCheckBox
                if checkbox is not None:
                    return checkbox.isChecked()
            return None
        
    def setCheckState(self, row: int, state: bool) -> None:
        with self._lock:
            widget = self.super.cellWidget(row, 0)
            if widget is not None:
                checkbox = widget.layout().itemAt(0).widget()  # type: QCheckBox
                if checkbox is not None:
                    checkbox.setChecked(state)
                    self._checkHeader()

    def checkAll(self, isOn: bool) -> None:
        with self._lock:
            for row in range(self.super.rowCount()):
                widget = self.super.cellWidget(row, 0)
                if widget is not None:
                    checkbox = widget.layout().itemAt(0).widget()  # type: QCheckBox
                    if checkbox is not None:
                        checkbox.setChecked(isOn)

    def onCheckboxStateChanged(self, state: int) -> None:
        with self._lock:
            if self._checkboxStateChangedLock.locked():
                return
            with self._checkboxStateChangedLock:
                checkbox_changed = self.super.sender()
                selected_rows = list(set(i.row() for i in self.super.selectedIndexes()))
                if any(
                    checkbox_changed.parent() == self.super.cellWidget(selected_row, 0)
                    for selected_row in selected_rows
                ):
                    for selected_row in selected_rows:
                        widget = self.super.cellWidget(selected_row, 0)
                        if widget is not None:
                            checkbox = widget.layout().itemAt(0).widget()  # type: QCheckBox
                            if checkbox is not None:
                                checkbox.setChecked(state == Qt.CheckState.Checked.value)

                if state == Qt.CheckState.Unchecked.value:
                    self._header.setOn(False)
                else:
                    self._checkHeader()

    def _checkHeader(self) -> None:
        with self._lock:
            for row in range(self.super.rowCount()):
                widget = self.super.cellWidget(row, 0)
                if widget is not None:
                    checkbox = widget.layout().itemAt(0).widget()  # type: QCheckBox
                    if checkbox is not None and checkbox.checkState() == Qt.CheckState.Unchecked:
                        self._header.setOn(False)
                        return
            self._header.setOn(True)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_index = self.super.indexAt(event.position().toPoint())
        if self._press_index.column() != 0:
            self.super.mousePressEvent(event)
        else:
            event.ignore()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            index = self.super.indexAt(event.position().toPoint())
            if index != self._press_index:
                self.super.mouseReleaseEvent(event)
                return
            if index.column() == 0:
                checkbox = self.super.cellWidget(index.row(), 0).layout().itemAt(0).widget()  # type: QCheckBox
                if checkbox is not None:
                    checkbox.toggle()
                    event.ignore()
                else:
                    self.super.mouseReleaseEvent(event)
            else:
                self.super.mouseReleaseEvent(event)
        else:
            self.super.mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            index = self.super.currentIndex()
            if index.column() == 0:
                checkbox = self.super.cellWidget(index.row(), 0).layout().itemAt(0).widget()  # type: QCheckBox
                if checkbox is not None:
                    checkbox.toggle()
                    event.ignore()
                else:
                    self.super.keyPressEvent(event)
            else:
                self.super.keyPressEvent(event)
        else:
            self.super.keyPressEvent(event)


if __name__ == "__main__":

    class MainWindow(QMainWindow):
        def __init__(self):
            super().__init__()

            self.table_widget = QTableWidgetWithCheckBox(0, 3)

            for i in range(5):
                self.table_widget.addRow([f"Item {i}-{j}" for j in range(3)])

            self.table_widget.setHorizontalHeaderLabels([f"Column {i}" for i in range(self.table_widget.columnCount())])
            self.table_widget.setSortingEnabled(True)
            self.table_widget.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

            self.setCentralWidget(self.table_widget)

    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()
