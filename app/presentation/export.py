from datetime import datetime
from enum import Enum

import tablib
from PyQt6.QtCore import Qt, QSortFilterProxyModel, QRegularExpression

import app
from app.presentation.models import TableModel


class ExportFormat(Enum):
    CSV = "csv", "wb", "csv", "Comma Separated file (*.csv)"
    HTML = "html", "w", "htm", "HTML file (*.htm)"
    JSON = "json", "w", "json", "Javascript Object Notation file (*.json)"
    LATEX = "latex", "w", "tex", "Latex Document (*.tex)"
    ODS = "ods", "wb", "ods", "OpenDocument Spreadsheet file (*.ods)"
    TSV = "tsv", "w", "tsv", "Tab Separated file (*.tsv)"
    XLSX = "xlsx", "wb", "xlsx", "Microsoft Excel spreadsheet (*.xlsx)"
    YAML = "yaml", "w", "yaml", "YAML file (*.yaml)"

    def __init__(self, value, file_mode, extension, file_filter):
        self._value = value
        self._file_mode = file_mode
        self._ext = extension
        self._filter = file_filter

    @property
    def filter(self):
        return self._filter

    @property
    def extension(self):
        return self._ext

    @property
    def value(self):
        return self._value

    @property
    def file_mode(self):
        return self._file_mode

    @classmethod
    def from_filter(cls, _filter: str):
        for v in cls:
            if v.filter == _filter:
                return v

        return None

    @classmethod
    def available_formats(cls):
        extensions = []
        for v in ExportFormat:
            extensions.append(v.filter)
        return ";;".join(extensions)


def from_data(save_file: str, table_items: list, fields: list,
              search_text: str, sort_column: int, sort_order: Qt.SortOrder, export_format: ExportFormat):
    """
    Creates a proxy model from the table items with the supplied sort and filter and saves it to a file. This is
    useful for tree models which are difficult to correctly export to a flat tabular view
    Args:
        save_file: The file to save the data to
        table_items: The items to save
        fields: The fields associated with the items
        search_text: The search text. Can be blank if not applicable
        sort_column: The column to sort the model by
        sort_order: The sort order

    """
    # First create a table model from the data set
    app.logger.debug("Building data model from the dataset")
    model = TableModel(table_items, fields)

    # Then create a proxy model
    proxy_model = QSortFilterProxyModel()
    proxy_model.setSourceModel(model)

    # Sort it based on the reference model
    app.logger.debug("Sorting it based on user input")
    proxy_model.sort(sort_column, sort_order)

    # Then apply the search filter on the model
    if search_text != "":
        app.logger.debug("Applying search filter")
        re = QRegularExpression(search_text, QRegularExpression.PatternOption.CaseInsensitiveOption)
        proxy_model.setFilterRegularExpression(re)

    # Export it to a file based on the file extension
    from_model(save_file, proxy_model, export_format)


def from_model(save_file: str, proxy_model: QSortFilterProxyModel, export_format: ExportFormat):
    headers = []
    for i in range(0, proxy_model.columnCount()):
        headers.append(proxy_model.headerData(i, Qt.Orientation.Horizontal))
    app.logger.debug(f"Exporting data to {export_format} in file {save_file}")
    data = tablib.Dataset(headers=headers,
                          title=f"{app.__APP_NAME__} Data Export [{datetime.today().strftime('%Y-%m-%d')}]")
    row_count = proxy_model.rowCount()
    ten_pct = round(row_count * 0.1)
    counter = 0
    for r in range(0, row_count):
        row = []
        for c in range(0, proxy_model.columnCount()):
            index = proxy_model.index(r, c)
            row.append(proxy_model.data(index, Qt.ItemDataRole.DisplayRole))
            if counter >= ten_pct:
                app.logger.debug(f"{round(r * 100 / row_count)}% read")
                counter = 0
        counter += 1
        data.append(row)
    # Write to file
    app.logger.debug(f"Writing to file ... {save_file}")
    with open(save_file, export_format.file_mode) as f:
        f.write(data.export(export_format.value))
    app.logger.debug("Export complete.")

