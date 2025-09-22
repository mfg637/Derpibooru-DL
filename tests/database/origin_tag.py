import unittest

import database
import copy
from datetime import datetime


class TestOriginTagBuilder(unittest.TestCase):

    def setUp(self):
        self.builder = database.origin_tag.OriginTagBuilder()
        self.builder.origin_name = database.origin_tag.OriginNameType.DERPIBOORU
        self.builder.origin_id = 123
        self.builder.tag_name = "test_tag"
        self.builder.tag_slug = "test_tag"
        self.builder.description = "test_desc"
        self.builder.short_description = "test_short_desc"
        self.builder.category = "test_cat"
        self.builder.tag_id = 456
        self.builder.last_update = datetime.now()

    def test_build_with_all_valid_data(self):
        try:
            result = self.builder.build()
            self.assertIsInstance(result, database.origin_tag.OriginTag)
        except TypeError as e:
            self.fail(f"build() raised TypeError unexpectedly: {e}")

    def test_build_without_optional_data(self):
        my_builder = copy.copy(self.builder)
        my_builder.tag_slug = None
        my_builder.description = None
        my_builder.short_description = None
        my_builder.category = None
        my_builder.last_update = None
        try:
            result = my_builder.build()
            self.assertIsInstance(result, database.origin_tag.OriginTag)
        except TypeError as e:
            self.fail(f"build() raised TypeError unexpectedly: {e}")

    def test_build_raises_type_error_for_origin_name(self):
        my_builder = copy.copy(self.builder)
        my_builder.origin_name = "invalid_type"
        with self.assertRaises(TypeError) as cm:
            my_builder.build()
            self.assertIn(
                "OriginTagBuilder.origin_name is not OriginNameType",
                str(cm.exception),
            )

    def test_build_raises_type_error_for_origin_id(self):
        my_builder = copy.copy(self.builder)
        my_builder.origin_id = "invalid_type"
        with self.assertRaises(TypeError) as cm:
            my_builder.build()
            self.assertIn(
                "OriginTagBuilder.origin_id is not an integer",
                str(cm.exception),
            )

    def test_build_raises_type_error_for_tag_name(self):
        my_builder = copy.copy(self.builder)
        my_builder.tag_name = 123
        with self.assertRaises(TypeError) as cm:
            my_builder.build()
            self.assertIn(
                "OriginTagBuilder.tag_name is not string", str(cm.exception)
            )

    def test_build_raises_type_error_for_tag_slug(self):
        my_builder = copy.copy(self.builder)
        my_builder.tag_slug = 123
        with self.assertRaises(TypeError) as cm:
            my_builder.build()
            self.assertIn(
                "OriginTagBuilder.tag_slug must be string or None",
                str(cm.exception),
            )

    def test_build_raises_type_error_for_description(self):
        my_builder = copy.copy(self.builder)
        my_builder.description = 123
        with self.assertRaises(TypeError) as cm:
            my_builder.build()
            self.assertIn(
                "OriginTagBuilder.description must be string or None",
                str(cm.exception),
            )

    def test_build_raises_type_error_for_short_description(self):
        my_builder = copy.copy(self.builder)
        my_builder.short_description = 123
        with self.assertRaises(TypeError) as cm:
            my_builder.build()
            self.assertIn(
                "OriginTagBuilder.short_description must be string or None",
                str(cm.exception),
            )

    def test_build_raises_type_error_for_category(self):
        my_builder = copy.copy(self.builder)
        my_builder.category = 123
        with self.assertRaises(TypeError) as cm:
            my_builder.build()
            self.assertIn(
                "OriginTagBuilder.category must be string or None",
                str(cm.exception),
            )

    def test_build_raises_type_error_for_tag_id(self):
        my_builder = copy.copy(self.builder)
        my_builder.tag_id = "invalid_type"
        with self.assertRaises(TypeError) as cm:
            my_builder.build()
            self.assertIn(
                "OriginTagBuilder.tag_id is not an integer",
                str(cm.exception),
            )

    def test_build_raises_type_error_for_last_update(self):
        my_builder = copy.copy(self.builder)
        my_builder.last_update = "invalid_type"
        with self.assertRaises(TypeError) as cm:
            my_builder.build()
            self.assertIn(
                "OriginTagBuilder.last_update must be datetime or None",
                str(cm.exception),
            )


