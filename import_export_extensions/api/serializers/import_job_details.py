import itertools
import typing

from rest_framework import serializers

from ... import models


class SkippedErrorsDict(typing.TypedDict):
    """Typed dict for skipped errors."""

    non_field_skipped_errors: list[str]
    field_skipped_errors: dict[str, list[str]]


class ImportParamsSerializer(serializers.Serializer):
    """Serializer for representing import parameters."""

    data_file = serializers.FileField()
    resource_path = serializers.CharField()
    resource_kwargs = serializers.CharField()


class ImportDiffSerializer(serializers.Serializer):
    """Serializer for representing importing rows diff."""

    previous = serializers.CharField(allow_blank=True, allow_null=True)
    current = serializers.CharField(allow_blank=True, allow_null=True)


class ImportRowSerializer(serializers.Serializer):
    """Serializer for representing importing rows.

    Used to generate correct openapi spec.

    """

    operation = serializers.CharField()
    parsed_fields = serializers.ListField(
        child=ImportDiffSerializer(allow_null=True),
        allow_null=True,
    )


class ImportingDataSerializer(serializers.Serializer):
    """Serializer for representing importing data."""

    headers = serializers.ListField(
        child=serializers.CharField(),
    )
    rows = serializers.ListField(
        child=ImportRowSerializer(),
    )

    def to_representation(self, instance: models.ImportJob):
        """Return dict with import details."""
        if instance.import_status not in models.ImportJob.success_statuses:
            return super().to_representation(self.get_initial())

        rows = []
        resource = instance.resource
        for row in instance.result.rows:
            original_fields = [
                resource.export_field(field, row.original)
                if row.original
                else ""
                for field in resource.get_user_visible_fields()
            ]
            current_fields = [
                resource.export_field(field, row.instance)
                for field in resource.get_user_visible_fields()
            ]

            parsed_fields = [
                {
                    "previous": original_field,
                    "current": current_field,
                }
                for original_field, current_field in itertools.zip_longest(
                    original_fields,
                    current_fields,
                    fillvalue="",
                )
            ]

            rows.append(
                {
                    "operation": row.import_type,
                    "parsed_fields": parsed_fields,
                },
            )

        importing_data = {
            "headers": instance.result.diff_headers,
            "rows": rows,
        }
        return super().to_representation(importing_data)


class TotalsSerializer(serializers.Serializer):
    """Serializer to represent import totals."""

    new = serializers.IntegerField(allow_null=True, required=False)
    update = serializers.IntegerField(allow_null=True, required=False)
    delete = serializers.IntegerField(allow_null=True, required=False)
    skip = serializers.IntegerField(allow_null=True, required=False)
    error = serializers.IntegerField(allow_null=True, required=False)

    def to_representation(self, instance):
        """Return dict with import totals."""
        if instance.import_status not in models.ImportJob.results_statuses:
            return super().to_representation(self.get_initial())
        return super().to_representation(instance.result.totals)


class RowError(serializers.Serializer):
    """Represent single row errors."""

    line = serializers.IntegerField()
    error = serializers.CharField()
    row = serializers.ListField(
        child=serializers.CharField(),
    )


class InputErrorSerializer(serializers.Serializer):
    """Represent Input errors."""

    base_errors = serializers.ListField(
        child=serializers.CharField(),
    )
    row_errors = serializers.ListField(
        child=serializers.ListField(
            child=RowError(),
        ),
    )

    def to_representation(self, instance: models.ImportJob):
        """Return dict with input errors."""
        if instance.import_status not in models.ImportJob.results_statuses:
            return super().to_representation(self.get_initial())

        input_errors: dict[str, list[typing.Any]] = {
            "base_errors": [],
            "row_errors": [],
        }

        if instance.result.base_errors:
            input_errors["base_errors"] = [
                str(error.error) for error in instance.result.base_errors
            ]

        if instance.result.row_errors():
            for line, errors in instance.result.row_errors():
                line_errors = [
                    {
                        "line": line,
                        "error": str(error.error),
                        "row": error.row.values(),
                    }
                    for error in errors
                ]
                input_errors["row_errors"].append(line_errors)

        return super().to_representation(input_errors)


class IsAllRowsShowField(serializers.BooleanField):
    """Field for representing `all_rows_saved` value."""

    def to_representation(self, instance):
        """Return boolean if all rows shown in importing data."""
        if instance.import_status not in models.ImportJob.success_statuses:
            return False
        return instance.result.total_rows == len(instance.result.rows)


class SkippedErrorsSerializer(serializers.Serializer):
    """Serializer for import job skipped rows."""

    non_field_skipped_errors = serializers.ListField(
        child=serializers.CharField(),
    )
    field_skipped_errors = serializers.DictField(
        child=serializers.ListField(child=serializers.CharField()),
    )

    def to_representation(self, instance: models.ImportJob):
        """Parse skipped errors from import job result."""
        if instance.import_status not in models.ImportJob.results_statuses:
            return super().to_representation(self.get_initial())
        skipped_errors: SkippedErrorsDict = {
            "non_field_skipped_errors": [],
            "field_skipped_errors": {},
        }
        for row in instance.result.skipped_rows:
            non_field_errors = [
                error.error for error in row.non_field_skipped_errors
            ]
            skipped_errors["non_field_skipped_errors"].extend(non_field_errors)
            for field, errors in row.field_skipped_errors.items():
                errors = [error.messages for error in errors]
                skipped_errors["field_skipped_errors"][field] = errors
        return super().to_representation(skipped_errors)
