from PyQt6.QtCore import Qt, QRegularExpression, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon, QRegularExpressionValidator, QFontDatabase
from PyQt6.QtWidgets import QDialog, QLineEdit, QApplication, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QLabel, \
    QComboBox, QListWidget, QDialogButtonBox, QDockWidget, QTabWidget, QLayout, \
    QListWidgetItem

import app
import apputils
import views
from app.views import ViewType
from database import dbutils
from database.dbutils import DatabaseType, Database


class DatabasePropertyWidget(QWidget):
    def __init__(self):
        """
        Displays the properties of a database
        """
        super().__init__()
        self.db_name = QLineEdit()
        self.db_type = QComboBox()
        self.db_save_path = QLineEdit()
        self.db_save_path_button = QPushButton()
        self.db_created = QLabel("Created")
        self.db_updated = QLabel("Updated")
        self.db_paths = QListWidget()
        self.db_views = QListWidget()

        self._configure_ui()
        self._init_ui()

    def set_database(self, database: Database):
        def path_icon_provider(path):
            icon_name = views.get_mime_type_icon_name(path)
            return views.get_mime_type_icon(icon_name)

        def view_icon_provider(view_name):
            return QIcon.fromTheme(ViewType[view_name].icon)

        def add_data(list_widget, data, icon_provider):
            for datum in data:
                item = QListWidgetItem(icon_provider(datum), datum, list_widget)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked)

        self.db_name.setText(database.name)
        self.db_type.setCurrentText(database.type)
        self.db_save_path.setText(database.save_path)
        self.db_created.setText(database.created if database.created is not None else "")
        self.db_updated.setText(database.updated if database.updated is not None else "")
        add_data(self.db_paths, database.paths, path_icon_provider)
        add_data(self.db_views, [v.name for v in database.views], view_icon_provider)
        self._db_type_changed()

    def get_database(self) -> Database:

        def get_view(name):
            return ViewType[name]

        def get_list(list_widget, cast):
            items = []
            for i in range(list_widget.count()):
                entry = list_widget.item(i)
                if entry.checkState() == Qt.CheckState.Checked:
                    items.append(cast(entry.text()))
            return items

        return Database(
            is_default=self.db_name.text() == dbutils.DEFAULT_DB_NAME,
            database_name=self.db_name.text(),
            save_path=None if self.db_save_path.text() == "" else self.db_save_path.text(),
            paths=get_list(self.db_paths, str),
            views=get_list(self.db_views, get_view),
            database_type=DatabaseType(self.db_type.currentText())
        )

    def _init_ui(self):
        tabs = QTabWidget()
        tabs.addTab(self._wrap_widget(self.db_paths), "Paths")
        tabs.addTab(self._wrap_widget(self.db_views), "Views")
        tabs.addTab(self._get_details_panel(), "Details")

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.db_name)
        main_layout.addWidget(tabs)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(main_layout)

    def _configure_ui(self):
        rx = QRegularExpression("^[a-zA-z0-9_-]+$")
        self.db_name.setPlaceholderText("Database Name")
        self.db_name.setValidator(QRegularExpressionValidator(rx))
        # self.db_name.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.TitleFont))

        self.db_type.setEditable(False)
        self.db_type.addItem(QIcon.fromTheme("folder"), DatabaseType.REGISTERED,
                             f"<p>A registered database will be stored in {app.__APP_NAME__}'s internal"
                             f" library, so that it is always accessible.</p>")
        self.db_type.addItem(QIcon.fromTheme("folder-remote"), DatabaseType.UNREGISTERED,
                             f"<p>An unregistered database is stored in a location of your choice "
                             f"(like a removable disk), and can be opened if {app.__APP_NAME__} "
                             f"can discover that location.</p>")
        self.db_type.currentTextChanged.connect(self._db_type_changed)

        self.db_created.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.db_updated.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))

    @staticmethod
    def _wrap_widget(widget) -> QWidget:
        layout = QVBoxLayout()
        layout.addWidget(widget)
        layout.insertStretch(-1, 1)
        layout.setContentsMargins(5, 5, 5, 5)
        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def _get_details_panel(self) -> QWidget:
        self.db_save_path_button.setIcon(QIcon.fromTheme("document-save"))
        self.db_save_path.setReadOnly(True)
        save_path_layout = QHBoxLayout()
        save_path_layout.setContentsMargins(0, 0, 0, 0)
        save_path_layout.addWidget(self.db_save_path, 90)
        save_path_layout.addWidget(self.db_save_path_button, 10)

        layout = QVBoxLayout()
        layout.addWidget(self.db_type)
        layout.addLayout(save_path_layout)
        layout.addWidget(self.db_created)
        layout.addWidget(self.db_updated)
        layout.insertStretch(-1, 1)
        layout.setContentsMargins(5, 5, 5, 5)
        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def _db_type_changed(self):
        app.logger.debug(f"DB type changed to {self.db_type.currentText()}")
        db_type = DatabaseType(self.db_type.currentText())
        self.db_save_path_button.setVisible(db_type == DatabaseType.UNREGISTERED)
        self.db_type.setToolTip(self.db_type.currentData(Qt.ItemDataRole.UserRole))