class TestOriginTagTable(unittest.TestCase):
    def setUp(self):
        self.connection = database.make_connection(
            database.DatabaseEnum.APP_TEST
        )
        self.tag_1_id = database.tag.add_tag(
            self.connection,
            "Twilight Sparkle (MLP)",
            database.tag.TagCategory.CHARACTER,
        )
        self.tag_2_id = database.tag.add_tag(
            self.connection, "alicorn", database.tag.TagCategory.SPECIES
        )

    def test_combined(self):
        tag_1_derpibooru_builder = database.origin_tag.OriginTagBuilder()
        derpibooru_origin = database.origin_tag.OriginNameType.DERPIBOORU
        tag_1_derpibooru_builder.origin_name = derpibooru_origin
        tag_1_derpibooru_builder.origin_id = 123
        tag_1_derpibooru_builder.tag_name = "twilight sparkle"
        tag_1_derpibooru_builder.tag_id = self.tag_1_id
        tag_1_derpibooru = tag_1_derpibooru_builder.build()
        database.origin_tag.add_origin_tag(self.connection, tag_1_derpibooru)
        tag_1_derpibooru_test = database.origin_tag.get_by_tag_name(
            self.connection, derpibooru_origin, "twilight sparkle"
        )
        self.assertIsNotNone(tag_1_derpibooru_test)
        tag_1_e621_builder = database.origin_tag.OriginTagBuilder()
        e621_origin = database.origin_tag.OriginNameType.E621
        tag_1_e621_builder.origin_name = e621_origin
        tag_1_e621_builder.origin_id = 456
        tag_1_e621_builder.tag_name = "twilight sparkle (mlp)"
        tag_1_e621_builder.tag_id = self.tag_1_id
        tag_1_e621 = tag_1_e621_builder.build()
        database.origin_tag.add_if_not_exists(self.connection, tag_1_e621)
        tag_1_e621_test = database.origin_tag.get_by_origin_id(
            self.connection, e621_origin, 456
        )
        self.assertIsNotNone(tag_1_e621_test)
        tag_1_test_list = database.origin_tag.get_by_tag_id(
            self.connection, self.tag_1_id
        )
        self.assertEqual(len(tag_1_test_list), 2)

    def test_tag_id_not_exists(self):
        test_record_builder = database.origin_tag.OriginTagBuilder()
        test_record_builder.origin_name = (
            database.origin_tag.OriginNameType.DERPIBOORU
        )
        test_record_builder.origin_id = 789
        test_record_builder.tag_name = "this record should not exists"
        test_record_builder.tag_id = 99999
        test_record = test_record_builder.build()
        with self.assertRaises(ValueError) as e:
            database.origin_tag.add_origin_tag(self.connection, test_record)
            self.assertIn(
                f"Tag with ID = {test_record.tag_id} does not exists",
                str(e.exception),
            )

    def test_clear_table(self):
        tag_2_derpibooru_builder = database.origin_tag.OriginTagBuilder()
        derpibooru_origin = database.origin_tag.OriginNameType.DERPIBOORU
        tag_2_derpibooru_builder.origin_name = derpibooru_origin
        tag_2_derpibooru_builder.origin_id = 987
        tag_2_derpibooru_builder.tag_name = "alicorn"
        tag_2_derpibooru_builder.tag_id = self.tag_2_id
        tag_2_derpibooru = tag_2_derpibooru_builder.build()
        database.origin_tag.add_origin_tag(self.connection, tag_2_derpibooru)
        tag_2_e621_builder = database.origin_tag.OriginTagBuilder()
        e621_origin = database.origin_tag.OriginNameType.E621
        tag_2_e621_builder.origin_name = e621_origin
        tag_2_e621_builder.origin_id = 654
        tag_2_e621_builder.tag_name = "winged unicorn"
        tag_2_e621_builder.tag_id = self.tag_2_id
        tag_2_e621 = tag_2_e621_builder.build()
        database.origin_tag.add_if_not_exists(self.connection, tag_2_e621)
        database.origin_tag.clear_table(self.connection)
        test_tag_2_list = database.origin_tag.get_by_tag_id(
            self.connection, self.tag_2_id
        )
        self.assertListEqual(test_tag_2_list, [])

    def tearDown(self):
        database.origin_tag.clear_table(self.connection)
        database.tag.clear_table(self.connection)
        self.connection.close()
