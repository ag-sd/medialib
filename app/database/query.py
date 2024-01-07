# https://stackoverflow.com/questions/44170597/pyparsing-nestedexpr-and-nested-parentheses
# https://github.com/pyparsing/pyparsing/tree/master/examples

from pyparsing import ParserElement, Suppress, Literal, Forward, CaselessKeyword, MatchFirst, QuotedString, Word, \
    alphas, alphanums, pyparsing_common, restOfLine, Regex, Combine, oneOf, nums, Optional, delimitedList, Group, \
    infixNotation, opAssoc, ZeroOrMore


class Tokenizer:
    class _Grammar:
        # Adapted from
        # https://github.com/pyparsing/pyparsing/blob/master/examples/select_parser.py
        # select_parser.py
        # Copyright 2010,2019 Paul McGuire
        #
        # a simple SELECT statement parser, taken from SQLite's SELECT statement
        # definition at https://www.sqlite.org/lang_select.html

        ParserElement.enablePackrat()

        LPAR, RPAR, COMMA = map(Suppress, "(),")
        DOT, STAR = map(Literal, ".*")
        select_stmt = Forward().setName("select statement")

        # keywords
        keywords = {
            k: CaselessKeyword(k)
            for k in """\
                        ALL AND ASC DESC ON AS NOT
                        SELECT DISTINCT WHERE GROUP BY HAVING ORDER LIMIT OFFSET OR ISNULL NOTNULL NULL IS BETWEEN ELSE
                        EXISTS IN LIKE REGEXP CURRENT_TIME CURRENT_DATE CURRENT_TIMESTAMP TRUE FALSE
                        """.split()
        }
        vars().update(keywords)

        any_keyword = MatchFirst(keywords.values())

        quoted_identifier = QuotedString('"', escQuote='""')
        identifier = (~any_keyword + Word(alphas, alphanums + "_")).setParseAction(
            pyparsing_common.downcaseTokens
        ) | quoted_identifier
        column_name = identifier.copy()
        column_alias = identifier.copy()
        table_name = identifier.copy()
        table_alias = identifier.copy()
        index_name = identifier.copy()
        function_name = identifier.copy()
        parameter_name = identifier.copy()
        database_name = identifier.copy()

        comment = "--" + restOfLine

        # expression
        expr = Forward().setName("expression")

        numeric_literal = pyparsing_common.number
        string_literal = QuotedString("'", escQuote="''")
        blob_literal = Regex(r"[xX]'[0-9A-Fa-f]+'")
        literal_value = (
                numeric_literal
                | string_literal
                | blob_literal
                | TRUE
                | FALSE
                | NULL
                | CURRENT_TIME
                | CURRENT_DATE
                | CURRENT_TIMESTAMP
        )
        bind_parameter = Word("?", nums) | Combine(oneOf(": @ $") + parameter_name)

        expr_term = (
                EXISTS + LPAR + select_stmt + RPAR
                | function_name.setName("function_name")
                + LPAR
                + Optional(STAR | delimitedList(expr))
                + RPAR
                | literal_value
                | bind_parameter
                | Group(
            identifier("col_db") + DOT + identifier("col_tab") + DOT + identifier("col")
        )
                | Group(identifier("col_tab") + DOT + identifier("col"))
                | Group(identifier("col"))
        )

        NOT_NULL = Group(NOT + NULL)
        NOT_BETWEEN = Group(NOT + BETWEEN)
        NOT_IN = Group(NOT + IN)
        NOT_LIKE = Group(NOT + LIKE)
        # NOT_MATCH = Group(NOT + MATCH)
        NOT_REGEXP = Group(NOT + REGEXP)

        UNARY, BINARY, TERNARY = 1, 2, 3
        expr << infixNotation(
            expr_term,
            [
                (oneOf("- + ~") | NOT, UNARY, opAssoc.RIGHT),
                (ISNULL | NOTNULL | NOT_NULL, UNARY, opAssoc.LEFT),
                ("||", BINARY, opAssoc.LEFT),
                (oneOf("* / %"), BINARY, opAssoc.LEFT),
                (oneOf("+ -"), BINARY, opAssoc.LEFT),
                (oneOf("<< >> & |"), BINARY, opAssoc.LEFT),
                (oneOf("< <= > >="), BINARY, opAssoc.LEFT),
                (
                    oneOf("= == != <>")
                    | IS
                    | IN
                    | LIKE
                    | REGEXP
                    | NOT_IN
                    | NOT_LIKE
                    | NOT_REGEXP,
                    BINARY,
                    opAssoc.LEFT,
                ),
                ((BETWEEN | NOT_BETWEEN, AND), TERNARY, opAssoc.LEFT),
                (
                    (IN | NOT_IN) + LPAR + Group(delimitedList(expr)) + RPAR,
                    UNARY,
                    opAssoc.LEFT,
                ),
                (AND, BINARY, opAssoc.LEFT),
                (OR, BINARY, opAssoc.LEFT),
            ],
        )

        ordering_term = Group(
            expr("order_key")
            + Optional(ASC | DESC)("direction")
        )

        single_source = (
                Group(database_name("database") + DOT + table_name("table*") | table_name("table*"))
                + Optional(Optional(AS) + table_alias("table_alias*"))
                | (LPAR + select_stmt + RPAR + Optional(Optional(AS) + table_alias))
        )

        result_column = Group(
            STAR("col")
            | table_name("col_table") + DOT + STAR("col")
            | expr("col") + Optional(Optional(AS) + column_alias("alias"))
        )

        select_core = (
                SELECT
                + Optional(DISTINCT | ALL)
                + Group(delimitedList(result_column))("columns")
                + Optional(WHERE + expr("where_expr"))
                + Optional(
            Optional(HAVING + expr("having_expr"))
        )
        )

        select_stmt << (
                select_core
                + ZeroOrMore(select_core)
                + Optional(ORDER + BY + Group(delimitedList(ordering_term))("order_by_terms"))
                + Optional(
            LIMIT
            + (Group(expr + OFFSET + expr) | Group(expr + COMMA + expr) | expr)("limit")
        )
        )

        select_stmt.ignore(comment)

    def __init__(self):
        super().__init__()

    parser = _Grammar.select_stmt

    @staticmethod
    def tokenize(query):
        return Tokenizer.parser.parseString(query, parseAll=True)


