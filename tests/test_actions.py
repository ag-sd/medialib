import unittest


class TestActions(unittest.TestCase):
    pass

    # https://github.com/jmcgeheeiv/pyqttestexample/blob/master/src/MargaritaMixerTest.py

    # def test_create_action_missing_fields(self):
    #     i1 = actions._create_action(None, "Test1")
    #     self.assertTrue(i1.text() == "Test1")
    #
    #     # If action has tooltip and shortcut, these are set at multiple places
    #     i2 = actions._create_action(None, "Test2", func=None, shortcut="X", tooltip="TOOLTIP")
    #     self.assertTrue(i2.toolTip() == "TOOLTIP (X)")
    #     self.assertTrue(i2.toolTip() == "TOOLTIP (X)")
    #     self.assertTrue(i2.statusTip() == "TOOLTIP (X)")
    #     self.assertTrue(i2.shortcut() == "X")
    #
    #     # If no shortcut is set, the tooltip does not show this
    #     i2 = actions._create_action(None, "Test2", func=None, shortcut=None, tooltip="TOOLTIP")
    #     self.assertTrue(i2.toolTip() == "TOOLTIP")
    #     self.assertTrue(i2.toolTip() == "TOOLTIP")
    #     self.assertTrue(i2.statusTip() == "TOOLTIP")
    #     self.assertTrue(i2.shortcut() is None)
