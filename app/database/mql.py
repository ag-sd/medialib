# https://stackoverflow.com/questions/44170597/pyparsing-nestedexpr-and-nested-parentheses
# https://github.com/pyparsing/pyparsing/tree/master/examples
# https://www.sqlite.org/lang_expr.html
# https://sqlparse.readthedocs.io/en/latest/

import json
import subprocess
from collections import namedtuple

from pyparsing import ParserElement, Suppress, Literal, Forward, CaselessKeyword, MatchFirst, QuotedString, Word, \
    alphas, alphanums, pyparsing_common, restOfLine, Regex, Combine, oneOf, nums, Optional, delimitedList, Group, \
    infixNotation, opAssoc, ZeroOrMore, ParseException

import app

_MQ_T_LIMIT = "__LIMIT__"
_MQ_T_ORDER_BY_TERMS = "ORDER_BY_TERMS"
_MQ_T_ORDER_BY_DIRECTION = "direction"
_MQ_T_ORDER_KEY = "ORDER_KEY"
_MQ_T_HAVING_EXPRESSION = "HAVING_EXPR"
_MQ_T_WHERE_EXPRESSION = "__WHERE_EXPR__"
_MQ_T_SELECT_OPTS = "__SELECT_OPTS__"
_MQ_T_COLS = "__COLUMNS__"
_MQ_T_COL_ALIAS = "__ALIAS__"
_MQ_T_COL_TABLE = "__COL_TABLE__"
_MQ_T_COL_DB = "__COL_DB__"
_MQ_T_COL_TAB = "__COL_TAB__"
_MQ_T_COL = "__COL__"

_MQ_SUPPORTED_KEYWORDS = "ALL AND ASC DESC ON AS NOT SELECT DISTINCT FROM WHERE GROUP BY " \
                         "HAVING ORDER LIMIT OFFSET OR ISNULL NOTNULL NULL IS BETWEEN ELSE " \
                         "EXISTS IN LIKE REGEXP CURRENT_TIME CURRENT_DATE CURRENT_TIMESTAMP TRUE FALSE"
_MQ_EMPTY_STRING = ""
_MQ_REGEX_OPS = "ixn"
_MQ_LITERAL_KEYWORDS = ["TRUE", "FALSE", "NULL"]


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
        for k in _MQ_SUPPORTED_KEYWORDS.split()
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
        identifier(_MQ_T_COL_DB) + DOT + identifier(_MQ_T_COL_TAB) + DOT + identifier(_MQ_T_COL)
    )
            | Group(identifier(_MQ_T_COL_TAB) + DOT + identifier(_MQ_T_COL))
            | Group(identifier(_MQ_T_COL))
    )

    NOT_NULL = Group(NOT + NULL)
    NOT_BETWEEN = Group(NOT + BETWEEN)
    NOT_IN = Group(NOT + IN)
    NOT_LIKE = Group(NOT + LIKE)
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
        expr(_MQ_T_ORDER_KEY)
        + Optional(ASC | DESC)(_MQ_T_ORDER_BY_DIRECTION)
    )

    single_source = (
            Group(database_name("database") + DOT + table_name("table*") | table_name("table*"))
            + Optional(Optional(AS) + table_alias("table_alias*"))
            | (LPAR + select_stmt + RPAR + Optional(Optional(AS) + table_alias))
    )

    result_column = Group(
        STAR(_MQ_T_COL)
        | table_name(_MQ_T_COL_TABLE) + DOT + STAR(_MQ_T_COL)
        | expr(_MQ_T_COL) + Optional(Optional(AS) + column_alias(_MQ_T_COL_ALIAS))
    )

    select_core = (
            SELECT
            + Group(Optional(DISTINCT | ALL))(_MQ_T_SELECT_OPTS)
            + Group(delimitedList(result_column))(_MQ_T_COLS)
            + Optional(FROM + oneOf("Database"))
            + Optional(WHERE + expr(_MQ_T_WHERE_EXPRESSION))
            + Optional(
        Optional(HAVING + expr(_MQ_T_HAVING_EXPRESSION))
    )
    )

    select_stmt << (
            select_core
            + ZeroOrMore(select_core)
            + Optional(ORDER + BY + Group(delimitedList(ordering_term))(_MQ_T_ORDER_BY_TERMS))
            + Optional(
        LIMIT
        + (Group(expr + OFFSET + expr) | Group(expr + COMMA + expr) | expr)(_MQ_T_LIMIT)
    )
    )

    select_stmt.ignore(comment)


