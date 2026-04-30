import unittest
import database


class TestTagOperations(unittest.TestCase):
    def setUp(self):
        self.connection = database.make_connection(
            database.DatabaseEnum.APP_TEST
        )

    def test_insert(self):
        tag_id = database.tag.add_tag(
            self.connection,
            "simple background",
            database.tag.TagCategory.CONTENT,
        )
        self.assertIsNotNone(tag_id)

    def test_get(self):
        tag_name = "gradient background"
        tag_category = database.tag.TagCategory.CONTENT
        tag_id = database.tag.add_tag(
            self.connection,
            tag_name,
            tag_category,
        )
        self.assertIsNotNone(tag_id)
        tag_1 = database.tag.get_tag_by_id(self.connection, tag_id)
        self.assertEqual(tag_1.id, tag_id)
        tag_2 = database.tag.get_tag_by_name_and_category(
            self.connection, tag_name, tag_category
        )
        self.assertEqual(tag_name, tag_2.name)
        self.assertEqual(tag_category, tag_2.category)
        self.assertEqual(tag_id, tag_2.id)

    def test_clear_table(self):
        database.tag.add_tag(
            self.connection,
            "a",
            database.tag.TagCategory.CONTENT,
        )
        database.tag.add_tag(
            self.connection,
            "b",
            database.tag.TagCategory.CONTENT,
        )
        database.tag.add_tag(
            self.connection,
            "c",
            database.tag.TagCategory.CONTENT,
        )
        database.tag.add_tag(
            self.connection,
            "d",
            database.tag.TagCategory.CONTENT,
        )
        database.tag.clear_table(self.connection)
        tag_id = database.tag.add_tag(
            self.connection,
            "f",
            database.tag.TagCategory.CONTENT,
        )
        self.assertEqual(tag_id, 1)

    def test_get_or_add(self):
        tag_1_id1 = database.tag.add_tag(
            self.connection,
            "a",
            database.tag.TagCategory.CONTENT,
        )
        tag_1_id2 = database.tag.get_or_create_tag_id(
            self.connection,
            "a",
            database.tag.TagCategory.CONTENT,
        )
        self.assertEqual(tag_1_id1, tag_1_id2)
        tag_2_id = database.tag.get_or_create_tag_id(
            self.connection,
            "b",
            database.tag.TagCategory.CONTENT,
        )
        self.assertIsNotNone(tag_2_id)

    def test_tag_not_exists(self):
        tag_1 = database.tag.get_tag_by_id(self.connection, 99999)
        self.assertIsNone(tag_1)
        tag_2 = database.tag.get_tag_by_name_and_category(
            self.connection,
            "this tag is not exists",
            database.tag.TagCategory.CONTENT,
        )
        self.assertIsNone(tag_2)

    def tearDown(self):
        database.tag.clear_table(self.connection)
        self.connection.close()
