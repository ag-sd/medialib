
from PyQt6.QtCore import QTimer, pyqtSignal, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QLineEdit, QApplication, QHBoxLayout, QWidget, QDockWidget, QListWidget, QVBoxLayout, \
    QTabWidget, QListWidgetItem, QDialog, QDialogButtonBox, QFrame, QLabel

from app import views
from app.database.ds import Database
from app.views import ViewType


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


class DatabasePropertyDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.db_paths = QListWidget()
        self.db_views = QListWidget()
        self.db_props = QLabel()
        self.tabs = QTabWidget()
        self._init_ui()

    def set_database(self, database: Database, show_details=False):
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

        self.db_props.setText(self._prop_str(database))
        self.db_props.setContentsMargins(5, 5, 5, 5)
        add_data(self.db_paths, database.paths, path_icon_provider)
        # add_data(self.db_views, [v.name for v in database.views], view_icon_provider)
        self.tabs.setTabVisible(0, show_details)

    @property
    def database_paths(self):
        return self.get_list(self.db_paths, str)

    def _init_ui(self):
        self.db_props.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.db_paths.setFrameStyle(QFrame.Shape.NoFrame | QFrame.Shadow.Plain)
        self.db_views.setFrameStyle(QFrame.Shape.NoFrame | QFrame.Shadow.Plain)

        self.tabs.addTab(self.db_props, "Details")
        self.tabs.addTab(self.db_paths, "Paths")
        # self.tabs.addTab(self.db_views, "Views")

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok, Qt.Orientation.Horizontal, self)
        buttons.accepted.connect(self.accept)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.tabs)
        main_layout.addWidget(buttons)
        self.setLayout(main_layout)
        self.setMinimumWidth(400)
        self.setMinimumHeight(500)
        self.setWindowTitle("Database Properties")

    @staticmethod
    def _prop_str(database: Database):
        def prop_str(prop, value):
            return f"<pre><p>{prop}<br>  <b><i>{value}</b></i></p></pre>"

        return f"{prop_str('Save Path', database.save_path)}" \
               f"{prop_str('Created', database.created)}" \
               f"{prop_str('Updated', database.updated)}"

    @staticmethod
    def get_list(list_widget, cast):
        items = []
        for i in range(list_widget.count()):
            entry = list_widget.item(i)
            if entry.checkState() == Qt.CheckState.Checked:
                items.append(cast(entry.text()))
        return items


if __name__ == '__main__':
    import sys

    xapp = QApplication(sys.argv)

    # ex = DatabaseSaveModal(None, Database.create_default(
    #     ["/home/sheldon/.cddb",
    #      "/mnt/dev/testing",
    #      "/mnt/dev/art-of-being",
    #      "/home/sheldon/Downloads/art-of-being/images/slider-img3.jpg"
    #      ]), save_mode="TESTING MODE")
    ex = DatabasePropertyDialog()
    ex.set_database(Database.create_in_memory(
        ["/home/sheldon/.cddb",
         "/mnt/dev/testing",
         "/mnt/dev/art-of-being",
         "/home/sheldon/Downloads/art-of-being/images/slider-img3.jpg"
         ]), show_details=True)
    # print(ex.get_database())
    # ex.show()
    sys.exit(xapp.exec())