class QueryException(Exception):
    def __init__(self, message):
        super().__init__(message)


_parser = _Grammar.select_stmt


def query_data(query: str, input_data: str):
    pass


def query_file(query: str, file: str):
    try:
        filter_map = _evaluate_query(query)
        app.logger.debug(f"Applying JQ filter-map:  cat {file} | jq '{filter_map}'")
        transformed = subprocess.run(["jq", filter_map, file], capture_output=True)
        transformed.check_returncode()
        return json.loads(transformed.stdout.decode("utf8"))
    except ParseException as p:
        app.logger.error(f"\n{p.explain()}")
        raise QueryException("An error occurred while parsing the query") from p
    except subprocess.CalledProcessError as c:
        raise QueryException("An error occurred while querying the data") from c


# TODO:
#     - HAVING
#     - OFFSET
#     - ORDER BY
#     - TIME OPERATIONS
#     - UNION | INTERSECT | EXCEPT
def _evaluate_query(query: str):
    tokenized_query = _parser.parseString(query, parseAll=True).asDict()
    # SELECT Clause
    select_expr = _choose_columns(tokenized_query[_MQ_T_COLS])
    if select_expr != _MQ_EMPTY_STRING:
        select_expr = f"| {{ {select_expr} }}"
    # SELECT Options
    opts_expr = _MQ_EMPTY_STRING
    if _MQ_T_SELECT_OPTS in tokenized_query:
        # One of the ALL or DISTINCT keywords may follow the SELECT keyword in a simple SELECT statement.
        # If the simple SELECT is a SELECT ALL, then the entire set of result rows are returned by the SELECT.
        # If neither ALL or DISTINCT are present, then the behavior is as if ALL were specified.
        # If the simple SELECT is a SELECT DISTINCT, then duplicate rows are removed from the set of result rows
        # before it is returned. For the purposes of detecting duplicate rows,
        # two NULL values are considered to be equal.
        if "DISTINCT" in tokenized_query[_MQ_T_SELECT_OPTS]:
            opts_expr = " | unique"
        elif "ALL" in tokenized_query[_MQ_T_SELECT_OPTS]:
            app.logger.debug("Ignore ALL keyword as this is default behavior of the query engine")
    # WHERE Clause
    if _MQ_T_WHERE_EXPRESSION in tokenized_query:
        where_expr = f" | select( {_flatten(tokenized_query[_MQ_T_WHERE_EXPRESSION])} )"
    else:
        where_expr = _MQ_EMPTY_STRING

    # Order By
    order_by_terms = _MQ_EMPTY_STRING
    if _MQ_T_ORDER_BY_TERMS in tokenized_query:
        order_by_terms = _compose_order_by_terms(tokenized_query[_MQ_T_COLS], tokenized_query[_MQ_T_ORDER_BY_TERMS])

    # Limit
    if _MQ_T_LIMIT in tokenized_query:
        return f"[ limit( {tokenized_query[_MQ_T_LIMIT][0]} ; .[] {where_expr} {select_expr} ) ] " \
               f"{opts_expr} {order_by_terms}".strip()

    return f"[.[] {where_expr} {select_expr}] {opts_expr} {order_by_terms}".strip()


