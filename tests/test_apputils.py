import unittest

from app import apputils
from app.collection import props


class TestAppUtils(unittest.TestCase):

    def test_mime_type_icon_name(self):
        self.assertEqual("text-plain", apputils.get_mime_type_icon_name("foo.txt"))
        self.assertEqual("image-jpeg", apputils.get_mime_type_icon_name("foo.jpg"))
        self.assertEqual("image-png", apputils.get_mime_type_icon_name("foo.png"))
        self.assertEqual("video-mp4", apputils.get_mime_type_icon_name("foo.mp4"))
        self.assertEqual("audio-mpeg", apputils.get_mime_type_icon_name("foo.mp3"))

    def test_create_tag_groups(self):
        tags = ["a", "b:1", "b:2", "c", "d:1", "e:1:2"]
        groups = apputils.create_tag_groups(tags)

        self.assertListEqual(['ROOT', 'b', 'd'], list(groups.keys()))
        self.assertTrue(props.DB_TAG_GROUP_DEFAULT in groups)
        self.assertEqual(['a', 'c'], groups[props.DB_TAG_GROUP_DEFAULT])
        self.assertEqual(['1', '2'], groups["b"])
        self.assertEqual(['1'], groups["d"])
