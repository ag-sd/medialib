import unittest
from unittest import skip

from PyQt6.QtTest import QTest

import app.tasks as dispatcher


class ThreadPoolTester(unittest.TestCase):

    def setUp(self):
        self._result_collector = []

    def rez_coll(self, result):
        self._result_collector.append(result)

    @skip("Run this test manually outside of pytest")
    def test_simple_threadpool(self):
        def runnable_func(_id):
            print("I have started")
            QTest.qWait(10000)
            print("I am Complete")
            return _id

        num_jobs = 1000
        runner = dispatcher.TaskManager(None)
        for i in range(0, num_jobs):
            runner.start_task("test-task", runnable_func, {"_id": 1})
