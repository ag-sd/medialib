# https://stackoverflow.com/questions/44170597/pyparsing-nestedexpr-and-nested-parentheses
# https://github.com/pyparsing/pyparsing/tree/master/examples
import json
import subprocess

from pyparsing import ParserElement, Suppress, Literal, Forward, CaselessKeyword, MatchFirst, QuotedString, Word, \
    alphas, alphanums, pyparsing_common, restOfLine, Regex, Combine, oneOf, nums, Optional, delimitedList, Group, \
    infixNotation, opAssoc, ZeroOrMore

import app


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
                        SELECT DISTINCT FROM WHERE GROUP BY HAVING ORDER LIMIT OFFSET OR ISNULL NOTNULL NULL IS BETWEEN ELSE
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
            + Optional(FROM + "Database")
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


_parser = _Grammar.select_stmt


class MQL:
    def __init__(self):
        super().__init__()

    def filter_in_data(self, query: str, input_data: str):
        pass

    def filter_in_file(self, query: str, input_file: str):
        filter_map = self._evaluate_query(query)
        app.logger.debug(f"Applying JQ filter-map:  cat {input_file} | jq '{filter_map}'")
        transformed = subprocess.run(["jq", filter_map, input_file], capture_output=True)
        transformed.check_returncode()
        return json.loads(transformed.stdout.decode("utf8"))

    def _evaluate_query(self, query: str):
        tokenized_query = _parser.parseString(query, parseAll=True).asDict()
        if "where_expr" in tokenized_query:
            where_expr = f" | select( {self._flatten(tokenized_query['where_expr'])} )"
        else:
            where_expr = ""
        return f"[.[] {where_expr}]"

    # TODO
    # | IN
    # | REGEXP
    # | NOT_IN
    # | NOT_REGEXP,
    def _flatten(self, expression):
        if isinstance(expression, list):
            operand = self._compose_operand(expression[1])
            suffix = " | not" if operand.startswith("NOT_") else ""
            match operand:
                case '<>':
                    return f"(  {self._flatten(expression[0])}  !=  {self._flatten(expression[2])}  )"
                case 'IS' | "=":
                    return f"(  {self._flatten(expression[0])}  ==  {self._flatten(expression[2])}  )"
                case 'LIKE' | 'NOT_LIKE':
                    expr2 = self._flatten(expression[2])
                    if expr2.startswith('%'):
                        q = f"( {self._flatten(expression[0])} | startswith('{self._flatten(expression[2])}'){suffix} )"
                    elif expr2.endswith('%'):
                        q = f"( {self._flatten(expression[0])} | endswith('{self._flatten(expression[2])}'){suffix} )"
                    else:
                        q = f"( {self._flatten(expression[0])} | contains('{self._flatten(expression[2])}'){suffix} )"
                    return q
                case _:
                    return f"(  {self._flatten(expression[0])}  {expression[1]}  {self._flatten(expression[2])}  )"
        elif isinstance(expression, dict):
            return expression['col'][0]
        elif isinstance(expression, str):
            # Wrap strings in quotes
            if expression.startswith("."):
                # Handle field names
                print("Field")
                return f'."{expression[1:]}"'
            return f'"{expression}"'
        else:
            return expression

    @staticmethod
    def _compose_operand(expression):
        if isinstance(expression, list):
            return "_".join(expression)
        else:
            return expression


class JQAdapter:
    def __init__(self):
        super().__init__()

    @staticmethod
    def _col_syntax(tokenized_dict: dict) -> str:
        columns = []
        for column in tokenized_dict['columns']:
            field = column['col']['col'][0]
            alias = column['alias'][0] if 'alias' in column else field
            columns.append(f"'{alias}':'{field}'")

        return f"{{{','.join(columns)}}}"



    @staticmethod
    def _where_expansion(tokenized_dict: dict) -> str:
        pass


# cat home__sheldon__Documents__dev__testing__images.json | jq -c '.[] | select( ."File:ImageHeight">2315 or ."File:ImageHeight" ==3744) | select(."SourceFile" | contains("unsplash")) | {message: ."SourceFile", height: ."File:ImageHeight"}'
# cat home__sheldon__Documents__dev__testing__images.json | jq -c '.[] | select( (."File:ImageHeight">2315) or (."File:ImageHeight" ==3744) or (."SourceFile" | contains("unsplash"))) | {message: ."SourceFile", height: ."File:ImageHeight"}'
if __name__ == "__main__":
    # resp = Tokenizer.tokenize(" SELECT x.a as Foo, b as Bar, c WHERE (1!=2 or 2!=3) and 2==3 or (foo=='bar')")
    # resp = Tokenizer.tokenize(" SELECT x.a as Foo, b as Bar, c WHERE (1!=2 or 2!=3) and goo<>boo or (foo=='bar')")
    # resp = JQ()._evaluate_query(" SELECT x.a as Foo, b as Bar, c WHERE (1!=2 or 2!=3) and goo<>boo or (foo=='bar')")
    resp = MQL().filter_in_file(" SELECT * from Database", "/mnt/dev/medialib/tests/resources/test_db_data.json")

    print(resp)
    print("All done!")
