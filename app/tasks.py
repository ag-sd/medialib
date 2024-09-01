import datetime
import logging
import queue
from dataclasses import dataclass
from enum import StrEnum

from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, QThreadPool
from PyQt6.QtWidgets import QWidget, QProgressBar, QHBoxLayout

import app


def _create_logger(app_name: str):
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - '
                                  '%(module)s:[%(funcName)s]:%(lineno)s - %(message)s')
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)
    logger = logging.getLogger(app_name)
    logger.addHandler(ch)
    logger.setLevel(logging.DEBUG)
    return logger


class TaskStatus(StrEnum):
    STARTED = "STARTED"
    WAITING = "WAITING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class Task:
    id: str
    args: dict
    status: TaskStatus
    time_taken: float
    result: ...
    error: ...


class TaskWorkerSignals(QObject):
    status = pyqtSignal("PyQt_PyObject")
    thread_complete = pyqtSignal("PyQt_PyObject")
    log_message = pyqtSignal("PyQt_PyObject")


class TaskWorker(QRunnable):
    def __init__(self, task_name, function, **kwargs):
        super().__init__()
        self._function = function
        self._kwargs = kwargs
        self._id = task_name
        self.signals = TaskWorkerSignals()
        self._status_message_template = {
            "id": self._id,
            "args": self._kwargs
        }

    def run(self):
        start_time = datetime.datetime.now()
        runtime = -1
        task_status = TaskStatus.WAITING
        error = None
        result = None
        try:
            task_status = TaskStatus.STARTED
            result = self._function(**self._kwargs)
        except Exception as e:
            task_status = TaskStatus.FAILED
            runtime = (datetime.datetime.now() - start_time).total_seconds()
            error = e
        else:
            task_status = TaskStatus.COMPLETED
            runtime = (datetime.datetime.now() - start_time).total_seconds()
        finally:
            self.signals.thread_complete.emit(self._get_task(task_status, runtime, result, error))

    def _get_task(self, status: TaskStatus, time: float = -1, result=None, error=None):
        return Task(id=self._id, status=status, time_taken=time, result=result, error=error, args=self._kwargs)


def _start_tasks(tasks: list):
    _threadpool = QThreadPool.globalInstance()
    app.logger.debug(f"Multithreading with maximum {_threadpool.maxThreadCount()} threads")
    for task in tasks:
        _threadpool.start(task)


class TaskManager(QWidget):
    work_complete = pyqtSignal(Task)

    def __init__(self, parent):
        super().__init__(parent=parent)
        self._tasks_queue = queue.Queue()
        self._progressbar = QProgressBar()
        self._progressbar.setMinimum(0)
        self._progressbar.setMaximum(0)
        self._logger = _create_logger(self.__class__.__name__)
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._progressbar)
        self._progressbar.setVisible(False)
        self.setLayout(layout)

    def _task_status(self, status):
        self._logger.debug(f"Received status message from task {status}")

    def _thread_complete(self, task):
        self._tasks_queue.get()
        if self._tasks_queue.qsize() > 0:
            self._logger.debug(f"Received task completion notice. Remaining tasks {self._tasks_queue.qsize()}")
        else:
            self._logger.debug("All tasks finished.")
            self._progressbar.setVisible(False)
        self.work_complete.emit(task)

    def start_task(self, task_name, work_func, kwargs=None):
        tasks = TaskWorker(task_name, work_func, **kwargs)
        tasks.signals.thread_complete.connect(self._thread_complete)
        self._tasks_queue.put(tasks)
        self._progressbar.setVisible(True)
        _start_tasks([tasks])

    @property
    def active_tasks(self):
        return self._tasks_queue.qsize()
