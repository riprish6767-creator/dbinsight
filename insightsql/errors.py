class InsightSQLError(Exception):
    """Base class for expected, safe-to-display application errors."""


class ConfigurationError(InsightSQLError):
    pass


class GenerationError(InsightSQLError):
    pass


class SQLValidationError(InsightSQLError):
    pass


class QueryExecutionError(InsightSQLError):
    pass