class DatabaseSaveModal(QDialog):
    def __init__(self, parent, window_title: str):
        super().__init__(parent)
        self.db_props = DatabasePropertyWidget()
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Save,
                                   Qt.Orientation.Horizontal, self)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.db_props)
        main_layout.addWidget(buttons)

        self.setLayout(main_layout)
        self.setWindowIcon(QIcon("medialib-icon"))
        self.setWindowTitle(window_title)

    def set_database(self, database: Database):
        self.db_props.set_database(database)

    def get_database(self):
        return self.db_props.get_database()

    def accept(self):
        try:
            # Validate
            self.get_database()
        except ValueError as v:
            apputils.show_exception(parent=self, exception=v)


class DatabaseRegistryBrowser(QDockWidget):
    def __init__(self):
        super().__init__()
        self.db_props = DatabasePropertyWidget()
        self.db_saves = QListWidget()
        self.db_saves.itemClicked.connect(self._db_clicked)
        self.load_registry()

        self._update_ui()
        self.setWindowTitle("Database Registry")

    def load_registry(self):
        registry = dbutils.get_registry()
        for db in registry.databases:
            QListWidgetItem(QIcon.fromTheme("database-registry"), db, self.db_saves)

    def get_database(self):
        pass

    def save_database(self, database: Database):
        pass

    def update_database(self, database: Database):
        pass

    def resizeEvent(self, event):
        switch_ratio = 1.7  # 16:9

        current_size = event.size()
        current_ratio = current_size.width() / current_size.height()

        previous_size = event.oldSize()
        previous_ratio = previous_size.width() / previous_size.height()

        if previous_ratio <= switch_ratio < current_ratio:
            self._update_ui(QHBoxLayout())
        elif previous_ratio >= switch_ratio > current_ratio:
            self._update_ui(QVBoxLayout())
        super().resizeEvent(event)

    def _update_ui(self, layout: QLayout = QVBoxLayout()):
        layout.addWidget(self.db_saves, 60)
        layout.addWidget(self.db_props, 40)
        layout_container = QWidget()
        layout_container.setLayout(layout)
        self.setWidget(layout_container)

    def _db_clicked(self, item):
        db_name = item.text()
        self.db_props.set_database(dbutils.get_registry().get(db_name))


class DatabaseSearch(QDockWidget):
    search_event = pyqtSignal(dict)
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Search")
        self.search_text = QLineEdit()
        self.search_text.textChanged.connect(self.text_changed)

        self.search_type_backoff = QTimer()
        self.search_type_backoff.setSingleShot(True)
        self.search_type_backoff.timeout.connect(self.trigger_search_request)

        layout = QHBoxLayout()
        layout.addWidget(self.search_text)
        layout_container = QWidget()
        layout_container.setLayout(layout)
        self.setWidget(layout_container)

    def text_changed(self):
        # Backoff triggering any events for 500ms after the user started typing
        self.search_type_backoff.start(400)

    def trigger_search_request(self):
        app.logger.debug(f"Trigger search for sting `{self.search_text.text()}`")
        self.search_event.emit({
            "text": self.search_text.text()
        })



if __name__ == '__main__':
    import sys

    xapp = QApplication(sys.argv)

    # ex = DatabaseSaveModal(None, Database.create_default(
    #     ["/home/sheldon/.cddb",
    #      "/mnt/dev/testing",
    #      "/mnt/dev/art-of-being",
    #      "/home/sheldon/Downloads/art-of-being/images/slider-img3.jpg"
    #      ]), save_mode="TESTING MODE")
    ex = DatabaseRegistryBrowser()
    # ex.set_database(Database.create_default(
    #     ["/home/sheldon/.cddb",
    #      "/mnt/dev/testing",
    #      "/mnt/dev/art-of-being",
    #      "/home/sheldon/Downloads/art-of-being/images/slider-img3.jpg"
    #      ]))
    # print(ex.get_database())
    ex.show()
    sys.exit(xapp.exec())
