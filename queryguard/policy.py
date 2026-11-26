"""Fail-closed PostgreSQL subset. Qualification is resolution, not authorization."""

import logging
import re
from dataclasses import dataclass

import sqlglot

# SQLGlot parser warnings can echo the full untrusted SQL. This application
# uses sanitized PolicyError diagnostics instead; never route those records to logs.
logging.getLogger("sqlglot").addFilter(lambda record: False)
from sqlglot import exp
from sqlglot.optimizer.qualify import qualify
from sqlglot.optimizer.scope import Scope, traverse_scope

from queryguard.db import TABLES

MAX_ROWS = 200
MAX_SQL = 12000
ALLOWED_NODES = frozenset(
    "Select From Table TableAlias Identifier Column Alias Literal Star Count Order Ordered Limit Where EQ NEQ GT GTE LT LTE And Or Not Is Null Boolean In Between Like ILike Group Having Join Sum Avg Min Max Add Sub Mul Div Mod Paren Distinct With CTE Subquery Union Intersect Except Exists Cast DataType Round Coalesce Nullif Abs Lower Upper DateTrunc TimestampTrunc Extract Var Neg Case If".split()
)
ALLOWED_FUNCTIONS = frozenset(
    "And Or Count Sum Avg Min Max Cast Round Coalesce Nullif Abs Lower Upper DateTrunc TimestampTrunc Extract Case If".split()
)
ALLOWED_TYPES = frozenset(
    ("DATE", "TIMESTAMP", "TIMESTAMPTZ", "INT", "BIGINT", "DECIMAL", "DOUBLE", "TEXT", "VARCHAR", "BOOLEAN")
)


class PolicyError(ValueError):
    pass


@dataclass(frozen=True)
class ReviewedSQL:
    sql: str


def _check(tree):
    nodes = list(tree.walk())
    if len(nodes) > 300 or max(n.depth for n in nodes) > 18:
        raise PolicyError("Query complexity exceeds policy")
    if len(list(tree.find_all(exp.Join))) > 4:
        raise PolicyError("Too many joins")
    for node in nodes:
        kind = type(node).__name__
        if kind not in ALLOWED_NODES:
            raise PolicyError("SQL construct is not allowed")
        if isinstance(node, exp.Func) and kind not in ALLOWED_FUNCTIONS:
            raise PolicyError("Function is not allowed")
        if isinstance(node, exp.Identifier) and not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,62}", node.name):
            raise PolicyError("Identifier is not allowed")
        if isinstance(node, exp.Join):
            on = node.args.get("on")
            if (
                not isinstance(on, exp.EQ)
                or not isinstance(on.left, exp.Column)
                or not isinstance(on.right, exp.Column)
                or on.left.table == on.right.table
            ):
                raise PolicyError("Join requires an explicit column equality between aliases")
        if isinstance(node, exp.Star) and not isinstance(node.parent, exp.Count):
            raise PolicyError("Select explicit approved columns, not stars")
        if isinstance(node, exp.DataType) and (node.this.value not in ALLOWED_TYPES or node.args.get("kind")):
            raise PolicyError("Type is not allowed")
        if isinstance(node, exp.Column) and (node.db or node.catalog):
            raise PolicyError("Column qualification is not allowed")
        if isinstance(node, exp.With) and node.args.get("recursive"):
            raise PolicyError("Recursive queries are not allowed")
        if isinstance(node, exp.Literal) and len(node.this) > 1000:
            raise PolicyError("Literal is too large")
        if isinstance(node, exp.Select) and any(
            node.args.get(k) for k in ("into", "locks", "operation_modifiers")
        ):
            raise PolicyError("Select modifier is not allowed")
    for scope in traverse_scope(tree):
        for _, source in scope.sources.items():
            if isinstance(source, Scope):
                continue
            if not isinstance(source, exp.Table) or not isinstance(source.this, exp.Identifier):
                raise PolicyError("Only approved physical tables are allowed")
            if source.catalog or source.db not in ("", "analytics") or source.name not in TABLES:
                raise PolicyError("Table is not approved")
        for column in scope.columns:
            if column.table:
                source = scope.sources.get(column.table)
                if isinstance(source, exp.Table) and column.name not in TABLES.get(source.name, {}):
                    raise PolicyError("Column is not approved")


def review_sql(sql: str) -> ReviewedSQL:
    if not isinstance(sql, str) or not sql.strip() or len(sql) > MAX_SQL:
        raise PolicyError("SQL size exceeds policy")
    try:
        statements = sqlglot.parse(sql, read="postgres")
        if len(statements) != 1 or not isinstance(
            statements[0], (exp.Select, exp.Union, exp.Intersect, exp.Except)
        ):
            raise PolicyError("Exactly one read-only query is required")
        tree = statements[0]
        _check(tree)
        tree = qualify(
            tree,
            dialect="postgres",
            db="analytics",
            schema={"analytics": TABLES},
            expand_stars=False,
            validate_qualify_columns=True,
        )
        _check(tree)
        limit = tree.args.get("limit")
        cap = MAX_ROWS
        if limit:
            value = limit.expression
            if not isinstance(value, exp.Literal) or not value.is_int or int(value.this) < 0:
                raise PolicyError("Literal nonnegative limit required")
            cap = min(cap, int(value.this))
        tree = tree.limit(cap, copy=False)
        _check(tree)
        return ReviewedSQL(tree.sql(dialect="postgres", comments=False))
    except PolicyError:
        raise
    except Exception:
        raise PolicyError("SQL could not be safely resolved") from None
