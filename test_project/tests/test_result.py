import pickle

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

import pytest

from import_export_extensions import results


@pytest.fixture
def row_result_with_skipped_errors() -> results.RowResult:
    """Create RowResult with skipped errors."""
    row_result = results.RowResult()
    row_result.non_field_skipped_errors = [results.Error("Error")]
    row_result.field_skipped_errors = {
        "title": [ValidationError("Error")],
    }
    return row_result


def test_reduce_error():
    """Test simplify exception object for pickling."""
    assert pickle.dumps(results.Error(_))


def test_result_skipped_properties(
    row_result_with_skipped_errors: results.RowResult,
):
    """Check that result properties calculate value correct."""
    result = results.Result()
    result.rows = [row_result_with_skipped_errors]
    assert result.has_skipped_rows
    assert len(result.skipped_rows) == 1


def test_row_result_properties(
    row_result_with_skipped_errors: results.RowResult,
):
    """Check that row result properties calculate value correct."""
    assert row_result_with_skipped_errors.has_skipped_errors
    assert row_result_with_skipped_errors.skipped_errors_count == 2
