from django.core.exceptions import ValidationError

from import_export import results


class Error(results.Error):
    """Customization of over base Error class from import export."""

    def __repr__(self) -> str:
        """Return object representation in string format."""
        return f"Error({self.error})"

    def __reduce__(self):
        """Simplify Exception object for pickling.

        `error` object may contain not pickable objects (for example, django's
        lazy text), so here it replaced with simple string.

        """
        self.error = str(self.error)
        return super().__reduce__()


class RowResult(results.RowResult):
    """Custom row result class with ability to store skipped errors in row."""
    def __init__(self):
        self.non_field_skipped_errors: list[Error] = []
        self.field_skipped_errors: dict[str, list[ValidationError]] = dict()
        super().__init__()

    @property
    def has_skipped_errors(self) -> bool:
        """Return True if row contain any skipped errors."""
        if len(self.non_field_skipped_errors) > 0 or len(self.field_skipped_errors) > 0:
            return True
        return False

    @property
    def skipped_errors_count(self) -> int:
        """Return count of skipped errors."""
        return (
            len(self.non_field_skipped_errors)
            + len(self.field_skipped_errors)
        )

    @property
    def has_error_import_type(self) -> bool:
        """Return true if import type is not valid."""
        if self.import_type not in self.valid_import_types:
            return True
        return False


class Result(results.Result):
    """Custom result class with ability to store info about skipped rows."""

    @property
    def has_skipped_rows(self) -> bool:
        """Return True if contain any skipped rows."""
        if any(row.has_skipped_errors for row in self.rows):
            return True
        return False

    @property
    def skipped_rows(self) -> list[RowResult]:
        """Return all rows with skipped errors."""
        return list(
            filter(lambda row: row.has_skipped_errors, self.rows),
        )
