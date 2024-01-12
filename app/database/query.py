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
                    oneOf("== != <>")
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

    def __init__(self):
        super().__init__()

    parser = _Grammar.select_stmt

    @staticmethod
    def tokenize(query):
        return Tokenizer.parser.parseString(query, parseAll=True)


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

    # TODO
    # | IN
    # | REGEXP
    # | NOT_IN
    # | NOT_LIKE
    # | NOT_REGEXP,

    @staticmethod
    def flatten(expression):
        if isinstance(expression, list):
            operand = expression[1]
            match operand:
                case '<>':
                    return f"(  {JQAdapter.flatten(expression[0])}  !=  {JQAdapter.flatten(expression[2])}  )"
                case 'IS':
                    return f"(  {JQAdapter.flatten(expression[0])}  ==  {JQAdapter.flatten(expression[2])}  )"
                case 'LIKE':
                    return f"(  {JQAdapter.flatten(expression[0])}  |  contains('{JQAdapter.flatten(expression[2])}')  )"
                case _:
                    return f"(  {JQAdapter.flatten(expression[0])}  {expression[1]}  {JQAdapter.flatten(expression[2])}  )"
        elif isinstance(expression, dict):
            return expression['col'][0]
        else:
            return expression


    @staticmethod
    def _where_expansion(tokenized_dict: dict) -> str:
        pass



#cat home__sheldon__Documents__dev__testing__images.json | jq -c '.[] | select( ."File:ImageHeight">2315 or ."File:ImageHeight" ==3744) | select(."SourceFile" | contains("unsplash")) | {message: ."SourceFile", height: ."File:ImageHeight"}'
#cat home__sheldon__Documents__dev__testing__images.json | jq -c '.[] | select( (."File:ImageHeight">2315) or (."File:ImageHeight" ==3744) or (."SourceFile" | contains("unsplash"))) | {message: ."SourceFile", height: ."File:ImageHeight"}'
if __name__ == "__main__":
    resp = Tokenizer.tokenize(" SELECT x.a as Foo, b as Bar, c WHERE (1!=2 or 2!=3) and 2==3 or (foo=='bar')")
    resp = Tokenizer.tokenize(" SELECT x.a as Foo, b as Bar, c WHERE (1!=2 or 2!=3) and goo<>boo or (foo=='bar')")
    resp = Tokenizer.tokenize(" SELECT x.a as Foo, b as Bar, c WHERE sourcefile not like '%hello'")
    dick = resp.asDict()

    print(JQAdapter.flatten(dick['where_expr']))
    print("All done!")
