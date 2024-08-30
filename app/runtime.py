import datetime
import logging
import uuid
from enum import StrEnum

from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, QThreadPool

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


class JobRunner(QRunnable):
    def __init__(self, function, command_id=None, **kwargs):
        super().__init__()
        self._function = function
        self._kwargs = kwargs
        self._id = str(command_id if command_id is not None else uuid.uuid1())
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


def run_jobs(jobs: list):
    _threadpool = QThreadPool.globalInstance()
    app.logger.debug(f"Multithreading with maximum {_threadpool.maxThreadCount()} threads")
    for job in jobs:
        _threadpool.start(job)
