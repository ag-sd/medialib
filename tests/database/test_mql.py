import unittest
from pathlib import Path

from app.database import mql
from app.database.mql import QueryException

TEST_IMPLEMENTED_OPERATIONS_ONLY = True


class TestMQL(unittest.TestCase):
    TEST_INPUT = str(Path(__file__).parent.parent / "resources" / "test_db_data.json")

    def test_simple_select_no_where(self):
        query = "select * From Database"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertTrue(len(response) == 15)

    def test_unary_where(self):
        query = "select * from Database where 1-1=0"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertTrue(len(response) == 15)

    def test_unary_false(self):
        query = "select * from Database where 1-1=01"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertTrue(len(response) == 0)

    def test_field_check(self):
        query = "select * from Database where \"File:ImageHeight\" > 2315"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertTrue(len(response) == 3)

    def test_field_qualified_name_check(self):
        query = 'select * from Database where "File:ImageHeight" > 2315'
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertTrue(len(response) == 3)

    def test_field_with_and(self):
        query = 'select * from Database where "File:ImageHeight" == 256 and "File:ImageWidth" == 256'
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertTrue(len(response) == 1)

    def test_field_with_or(self):
        query = 'select * from Database where "File:ImageHeight" == 256 or "File:ImageWidth" == 3024'
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertTrue(len(response) == 2)

    def test_in_clause_nums(self):
        query = "select * from Database where \"File:ImageHeight\" in (256, 1500)"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertTrue(len(response) == 3)

    def test_in_clause_expr(self):
        query = "select * from Database where \"File:ImageHeight\" in (16 * 16, 1600 - 100)"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertTrue(len(response) == 3)

    def test_in_clause_strings(self):
        query = "select SourceFile from Database where \"System:FileSize\" in ('139 kB', '179 kB')"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertEqual(len(response), 2)

    def test_not_in_clause_strings(self):
        query = "select SourceFile from Database where \"System:FileSize\" not in ('139 kB', '179 kB')"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertTrue(len(response) == 13)

    def test_between_clause(self):
        query = "select * from Database where \"File:ImageHeight\" between 256, 1500"
        self.assertRaises(QueryException, mql.query_file, query, self.TEST_INPUT)

    def test_select_single_field_operation(self):
        query = "select \"SourceFile\" from Database"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertEqual(len(response), 15)
        for ele in response:
            self.assertEqual(len(ele), 1)
            self.assertTrue("SourceFile" in ele)

    def test_case_change_for_unquoted_fields(self):
        """
        Unquoted fields are lower cased, so they may not be found in the database
        """
        query = "select SourceFile from Database"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertEqual(len(response), 15)
        for ele in response:
            self.assertEqual(len(ele), 1)
            self.assertTrue("sourcefile" in ele)
            self.assertIsNone(ele["sourcefile"])

    def test_aliased_stars_will_fail_syntax_error(self):
        query = "select x.* from database"
        self.assertRaises(QueryException, mql.query_file, query, self.TEST_INPUT)

    def test_qualified_field_names(self):
        """
        Unquoted fields are lower cased, so they may not be found in the database
        """
        query = "select x.SourceFile from Database"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertEqual(len(response), 15)
        for ele in response:
            self.assertEqual(len(ele), 1)
            self.assertTrue("sourcefile" in ele)
            self.assertIsNone(ele["sourcefile"])

    def test_quoted_field_names(self):
        """
        Unquoted fields are lower cased, so they may not be found in the database
        """
        query = "select SourceFile from Database"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertEqual(len(response), 15)

    def test_field_unquoted_alias(self):
        """
        Unquoted aliases are lowercased
        """
        query = "select SourceFile as File, \"System:FileSize\" as size, " \
                "\"File:ImageWidth\" as width, \"File:ImageHeight\" as height from Database"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertEqual(len(response), 15)
        for ele in response:
            self.assertEqual(len(ele), 4)
            self.assertTrue("file" in ele)
            self.assertTrue("size" in ele)
            self.assertTrue("width" in ele)
            self.assertTrue("height" in ele)

    def test_field_quoted_alias(self):
        query = "select SourceFile as 'File', \"System:FileSize\" as 'SizE', " \
                "\"File:ImageWidth\" as width, \"File:ImageHeight\" as height from Database"
        self.assertRaises(QueryException, mql.query_file, query, self.TEST_INPUT)

    def test_regexp_match(self):
        query = "Select \"SourceFile\" as file from Database where \"SourceFile\" regexp '.*lena.*'"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertEqual(len(response), 9)
        for ele in response:
            name = ele["file"]
            # Note: Case Insensitive search
            self.assertTrue("lena" in name or "Lena" in name)

    def test_regexp_not_match(self):
        query = "Select \"SourceFile\" as file from Database where \"SourceFile\" not regexp '.*lena.*'"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertEqual(len(response), 6)
        for ele in response:
            name = ele["file"]
            self.assertTrue("lena" not in name)

    def test_like_operation_ends_with(self):
        query = "Select SourceFile as file, \"File:FileType\" as type " \
                "from Database where \"File:FileType\" like '%g'"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertEqual(len(response), 10)
        for ele in response:
            _type = ele["type"]
            self.assertTrue("JPEG" == _type or "PNG" == _type)

    def test_like_operation_starts_with_and_ends_with(self):
        query = "Select SourceFile as file, \"File:FileType\" as type " \
                "from Database where \"File:FileType\" like 'j%g'"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertEqual(len(response), 8)
        for ele in response:
            _type = ele["type"]
            self.assertTrue("JPEG" == _type)

    def test_like_operation_contains(self):
        query = "Select SourceFile as file, \"File:FileType\" as type " \
                "from Database where \"File:FileType\" like '%n%'"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertEqual(len(response), 2)
        for ele in response:
            _type = ele["type"]
            self.assertTrue("PNG" == _type)

    def test_like_operation_fixed_len(self):
        query = "Select SourceFile as file, \"File:FileType\" as type " \
                "from Database where \"File:FileType\" like '___'"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertEqual(len(response), 4)
        for ele in response:
            _type = ele["type"]
            self.assertTrue("PNG" == _type or "GIF" == _type)

    def test_like_combination_with_positional(self):
        query = "Select SourceFile as file, \"File:FileType\" as type " \
                "from Database where \"File:FileType\" like '%if_'"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertEqual(len(response), 3)
        for ele in response:
            _type = ele["type"]
            self.assertTrue("TIFF" == _type)

    def test_like_exact_match(self):
        query = "Select SourceFile as file, \"File:FileType\" as type " \
                "from Database where \"File:FileType\" like 'GIF'"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertEqual(len(response), 2)
        for ele in response:
            _type = ele["type"]
            self.assertTrue("GIF" == _type)

    def test_is_operator_basic(self):
        query = "Select SourceFile as file, \"File:FileType\" as type " \
                "from Database where \"File:FileType\" is 'GIF'"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertEqual(len(response), 2)
        for ele in response:
            _type = ele["type"]
            self.assertTrue("GIF" == _type)

    def test_is_operator_basic_not(self):
        query = "Select SourceFile as file, \"File:FileType\" as type " \
                "from Database where \"File:FileType\" is not 'JPEG'"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertEqual(len(response), 7)
        for ele in response:
            _type = ele["type"]
            self.assertTrue("JPEG" != _type)

    def test_is_null(self):
        query = "Select SourceFile as file, \"File:FileType\" as type, " \
                "\"JFIF:ResolutionUnit\" as jfif from Database where \"JFIF:ResolutionUnit\" is null"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertEqual(len(response), 9)
        for ele in response:
            self.assertIsNone(ele["jfif"])

    def test_is_not_null(self):
        query = "Select SourceFile as file, \"File:FileType\" as type, " \
                "\"JFIF:ResolutionUnit\" as jfif from Database where \"JFIF:ResolutionUnit\" is not null"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertEqual(len(response), 6)
        for ele in response:
            self.assertIsNotNone(ele["jfif"])

    def test_is_true(self):
        query = "Select SourceFile as file, mature_content as content " \
                "from Database where \"mature_content\" is true"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertEqual(len(response), 5)
        for ele in response:
            self.assertTrue(ele["content"])

    def test_is_not_true(self):
        query = "Select SourceFile as file, mature_content as content " \
                "from Database where \"mature_content\" is not true"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertEqual(len(response), 10)
        for ele in response:
            self.assertFalse(ele["content"])

    def test_is_false(self):
        query = "Select SourceFile as file, mature_content as content " \
                "from Database where \"mature_content\" is false"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertEqual(len(response), 10)
        for ele in response:
            self.assertFalse(ele["content"])

    def test_is_not_false(self):
        query = "Select SourceFile as file, mature_content as content " \
                "from Database where \"mature_content\" is not false"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertEqual(len(response), 5)
        for ele in response:
            self.assertTrue(ele["content"])

    def test_between_numbers(self):
        query = 'Select SourceFile as file, "File:ImageWidth" as width ' \
                'from Database where "File:ImageWidth" between 100+100 and 300*2'
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertEqual(len(response), 3)
        for ele in response:
            self.assertTrue((100 + 100) <= ele["width"] <= (300 * 2))

    def test_between_invalid_syntax(self):
        query = 'Select SourceFile as file, mature_content as content ' \
                'from Database where "File:ImageWidth" between 100+100 or 300*2'

        self.assertRaises(QueryException, mql.query_file, query, self.TEST_INPUT)

    def test_not_between_numbers(self):
        query = "Select SourceFile as file, \"File:ImageWidth\" as width " \
                "from Database where \"File:ImageWidth\" not between 257 and 1000"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertEqual(len(response), 11)

    @unittest.skipIf(TEST_IMPLEMENTED_OPERATIONS_ONLY, "Only testing working operations")
    def test_between_dates(self):
        raise NotImplementedError

    @unittest.skipIf(TEST_IMPLEMENTED_OPERATIONS_ONLY, "Only testing working operations")
    def test_not_between_dates(self):
        raise NotImplementedError

    def test_between_text_values(self):
        query = 'Select SourceFile as file, "File:FileType" as format ' \
                "from Database where \"File:FileType\" between 'GIF' and 'PNG'"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertEqual(len(response), 12)
        for ele in response:
            fmt = ele["format"]
            self.assertTrue("JPEG" in fmt or "GIF" in fmt or "PNG" in fmt)

    def test_not_between_text_values(self):
        query = "Select SourceFile as file, \"File:FileType\" as format " \
                "from Database where \"File:FileType\" not between 'GIF' and 'PNG'"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertEqual(len(response), 7)
        for ele in response:
            fmt = ele["format"]
            self.assertTrue("TIFF" in fmt or "GIF" in fmt or "PNG" in fmt)

    def test_distinct(self):
        query = "Select distinct \"File:FileType\" as format from Database"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertEqual(len(response), 4)

    def test_query(self):
        test = "SELECT SourceFile as file where \"identifier with ""quotes"" " \
               "and a trailing space \" IS NOT null -- COMMENT"
        # test = "select x.* from database"
        success, parsed = mql._parser.runTests(test)
        self.assertTrue(success, f"Failed for test {test}")

    def test_limit(self):
        query = "select \"SourceFile\" From Database limit 6"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertTrue(len(response) == 6)

    def test_limit_offset(self):
        query = " Select \"mature_content\" as content " \
                " from Database order by content limit 5 offset 6"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertEqual(len(response), 5)
        self.assertEqual(response[4]['content'], True)


    def test_order_by_multiple(self):
        query = ("select \"JFIF:XResolution\" as rez, \"Composite:Megapixels\" as mp, \"File:FileType\" as type "
                 "From Database order by rez, 2")
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertEqual(response[0]['rez'], None)
        self.assertEqual(response[0]['mp'], 0.198)
        self.assertEqual(response[0]['type'], "PNG")

        self.assertEqual(response[1]['rez'], None)
        self.assertEqual(response[1]['mp'], 0.262)
        self.assertEqual(response[1]['type'], "TIFF")

        self.assertEqual(response[-1]['rez'], 100)
        self.assertEqual(response[-1]['mp'], 2.5)
        self.assertEqual(response[-1]['type'], "JPEG")

        self.assertEqual(response[-2]['rez'], 100)
        self.assertEqual(response[-2]['mp'], 0.342)
        self.assertEqual(response[-2]['type'], "JPEG")

        self.assertEqual(response[9]['rez'], 72)
        self.assertEqual(response[9]['mp'], 0.066)
        self.assertEqual(response[9]['type'], "JPEG")

    def test_order_by_multiple_mixed_order_keys(self):
        query = ("select \"JFIF:XResolution\" as rez, \"Composite:Megapixels\" as mp, \"File:FileType\" as type "
                 "From Database order by rez, 2 desc")
        self.assertRaises(QueryException, mql.query_file, query, self.TEST_INPUT)

    def test_order_by_single_order_key(self):
        query = ("select \"JFIF:XResolution\" as rez, \"Composite:Megapixels\" as mp, \"File:FileType\" as type "
                 "From Database order by rez")
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertEqual(response[0]['rez'], None)
        self.assertEqual(response[0]['mp'], 0.262)
        self.assertEqual(response[0]['type'], "TIFF")

        self.assertEqual(response[1]['rez'], None)
        self.assertEqual(response[1]['mp'], 1.2)
        self.assertEqual(response[1]['type'], "JPEG")

        self.assertEqual(response[-1]['rez'], 100)
        self.assertEqual(response[-1]['mp'], 0.342)
        self.assertEqual(response[-1]['type'], "JPEG")

        self.assertEqual(response[-2]['rez'], 100)
        self.assertEqual(response[-2]['mp'], 2.5)
        self.assertEqual(response[-2]['type'], "JPEG")

    def test_order_by_single_order_key_desc(self):
        query = ("select \"JFIF:XResolution\" as rez, \"Composite:Megapixels\" as mp, \"File:FileType\" as type "
                 "From Database order by rez desc")
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertEqual(response[0]['rez'], 100)
        self.assertEqual(response[0]['mp'], 0.342)
        self.assertEqual(response[0]['type'], "JPEG")

        self.assertEqual(response[1]['rez'], 100)
        self.assertEqual(response[1]['mp'], 2.5)
        self.assertEqual(response[1]['type'], "JPEG")

        self.assertEqual(response[-1]['rez'], None)
        self.assertEqual(response[-1]['mp'], 0.262)
        self.assertEqual(response[-1]['type'], "TIFF")

        self.assertEqual(response[-2]['rez'], None)
        self.assertEqual(response[-2]['mp'], 1.2)
        self.assertEqual(response[-2]['type'], "JPEG")

    def test_order_by_indexes(self):
        query = ("select \"JFIF:XResolution\" as rez, \"Composite:Megapixels\" as mp, \"File:FileType\" as type "
                 "From Database order by 1 desc")
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertEqual(response[0]['rez'], 100)
        self.assertEqual(response[0]['mp'], 0.342)
        self.assertEqual(response[0]['type'], "JPEG")

        self.assertEqual(response[1]['rez'], 100)
        self.assertEqual(response[1]['mp'], 2.5)
        self.assertEqual(response[1]['type'], "JPEG")

        self.assertEqual(response[-1]['rez'], None)
        self.assertEqual(response[-1]['mp'], 0.262)
        self.assertEqual(response[-1]['type'], "TIFF")

        self.assertEqual(response[-2]['rez'], None)
        self.assertEqual(response[-2]['mp'], 1.2)

    def test_order_by_invalid_index(self):
        query = ("select \"JFIF:XResolution\" as rez, \"Composite:Megapixels\" as mp, \"File:FileType\" as type "
                 "From Database order by 20 desc")
        self.assertRaises(QueryException, mql.query_file, query, self.TEST_INPUT)

    def test_order_by_missing_column(self):
        query = ("select \"JFIF:XResolution\" as rez, \"Composite:Megapixels\" as mp, \"File:FileType\" as type "
                 "From Database order by foo desc")
        self.assertRaises(QueryException, mql.query_file, query, self.TEST_INPUT)

    def test_order_by_star(self):
        query = ("select * "
                 "From Database order by \"JFIF:XResolution\" desc")
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertEqual(response[0]['JFIF:XResolution'], 100)
        self.assertEqual(response[2]['JFIF:XResolution'], 72)
        self.assertNotIn('JFIF:XResolution', response[-1])
        self.assertNotIn('JFIF:XResolution', response[-2])

    def test_complex_union_except(self):
        query = " Select \"SourceFile\" as file, \"mature_content\" as content " \
                " from Database where \"mature_content\" is true " \
                " UNION " \
                " Select \"SourceFile\" as file, \"mature_content\" as content " \
                " from Database where \"mature_content\" is false " \
                " EXCEPT " \
                " Select \"SourceFile\" as file, \"mature_content\" as content " \
                " from Database where \"mature_content\" is false "

        response = mql.query_file(query, self.TEST_INPUT)
        self.assertEqual(len(response), 5)
        for ele in response:
            self.assertTrue(ele["content"])

    def test_union(self):
        query = " Select \"SourceFile\" as file, \"mature_content\" as content " \
                " from Database where \"mature_content\" is true " \
                " UNION " \
                " Select \"SourceFile\" as file, \"mature_content\" as content " \
                " from Database where \"mature_content\" is true "
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertEqual(len(response), 5)
        for ele in response:
            self.assertTrue(ele["content"])

    def test_union_all(self):
        query = " Select \"SourceFile\" as file, \"mature_content\" as content " \
                " from Database where \"mature_content\" is true " \
                " UNION ALL " \
                " Select \"SourceFile\" as file, \"mature_content\" as content " \
                " from Database where \"mature_content\" is true "
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertEqual(len(response), 10)
        for ele in response:
            self.assertTrue(ele["content"])

    @unittest.skipIf(TEST_IMPLEMENTED_OPERATIONS_ONLY, "Only testing working operations")
    def test_intersect(self):
        raise NotImplementedError

    def test_compound_select_order_by(self):
        query = " Select \"SourceFile\" as file, \"mature_content\" as content " \
                " from Database " \
                " UNION ALL " \
                " Select \"SourceFile\" as file, \"mature_content\" as content " \
                " from Database where \"mature_content\" is true order by content"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertEqual(len(response), 20)

    def test_run_all_parser_tests(self):
        tests = """\
                select * From Database where z > 100
                select * where z > 100 order by zz
                select *
                select z.*
                select a, b where 1==1 and b=='yes'
                select a, b where 1=1
                select z.a, b where 1=1
                select z.a, b where 1=1 order by b,c desc,d
                select a, db.table.b as BBB where 1=1 and BBB='yes'
                select a, db.table.b as BBB where 1=1 and BBB='yes'
                select a, db.table.b as BBB where 1=1 and BBB='yes' limit 50
                SELECT * where (ST_Overlaps("GEOM", 'POINT(0 0)'))
                SELECT * where bar BETWEEN +180 AND +10E9
                SELECT SomeFunc(99)
                SELECT * where ST_X(ST_Centroid(geom)) BETWEEN (-180*2) AND (180*2)
                SELECT * where a
                SELECT * where snowy_things REGEXP '[⛄️☃️☃🎿🏂🌨❄️⛷🏔🗻❄︎❆❅]'
                SELECT * where a."b" IN 4
                SELECT * where a."b" In ('4')
                SELECT * where "E"."C" >= CURRENT_Time
                SELECT * where "dave" != "Dave" -- names & things ☃️
                SELECT * where a.dave is not null
                SELECT * where pete == FALSE or peter is true
                SELECT * where a >= 10 * (2 + 3)
                SELECT * where frank = 'is ''scary'''
                SELECT * where "identifier with ""quotes"" and a trailing space " IS NOT FALSE
                SELECT * where blobby == x'C0FFEE'  -- hex
                SELECT * where ff NOT IN (1,2,4,5)
                SELECT * where ff not between 3 and 9
                SELECT * where ff not like 'bob%'
                SELECT * where ff not like 'bob%' limit 10 offset 5
                SELECT * where foo like '%bob___'
                SELECT * where 1=1 union select * where 1=2
                SELECT * where 1=1 union all select * where 1=2
                SELECT * where 1=1 intersect select * where 1=2
            """
        for test in tests.split('\n'):
            success, parsed = mql._parser.runTests(test)
            self.assertTrue(success, f"Failed for test {test}")
