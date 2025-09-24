import unittest
import database


class TestDerpibooruDumpDB(unittest.TestCase):
    def setUp(self):
        self.connection = database.make_connection(
            database.DatabaseEnum.DERPIBOORU
        )

    def test_content_exists(self):
        positive_check_test = database.derpibooru.check_image_exists(
            self.connection, 1
        )
        self.assertTrue(positive_check_test)
        negative_check_test = database.derpibooru.check_image_exists(
            self.connection, 999999999999999
        )
        self.assertFalse(negative_check_test)

    def test_duplicates(self):
        target_id_expected = database.derpibooru.check_duplicates(
            self.connection, 26148
        )
        self.assertEqual(target_id_expected, 3627151)
        none_expected = database.derpibooru.check_duplicates(self.connection, 1)
        self.assertIsNone(none_expected)

    def test_is_image_hidden(self):
        positive_check_test = database.derpibooru.is_image_hidden(
            self.connection, 1158660
        )
        self.assertTrue(positive_check_test)
        negative_check_test = database.derpibooru.is_image_hidden(
            self.connection, 1
        )
        self.assertFalse(negative_check_test)

    def test_get_image(self):
        my_image = database.derpibooru.get_image_by_id(self.connection, 1)
        image_hash_hex = "f16c98e2848c2f1bfff3985e8f1a54375cc49f78125391aeb80534ce011ead14e3e452a5c4bc98a66f56bdfcd07ef7800663b994f3f343c572da5ecc22a9660f"
        if my_image is None:
            raise ValueError("Unexpected None")
        self.assertEqual(my_image.image_sha512_hash, image_hash_hex)

    def test_get_tag_by_id(self):
        existing_tag = database.derpibooru.get_tag_by_id(self.connection, 3)
        if existing_tag is None:
            raise ValueError("Unexpected None")
        self.assertEqual(existing_tag.name, ":<")
        non_existing_tag = database.derpibooru.get_tag_by_id(self.connection, 1)
        self.assertIsNone(non_existing_tag)

    def test_get_tag_by_name(self):
        tag_1 = database.derpibooru.get_tag_by_name(
            self.connection, "twilight sparkle"
        )
        if tag_1 is None:
            raise ValueError("Unexpected None")
        self.assertEqual(tag_1.id, 46192)
        not_existing_tag = database.derpibooru.get_tag_by_name(
            self.connection, "this tag does not exists"
        )
        self.assertIsNone(not_existing_tag)

    def test_get_image_tags(self):
        tags_list = database.derpibooru.get_tags_of_image(self.connection, 1540)
        self.assertAlmostEqual(len(tags_list), 20, delta=5)

    def tearDown(self):
        self.connection.close()
