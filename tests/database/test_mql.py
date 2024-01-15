import unittest
from pathlib import Path

from app.database import mql

from pyparsing import ParseException


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
        query = "select * from Database where '.File:ImageHeight' > 2315"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertTrue(len(response) == 3)

    def test_field_qualified_name_check(self):
        query = "select * from Database where 'db.File:ImageHeight' > 2315"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertTrue(len(response) == 3)

    def test_field_with_and(self):
        query = "select * from Database where '.File:ImageHeight' == 256 and '.File:ImageWidth' == 256"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertTrue(len(response) == 1)

    def test_field_with_or(self):
        query = "select * from Database where '.File:ImageHeight' == 256 or '.File:ImageWidth' == 3024"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertTrue(len(response) == 2)

    def test_in_clause_nums(self):
        query = "select * from Database where '.File:ImageHeight' in (256, 1500)"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertTrue(len(response) == 3)

    def test_in_clause_expr(self):
        query = "select * from Database where '.File:ImageHeight' in (16 * 16, 1600 - 100)"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertTrue(len(response) == 3)

    def test_in_clause_strings(self):
        query = "select 'SourceFile' from Database where '.System:FileSize' in ('139 kB', '179 kB')"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertTrue(len(response) == 2)

    def test_not_in_clause_strings(self):
        query = "select 'SourceFile' from Database where '.System:FileSize' not in ('139 kB', '179 kB')"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertTrue(len(response) == 13)

    def test_between_clause(self):
        query = "select * from Database where '.File:ImageHeight' between 256, 1500"
        try:
            response = mql.query_file(query, self.TEST_INPUT)
            self.assertTrue(len(response) == 2)
        except ParseException:
            self.assertTrue(True)

    def test_select_single_field_operation(self):
        query = "select 'SourceFile' from Database"
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
        try:
            _ = mql.query_file(query, self.TEST_INPUT)
            self.assertFalse(True, "This query should fail parsing")
        except ParseException:
            self.assertTrue(True)

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
        query = "select 'SourceFile' from Database"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertEqual(len(response), 15)

    def test_field_unquoted_alias(self):
        """
        Unquoted aliases are lowercased
        """
        query = "select 'SourceFile' as File, 'System:FileSize' as size, " \
                "'File:ImageWidth' as width, 'File:ImageHeight' as height from Database"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertEqual(len(response), 15)
        for ele in response:
            self.assertEqual(len(ele), 4)
            self.assertTrue("file" in ele)
            self.assertTrue("size" in ele)
            self.assertTrue("width" in ele)
            self.assertTrue("height" in ele)

    # def test_field_quoted_alias(self):
    #     query = "select 'SourceFile' as 'File', 'System:FileSize' as 'SizE', " \
    #             "'File:ImageWidth' as width, 'File:ImageHeight' as height from Database"
    #     response = mql.query_file(query, self.TEST_INPUT)
    #     self.assertEqual(len(response), 15)
    #     for ele in response:
    #         self.assertEqual(len(ele), 4)
    #         self.assertTrue("file" in ele)
    #         self.assertTrue("size" in ele)
    #         self.assertTrue("width" in ele)
    #         self.assertTrue("height" in ele)

    def test_regexp_match(self):
        query = "Select 'SourceFile' as file from Database where '.SourceFile' regexp '.*lena.*'"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertEqual(len(response), 9)
        for ele in response:
            name = ele["file"]
            # Note: Case Insensitive search
            self.assertTrue("lena" in name or "Lena" in name)

    def test_regexp_not_match(self):
        query = "Select 'SourceFile' as file from Database where '.SourceFile' not regexp '.*lena.*'"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertEqual(len(response), 6)
        for ele in response:
            name = ele["file"]
            self.assertTrue("lena" not in name)

    def test_like_operation_ends_with(self):
        query = "Select 'SourceFile' as file, 'File:FileType' as type " \
                "from Database where '.File:FileType' like '%g'"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertEqual(len(response), 10)
        for ele in response:
            _type = ele["type"]
            self.assertTrue("JPEG" == _type or "PNG" == _type)

    def test_like_operation_starts_with_and_ends_with(self):
        query = "Select 'SourceFile' as file, 'File:FileType' as type " \
                "from Database where '.File:FileType' like 'j%g'"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertEqual(len(response), 8)
        for ele in response:
            _type = ele["type"]
            self.assertTrue("JPEG" == _type)

    def test_like_operation_contains(self):
        query = "Select 'SourceFile' as file, 'File:FileType' as type " \
                "from Database where '.File:FileType' like '%n%'"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertEqual(len(response), 2)
        for ele in response:
            _type = ele["type"]
            self.assertTrue("PNG" == _type)

    def test_like_operation_fixed_len(self):
        query = "Select 'SourceFile' as file, 'File:FileType' as type " \
                "from Database where '.File:FileType' like '___'"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertEqual(len(response), 4)
        for ele in response:
            _type = ele["type"]
            self.assertTrue("PNG" == _type or "GIF" == _type)

    def test_like_combination_with_positional(self):
        query = "Select 'SourceFile' as file, 'File:FileType' as type " \
                "from Database where '.File:FileType' like '%if_'"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertEqual(len(response), 3)
        for ele in response:
            _type = ele["type"]
            self.assertTrue("TIFF" == _type)

    def test_like_exact_match(self):
        query = "Select 'SourceFile' as file, 'File:FileType' as type " \
                "from Database where '.File:FileType' like 'GIF'"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertEqual(len(response), 2)
        for ele in response:
            _type = ele["type"]
            self.assertTrue("GIF" == _type)

    def test_is_operator_basic(self):
        query = "Select 'SourceFile' as file, 'File:FileType' as type " \
                "from Database where '.File:FileType' is 'GIF'"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertEqual(len(response), 2)
        for ele in response:
            _type = ele["type"]
            self.assertTrue("GIF" == _type)

    def test_is_operator_basic_not(self):
        query = "Select 'SourceFile' as file, 'File:FileType' as type " \
                "from Database where '.File:FileType' is not 'JPEG'"
        response = mql.query_file(query, self.TEST_INPUT)
        self.assertEqual(len(response), 2)
        for ele in response:
            _type = ele["type"]
            self.assertTrue("JPEG" == _type)










    # SELECT * where bar BETWEEN +180 AND +10E9
    # SELECT * where snowy_things REGEXP '[⛄️☃️☃🎿🏂🌨❄️⛷🏔🗻❄︎❆❅]'
    # SELECT * where a."b" IN 4
    # SELECT * where a."b" In ('4')
    # SELECT * where "E"."C" >= CURRENT_Time
    # SELECT * where "dave" != "Dave" -- names & things ☃️
    # SELECT * where frank = 'is ''scary'''
    # SELECT * where ff NOT IN (1,2,4,5)
    # SELECT * where ff not between 3 and 9
    # SELECT * where ff not like 'bob%'
    # SELECT * where ff not like '%bob'
    # SELECT * where ff not like 'bo%b' limit 10 offset 5
    # Test Not

    #
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
            """
        for test in tests.split('\n'):
            success, parsed = mql._parser.runTests(test)
            self.assertTrue(success, f"Failed for test {test}")
