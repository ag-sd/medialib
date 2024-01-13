import unittest
from pathlib import Path

from app.database.query import MQL


class TestMQLTokenizer(unittest.TestCase):
    TEST_INPUT = str(Path(__file__).parent.parent / "resources" / "test_db_data.json")

    def test_simple_select_no_where(self):
        query = "select * From Database"
        querier = MQL()
        response = querier.filter_in_file(query, self.TEST_INPUT)
        self.assertTrue(len(response) == 15)

    def test_unary_where(self):
        query = "select * from Database where 1-1=0"
        querier = MQL()
        response = querier.filter_in_file(query, self.TEST_INPUT)
        self.assertTrue(len(response) == 15)

    def test_unary_false(self):
        query = "select * from Database where 1-1=01"
        querier = MQL()
        response = querier.filter_in_file(query, self.TEST_INPUT)
        self.assertTrue(len(response) == 0)

    def test_field_check(self):
        query = "select * from Database where '.File:ImageHeight' > 2315"
        querier = MQL()
        response = querier.filter_in_file(query, self.TEST_INPUT)
        self.assertTrue(len(response) == 3)

    def test_field_with_and(self):
        query = "select * from Database where '.File:ImageHeight' < 2315 and '.File:ImageWidth' == 512"
        querier = MQL()
        response = querier.filter_in_file(query, self.TEST_INPUT)
        print(response)


    #
    # def test_run_all_tests(self):
    #     tests = """\
    #             select * From Database where z > 100
    #             select * where z > 100 order by zz
    #             select *
    #             select z.*
    #             select a, b where 1==1 and b=='yes'
    #             select a, b where 1=1
    #             select z.a, b where 1=1
    #             select z.a, b where 1=1 order by b,c desc,d
    #             select a, db.table.b as BBB where 1=1 and BBB='yes'
    #             select a, db.table.b as BBB where 1=1 and BBB='yes'
    #             select a, db.table.b as BBB where 1=1 and BBB='yes' limit 50
    #             SELECT * where (ST_Overlaps("GEOM", 'POINT(0 0)'))
    #             SELECT * where bar BETWEEN +180 AND +10E9
    #             SELECT SomeFunc(99)
    #             SELECT * where ST_X(ST_Centroid(geom)) BETWEEN (-180*2) AND (180*2)
    #             SELECT * where a
    #             SELECT * where snowy_things REGEXP '[⛄️☃️☃🎿🏂🌨❄️⛷🏔🗻❄︎❆❅]'
    #             SELECT * where a."b" IN 4
    #             SELECT * where a."b" In ('4')
    #             SELECT * where "E"."C" >= CURRENT_Time
    #             SELECT * where "dave" != "Dave" -- names & things ☃️
    #             SELECT * where a.dave is not null
    #             SELECT * where pete == FALSE or peter is true
    #             SELECT * where a >= 10 * (2 + 3)
    #             SELECT * where frank = 'is ''scary'''
    #             SELECT * where "identifier with ""quotes"" and a trailing space " IS NOT FALSE
    #             SELECT * where blobby == x'C0FFEE'  -- hex
    #             SELECT * where ff NOT IN (1,2,4,5)
    #             SELECT * where ff not between 3 and 9
    #             SELECT * where ff not like 'bob%'
    #             SELECT * where ff not like 'bob%' limit 10 offset 5
    #         """
    #
    #     for test in tests.split('\n'):
    #         success, parsed = Tokenizer.parser.runTests(test)
    #         self.assertTrue(success)
    #
    # def test_invalid_query(self):
    #     try:
    #         Tokenizer.tokenize("SELECT * where ff not like 'bob%' limit 10 offset")
    #         self.assertFalse(True, "This query is syntactically incorrect")
    #     except ParseException:
    #         self.assertTrue(True)