def _choose_columns(col_list: list) -> str:
    # First Check for all columns (*)
    if _is_select_star(col_list):
        # Empty string represents no field selection by JQ
        return _MQ_EMPTY_STRING

    # Then check for individual columns
    columns = []
    for column in col_list:
        qualified = _get_column_and_alias(column)
        columns.append(f'"{qualified.alias}":.["{qualified.field}"]')

    return f"{','.join(columns)}"


def _is_select_star(col_list: list) -> bool:
    """
    Checks if the columns list is a simple `select *` query.
    Args:
        col_list: The tokenized columns list from the query

    Returns: Will return true if the columns list is a select *

    """
    return len(col_list) == 1 and col_list[0][_MQ_T_COL] == "*"


def _get_column_and_alias(column: dict) -> tuple:
    """
    Returns a named tuple representing the column and its alias
    Args:
        column: The tokenized column entry from the query

    Returns: A named tuple Column = namedtuple('Column', 'field alias')

    """
    Column = namedtuple('Column', 'field alias')

    node = column[_MQ_T_COL]
    if _MQ_T_COL in node:
        # Aliased columns
        field = node[_MQ_T_COL][0]
    else:
        field = node

    alias = column[_MQ_T_COL_ALIAS][0] if _MQ_T_COL_ALIAS in column else field
    return Column(field=_compose_field_name(field), alias=alias)


def _compose_order_by_terms(col_list: list, order_by_keys: dict) -> str:
    """
    Generates a JQ order by command with a few limitations.
    1. Mixed order by directions are not supported. This is because different JQ commands are required to handle
    nulls, numbers and strings. As the value of the data is unknown, this cannot be correctly predicted.
    2. If a column is aliased, that alias must be used in the order by. If the column name is used instead,
    JQ will ignore the ordering

    --> https://www.sqlite.org/lang_select.html#orderby
    Each ORDER BY expression is processed as follows:
    1. If the ORDER BY expression is a constant integer K then the expression is considered an alias for the
    K-th column of the result set (columns are numbered from left to right starting with 1).
    2. If the ORDER BY expression is an identifier that corresponds to the alias of one of the output columns,
    then the expression is considered an alias for that column.
    3. Otherwise, if the ORDER BY expression is any other expression, it is evaluated and the returned value
    used to order the output rows. ORDER BY expressions that are not aliases to output columns
    must be exactly the same as an expression used as an output column.

    Args:
        col_list: The list of columns from the select clause
        order_by_keys: The order by keys

    Returns: A string representation of the JQ sort_by command

    Raises: QueryException if either of the 2 rules mentioned above are violated

    """

    # Step 1: Get a list of columns / aliases from the select statement
    select_params = []
    is_select_star = _is_select_star(col_list)
    for column in col_list:
        qualified = _get_column_and_alias(column)
        select_params.append(qualified.alias)

    # Step 2: Check if order_by_terms has mixed sorting and confirm all
    sort_order = set()
    for key in order_by_keys:
        if _MQ_T_COL in key[_MQ_T_ORDER_KEY]:
            column_key = key[_MQ_T_ORDER_KEY][_MQ_T_COL][0]
        elif isinstance(key[_MQ_T_ORDER_KEY], int):
            column_idx = key[_MQ_T_ORDER_KEY]
            if 1 <= column_idx <= len(select_params):
                column_key = select_params[column_idx]
            else:
                raise QueryException(f"Index {column_idx} does not reference a valid column from the select clause")

        if _MQ_T_ORDER_BY_DIRECTION in key:
            sort_order.add(key[_MQ_T_ORDER_BY_DIRECTION])
        else:
            sort_order.add("ASC")
        if not (is_select_star or column_key in select_params):
            raise QueryException(f"Column {column_key} is not part of the select clause")

    return _MQ_EMPTY_STRING


