import collections
import typing

from django.core.exceptions import ValidationError

from import_export import results


class Error(results.Error):
    """Customization of over base Error class from import export."""

    def __repr__(self) -> str:
        """Return object representation in string format."""
        return f"Error({self.error})"

    def __reduce__(self):
        """Simplify Exception object for pickling.

        `error` object may contain not picklable objects (for example, django's
        lazy text), so here it replaced with simple string.

        """
        self.error = str(self.error)
        return super().__reduce__()


class RowResult(results.RowResult):
    """Custom row result class with ability to store skipped errors in row."""

    def __init__(self) -> None:
        """Copy of base init except creating validation error field."""
        self.non_field_skipped_errors: list[results.Error] = []
        self.field_skipped_errors: dict[str, list[ValidationError]] = dict()
        self.errors: list[Error] = []
        self.diff: list[str] | None = None
        self.import_type = None
        self.row_values: dict[str, typing.Any] = {}
        self.object_id = None
        self.object_repr = None
        self.instance = None
        self.original = None
        # variable to store modified value of ValidationError
        self._validation_error: ValidationError | None = None

    @property
    def validation_error(self) -> ValidationError | None:
        """Return modified validation error."""
        return self._validation_error

    @validation_error.setter
    def validation_error(self, value: ValidationError) -> None:
        """Modify passed error to reduce count of nested exception classes.

        Result class is saved in `ImportJob` model as pickled field
        and python's `pickle` can't handle
        `ValidationError` with high level of nested errors,
        therefore we reduce nesting by using string value of nested errors.

        If `ValidationError` has no `message_dict` attr,
        then it means that there're no nested exceptions
        and we can safely save it.

        Otherwise, we will go through all nested validation errors
        and build new `ValidationError` with only one level of
        nested `ValidationError` instances.

        """
        if not hasattr(value, "message_dict"):
            self._validation_error = value
            return
        result = collections.defaultdict(list)
        for field, error_messages in value.message_dict.items():
            validation_errors = [
                ValidationError(message=message, code="invalid")
                for message in error_messages
            ]
            result[field].extend(validation_errors)
        self._validation_error = ValidationError(result)

    @property
    def has_skipped_errors(self) -> bool:
        """Return True if row contain any skipped errors."""
        return bool(
            len(self.non_field_skipped_errors) > 0
            or len(self.field_skipped_errors) > 0,
        )

    @property
    def skipped_errors_count(self) -> int:
        """Return count of skipped errors."""
        return len(self.non_field_skipped_errors) + len(
            self.field_skipped_errors,
        )

    @property
    def has_error_import_type(self) -> bool:
        """Return true if import type is not valid."""
        return self.import_type not in self.valid_import_types


class Result(results.Result):
    """Custom result class with ability to store info about skipped rows."""

    @property
    def has_skipped_rows(self) -> bool:
        """Return True if contain any skipped rows."""
        return bool(any(row.has_skipped_errors for row in self.rows))

    @property
    def skipped_rows(self) -> list[RowResult]:
        """Return all rows with skipped errors."""
        return list(
            filter(lambda row: row.has_skipped_errors, self.rows),
        )
