import datetime
import logging
import queue
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


class JobStatus(StrEnum):
    STARTED = "STARTED"
    WAITING = "WAITING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class CommandSignals(QObject):
    status = pyqtSignal("PyQt_PyObject")
    thread_complete = pyqtSignal("PyQt_PyObject")
    log_message = pyqtSignal("PyQt_PyObject")


class Job(QRunnable):
    def __init__(self, task_name, function, **kwargs):
        super().__init__()
        self._function = function
        self._kwargs = kwargs
        self._id = task_name
        self.signals = CommandSignals()

    def run(self):
        start_time = datetime.datetime.now()
        try:
            self.signals.status.emit({
                "id": self._id,
                "status": JobStatus.STARTED,
            })
            result = self._function(**self._kwargs)
            end_time = datetime.datetime.now()
        except Exception as e:
            end_time = datetime.datetime.now()
            self.signals.status.emit({
                "id": self._id,
                "status": JobStatus.FAILED,
                "time": (end_time - start_time).total_seconds(),
                "exception": e
            })
        else:
            self.signals.status.emit({
                "id": self._id,
                "status": JobStatus.COMPLETED,
                "time": (end_time - start_time).total_seconds(),
                "result": result
            })  # Return the result of the processing
        finally:
            self.signals.thread_complete.emit(self._id)


def _start_jobs(jobs: list):
    _threadpool = QThreadPool.globalInstance()
    app.logger.debug(f"Multithreading with maximum {_threadpool.maxThreadCount()} threads")
    for job in jobs:
        _threadpool.start(job)


class JobManager(QWidget):

    work_complete = pyqtSignal(str)

    def __init__(self, parent):
        super().__init__(parent=parent)
        self._job_queue = queue.Queue()
        self._progressbar = QProgressBar()
        self._progressbar.setMinimum(0)
        self._progressbar.setMaximum(0)
        self._logger = _create_logger(self.__class__.__name__)

    def _init_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._progressbar)
        self.setLayout(layout)

    def _job_status(self, status):
        self._logger.debug(f"Received status message from job {status}")

    def _thread_complete(self, task_name):
        self._job_queue.get()
        if self._job_queue.qsize() > 0:
            self._logger.debug(f"Received Job completion notice. Remaining jobs {self._job_queue.qsize()}")
        else:
            self._logger.debug("All jobs finished.")
            self._progressbar.setVisible(False)
        self.work_complete.emit(task_name)


    def start_job(self, job: Job):
        job.signals.status.connect(self._job_status)
        job.signals.thread_complete.connect(self._thread_complete)
        self._job_queue.put(job)
        self._progressbar.setVisible(True)
        _start_jobs([job])

    def do_work(self, task_name, work_func, kwargs=None):
        job = Job(task_name, work_func, **kwargs)
        job.signals.status.connect(self._job_status)
        job.signals.thread_complete.connect(self._thread_complete)
        self._job_queue.put(job)
        self._progressbar.setVisible(True)
        _start_jobs([job])

