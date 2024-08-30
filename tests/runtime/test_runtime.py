import unittest

from PyQt6.QtTest import QTest

import app.runtime as dispatcher


class ThreadPoolTester(unittest.TestCase):

    def setUp(self):
        self._result_collector = []

    def rez_coll(self, result):
        self._result_collector.append(result)

    def test_simple_threadpool(self):
        def runnable_func(_id):
            print("I have started")
            QTest.qWait(10000)
            print("I am Complete")
            return _id

        def status(result):
            self._result_collector.append(result)
            print("Status message received")

        num_jobs = 1000
        jobs = []
        for i in range(0, num_jobs):
            job = dispatcher.JobRunner(runnable_func, f"job:{i}", _id=i)
            job.signals.status.connect(self.rez_coll)
            jobs.append(job)
        runner = dispatcher.JobDispatcher(jobs)
        runner.start()

        # self.assertTrue(QThreadPool.globalInstance().waitForDone(-1))
        # self.assertEqual(num_jobs, len(self._result_collector))
        print("Done")
