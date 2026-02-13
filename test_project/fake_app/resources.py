from import_export.resources import ModelResource

from import_export_extensions.fields import IntermediateManyToManyField
from import_export_extensions.resources import (
    CeleryModelResource,
    ResourceMixin,
)
from import_export_extensions.widgets import IntermediateManyToManyWidget

from .filters import ArtistFilterSet
from .models import Artist, Band


class DjangoTasksArtisResource(ResourceMixin, ModelResource):
    """Artist resource with simple fields.

    Use the django.tasks module for async operations.

    """

    filterset_class = ArtistFilterSet

    class Meta:
        model = Artist
        import_id_fields = ["external_id"]
        clean_model_instances = True
        fields = [
            "id",
            "external_id",
            "name",
            "instrument",
        ]
        # Enable background export/import
        use_django_tasks = True

    def initialize_task_state(
        self,
        state: str,
        queryset,
        task_id: str = ""
    ):
        """"""
        # TODO(otto): add logic or left empty
        print("doesnt problem")
        try:
            from rq import get_current_job  # type: ignore
        except Exception:  # pragma: no cover
            return

        import django_rq
        from rq.job import Job

        print("task id ???")

        connection = django_rq.get_connection()
        job = Job.fetch(self.task_id, connection=connection)
        print(job)
        if job is None:
            return

        try:
            total = queryset.count()
        except Exception:
            total = len(queryset)

        self.total_objects_count = int(total)

        job.meta["total"] = self.total_objects_count
        job.meta["current"] = self.current_object_number
        job.save_meta()

        print(job.get_meta())


    def update_task_state(
        self,
        state: str,
    ):
        """"""
        # TODO(otto): add logic or left empty

        self.current_object_number += 1

        is_reached_update_count = (
            self.current_object_number % self.status_update_row_count == 0
        )
        is_last_object = self.current_object_number == self.total_objects_count

        if is_reached_update_count or is_last_object:
            import django_rq
            from rq.job import Job

            connection = django_rq.get_connection()
            job = Job.fetch(self.task_id, connection=connection)

            if job is None:
                return

            job.meta["total"] = self.total_objects_count
            job.meta["current"] = self.current_object_number
            job.save_meta()


class SimpleArtistResource(CeleryModelResource):
    """Artist resource with simple fields."""

    filterset_class = ArtistFilterSet

    class Meta:
        model = Artist
        import_id_fields = ["external_id"]
        clean_model_instances = True
        fields = [
            "id",
            "external_id",
            "name",
            "instrument",
        ]


class ArtistResourceWithM2M(CeleryModelResource):
    """Artist resource with Many2Many field."""

    bands = IntermediateManyToManyField(
        attribute="bands",
        column_name="Bands he played in",
        widget=IntermediateManyToManyWidget(
            rem_model=Band,
            rem_field="title",
            extra_fields=["date_joined"],
            instance_separator=";",
        ),
    )

    class Meta:
        model = Artist
        clean_model_instances = True
        fields = ["id", "name", "bands", "instrument"]

    def get_queryset(self):
        """Return a queryset."""
        return (
            super()
            .get_queryset()
            .prefetch_related(
                "membership_set__band",
                "bands",
            )
        )


class BandResourceWithM2M(CeleryModelResource):
    """Band resource with Many2Many field."""

    artists = IntermediateManyToManyField(
        attribute="artists",
        column_name="Artists in band",
        widget=IntermediateManyToManyWidget(
            rem_model=Artist,
            rem_field="name",
            extra_fields=["date_joined"],
            instance_separator=";",
        ),
    )

    class Meta:
        model = Band
        clean_model_instances = True
        fields = ["id", "title", "artists"]

    def get_queryset(self):
        """Return a queryset."""
        return (
            super()
            .get_queryset()
            .prefetch_related(
                "membership_set__artist",
                "artists",
            )
        )
