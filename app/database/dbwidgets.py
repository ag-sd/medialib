from PyQt6.QtCore import Qt, QSize, QRegularExpression
from PyQt6.QtGui import QIcon, QRegularExpressionValidator
from PyQt6.QtWidgets import QDialog, QLineEdit, QApplication, QPushButton, QVBoxLayout, QGroupBox, \
    QHBoxLayout, QWidget, QLabel, QComboBox, QListWidget, QDialogButtonBox

import app
import appsettings
import apputils
import views
from app.views import ViewType
from database import dbutils
from database.dbutils import DatabaseType, Database


class DatabaseSaveModal(QDialog):
    def __init__(self, parent, database: Database, save_mode: str):
        super().__init__(parent)
        self.db = database
        self.save_mode = save_mode

        self.db_name = QLineEdit()
        self.db_type = QComboBox()

        self.db_unregistered_path = QLineEdit()
        self.db_unregistered_path_button = QPushButton("...")
        self.db_unregistered_path_select = QWidget()

        self.db_paths = QListWidget()
        self.db_views = QListWidget()

        self._init_ui()
        self._db_type_changed()
        if database is not None:
            app.logger.debug(f"Loading view for database {database}")
            self.load_database(database)

    def _init_ui(self):
        rx = QRegularExpression("^[a-zA-z0-9_-]+$")
        self.db_name.setPlaceholderText("Database Name")
        self.db_name.setValidator(QRegularExpressionValidator(rx))

        self.db_unregistered_path_button.clicked.connect(self._db_path_selection_button_press)
        self.db_unregistered_path.setReadOnly(True)
        db_path_selector_layout = QHBoxLayout()
        db_path_selector_layout.setContentsMargins(0, 0, 0, 0)
        db_path_selector_layout.addWidget(self.db_unregistered_path, 90)
        db_path_selector_layout.addWidget(self.db_unregistered_path_button, 10)
        self.db_unregistered_path_select.setLayout(db_path_selector_layout)

        db_type_description = QLabel(f"<p> </p><p><b>About Database Types...</b></p>"
                                     f"<p>A registered database will be stored in {app.__APP_NAME__}'s internal "
                                     f"library, so that it is always accessible.</p>"
                                     f"<p>An unregistered database is stored in a location of your choice "
                                     f"(like a removable disk), and can be opened if {app.__APP_NAME__} "
                                     f"can discover that location.")
        db_type_description.setWordWrap(True)

        self.db_type.setEditable(False)
        self.db_type.addItems([v for v in DatabaseType])
        self.db_type.currentTextChanged.connect(self._db_type_changed)
        type_and_description_layout = QVBoxLayout()
        type_and_description_layout.addWidget(self.db_type, 50)
        type_and_description_layout.addWidget(self.db_unregistered_path_select)
        type_and_description_layout.addWidget(db_type_description, 50)

        gb = QGroupBox("Select Database Type")
        gb.setLayout(type_and_description_layout)

        list_layout = QHBoxLayout()
        # TODO: Make this style dependent
        self.db_paths.setIconSize(QSize(16, 16))
        self.db_views.setIconSize(QSize(16, 16))
        list_layout.addWidget(self.db_paths, 70)
        # list_layout.addWidget(self.db_views, 30)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Save,
                                   Qt.Orientation.Horizontal, self)
        buttons.rejected.connect(self.close)
        buttons.accepted.connect(self._save_action_triggered)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.db_name)
        main_layout.addWidget(gb)
        main_layout.addLayout(list_layout)
        main_layout.addWidget(buttons)

        self.setLayout(main_layout)
        self.setWindowIcon(QIcon("medialib-icon"))
        self.setWindowTitle(self.save_mode)

    def load_database(self, database: Database):
        def path_icon_provider(path):
            icon_name = views.get_mime_type_icon_name(path)
            return views.get_mime_type_icon(icon_name)

        def view_icon_provider(view_name):
            return QIcon.fromTheme(ViewType[view_name].icon)

        def make_checkable(list_widget, icon_provider=None):
            for i in range(list_widget.count()):
                entry = list_widget.item(i)
                entry.setFlags(entry.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                entry.setCheckState(Qt.CheckState.Checked)
                if icon_provider is not None:
                    entry.setIcon(icon_provider(entry.text()))

        if not database.is_default:
            self.db_name.setText(database.name)

        self.db_type.setCurrentText(database.type)

        self.db_paths.addItems(database.paths)
        make_checkable(self.db_paths, path_icon_provider)

        self.db_views.addItems([v.name for v in ViewType])
        make_checkable(self.db_views, view_icon_provider)

    def _save_action_triggered(self):
        paths = []
        for i in range(self.db_paths.count()):
            entry = self.db_paths.item(i)
            if entry.checkState() == Qt.CheckState.Checked:
                paths.append(entry.text())

        db_type = DatabaseType(self.db_type.currentText())
        if db_type == DatabaseType.UNREGISTERED:
            save_path = self.db_unregistered_path.text()
        else:
            save_path = str(appsettings.get_registry_dir() / self.db_name.text())

        try:
            app.logger.info(f"Creating a {db_type.value} database {self.db_name.text()} with {len(paths)} paths")
            save_db = Database(
                is_default=False,
                database_type=db_type,
                save_path=save_path,
                database_name=self.db_name.text(),
                paths=paths,
                views=[ViewType.JSON]
            )
            app.logger.info(f"Saving database")
            save_db.save()
            if save_db.type == DatabaseType.REGISTERED:
                app.logger.info("Registering database")
                dbutils.get_registry().add(save_db)
                dbutils.get_registry().commit()
            app.logger.info(f"Complete")
        except ValueError as v:
            apputils.show_exception(parent=self, exception=v)

    def _db_type_changed(self):
        app.logger.debug(f"DB type changed to {self.db_type.currentText()}")
        self.db_unregistered_path_select.setVisible(
            DatabaseType(self.db_type.currentText()) == DatabaseType.UNREGISTERED)

    def _db_path_selection_button_press(self):
        db_dir = apputils.get_new_paths(self, is_dir=True)
        if len(db_dir):
            app.logger.debug(f"Database save path changed to {db_dir[0]}")
            self.db_unregistered_path.setText(db_dir[0])


if __name__ == '__main__':
    import sys

    xapp = QApplication(sys.argv)

    ex = DatabaseSaveModal(None, Database.create_default(
        ["/home/sheldon/.cddb",
         "/mnt/dev/testing",
         "/mnt/dev/art-of-being",
         "/home/sheldon/Downloads/art-of-being/images/slider-img3.jpg"
         ]), save_mode="sds")
    ex.show()
    sys.exit(xapp.exec())