def _flatten(expression):
    if isinstance(expression, list):
        operator = _compose_operator(expression[1])
        suffix = " | not" if operator.startswith("NOT_") else _MQ_EMPTY_STRING
        match operator:
            case "<>":
                return f"(  {_flatten(expression[0])}  !=  {_flatten(expression[2])}  )"
            case "=":
                return f"(  {_flatten(expression[0])}  ==  {_flatten(expression[2])}  )"
            case "IS":
                # The IS and IS NOT operators work like = and != except when one or both of the operands are NULL
                # get the NOT
                is_not = expression[2][0] == "NOT"
                if is_not:
                    expression[2] = expression[2].pop()
                suffix = " | not" if is_not else _MQ_EMPTY_STRING
                return f"(  {_flatten(expression[0])}  ==  {_flatten(expression[2])} {suffix} )"
            case "LIKE" | "NOT_LIKE" | "REGEXP" | "NOT_REGEXP":
                if operator == "LIKE" or operator == "NOT_LIKE":
                    regexp = _compose_like_operand(expression[2])
                else:
                    regexp = expression[2]
                return f"( {_flatten(expression[0])} | test(\"{regexp}\"; \"{_MQ_REGEX_OPS}\")  {suffix}  )"
            case "AND" | "OR":
                return f"(  {_flatten(expression[0])}  {operator.lower()}  {_flatten(expression[2])}  )"
            case "IN" | "NOT_IN":
                # https://stackoverflow.com/questions/50750688/jq-select-where-attribute-in-list
                # jq does implicit one-to-many and many-to-one munging so x == (a, b, c) is an IN. But
                # this does not work for NOT IN. Also note the case of 'IN' here as 'in' means something
                # else completely
                in_list = [str(_flatten(x)) for x in expression[2]]
                return f"(  {_flatten(expression[0])} | IN ({', '.join(in_list)}) {suffix} )"
            case "BETWEEN" | "NOT_BETWEEN":
                # The BETWEEN operator is logically equivalent to a pair of comparisons.
                # "x BETWEEN y AND z" is equivalent to "x>=y AND x<=z"
                # except that with BETWEEN, the x expression is only evaluated once.
                # https://www.sqlite.org/lang_expr.html#between
                operand_x = _flatten(expression[0])
                operand_y = _flatten(expression[2])
                operand_z = _flatten(expression[4])
                if operator == "NOT_BETWEEN":
                    # Flip x,y operands with an OR
                    return f"( ({operand_x} >= {operand_z}) or ({operand_x} <= {operand_y}) )"
                else:
                    return f"( ({operand_x} >= {operand_y}) and ({operand_x} <= {operand_z}) )"
            case _:
                return f"(  {_flatten(expression[0])}  {operator}  {_flatten(expression[2])}  )"
    elif isinstance(expression, dict):
        return expression[_MQ_T_COL][0]
    elif isinstance(expression, str):
        # Wrap strings in quotes
        if expression.startswith(".") or expression.startswith("db."):
            return f'."{_compose_field_name(expression)}"'
        if expression in _MQ_LITERAL_KEYWORDS:
            return expression.lower()
        return f'"{expression}"'
    else:
        return expression


def _compose_field_name(expression):
    if expression.startswith(".") or expression.startswith("db."):
        # Handle field names
        dot = expression.find(".") + 1
        return expression[dot:]
    # This is not a field!
    return expression


def _compose_operator(expression):
    if isinstance(expression, list):
        return "_".join(expression)
    else:
        return expression


def _compose_like_operand(expression: str) -> str:
    """
    Converts a like search term to a regex pattern based on the following rules
    https://www.w3schools.com/sql/sql_like.asp
    % -> .*? : matches any character (except for line terminators) between zero and unlimited times, as few times
    as possible, expanding as needed (lazy)
    _ -> .   : matches any character (except for line terminators)
    Example:
        Hello
        %lo     -> ^.*?lo$
        He%     -> ^He.*?$
        He%o    -> ^He.*?o$
        He__o   -> ^He..o$
        %__o     -> ^.*?..o$
    """
    expression = expression.replace("%", ".*?")
    expression = expression.replace("_", ".")
    return f"^{expression}$"