# def main():
#     tests = """\
#         select * where z > 100
#         select * where z > 100 order by zz
#         select *
#         select z.*
#         select a, b where 1=1 and b='yes'
#         select a, b where 1=1
#         select z.a, b where 1=1
#         select z.a, b where 1=1 order by b,c desc,d
#         select a, db.table.b as BBB where 1=1 and BBB='yes'
#         select a, db.table.b as BBB where 1=1 and BBB='yes'
#         select a, db.table.b as BBB where 1=1 and BBB='yes' limit 50
#         SELECT * where (ST_Overlaps("GEOM", 'POINT(0 0)'))
#         SELECT * where bar BETWEEN +180 AND +10E9
#         SELECT SomeFunc(99)
#         SELECT * where ST_X(ST_Centroid(geom)) BETWEEN (-180*2) AND (180*2)
#         SELECT * where a
#         SELECT * where snowy_things REGEXP '[⛄️☃️☃🎿🏂🌨❄️⛷🏔🗻❄︎❆❅]'
#         SELECT * where a."b" IN 4
#         SELECT * where a."b" In ('4')
#         SELECT * where "E"."C" >= CURRENT_Time
#         SELECT * where "dave" != "Dave" -- names & things ☃️
#         SELECT * where a.dave is not null
#         SELECT * where pete == FALSE or peter is true
#         SELECT * where a >= 10 * (2 + 3)
#         SELECT * where frank = 'is ''scary'''
#         SELECT * where "identifier with ""quotes"" and a trailing space " IS NOT FALSE
#         SELECT * where blobby == x'C0FFEE'  -- hex
#         SELECT * where ff NOT IN (1,2,4,5)
#         SELECT * where ff not between 3 and 9
#         SELECT * where ff not like 'bob%'
#         SELECT * where ff not like 'bob%' limit 10 offset 5
#     """
#
#     # for test in tests.split('\n'):
#     #     print(test)
#     #     success, parsed = MQL.parser.runTests(test)
#     #     if not success:
#     #         print("Error")
#     #         print(parsed)
#     #         exit(0)
#     #     print("----------------------------")
#
#     print(Tokenizer.tokenize(" SELECT * WHERE (1!=2 or 2!=3) and 2=3 or (foo='bar')"))
#     print("All done!")
#
#
# if __name__ == "__main__":
#     main()
