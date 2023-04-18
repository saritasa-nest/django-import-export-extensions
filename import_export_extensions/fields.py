from django.db.models.fields.reverse_related import ManyToManyRel

from import_export.fields import Field


class M2MField(Field):
    """Base M2M field provides faster related instances import."""

    def __init__(self, *args, export_order=None, **kwargs):
        """Save additional field params.

        Args:
            export_order(str): field name that should be used for ordering
                instances during export

        """
        super().__init__(*args, **kwargs)
        self.export_order = export_order

    def _format_exception(self, exception):
        """Shortcut for humanizing exception."""
        error = str(exception)
        if hasattr(exception, "messages"):
            error = " ".join(exception.messages)

        msg = f"Column '{self.column_name}': {error}"
        raise ValueError(msg) from exception

    def get_value(self, obj):
        """Return the value of the object's attribute.

        This method should return instances of intermediate model, i.e.
        Membership instances

        """
        if self.attribute is None:
            return None

        m2m_rel, _, field_name, _ = self.get_relation_field_params(obj)

        # retrieve intermediate model
        # intermediate_model == Membership
        intermediate_model = m2m_rel.through

        # filter relations with passed object
        qs = intermediate_model.objects.filter(**{field_name: obj})
        if self.export_order:
            qs = qs.order_by(self.export_order)
        return qs

    def get_relation_field_params(self, obj):
        """Shortcut to get relation field params.

        Gets relation, field itself, its name and its reversed field name

        """
        # retrieve M2M field itself (i.e. Artist.bands)
        field = obj._meta.get_field(self.attribute)

        # if field is `ManyToManyRel` - it is a reversed relation
        if isinstance(field, ManyToManyRel):
            m2m_rel = field
            m2m_field = m2m_rel.field
            field_name = m2m_field.m2m_reverse_field_name()
            reversed_field_name = m2m_field.m2m_field_name()
            return m2m_rel, m2m_field, field_name, reversed_field_name

        # otherwise it is a forward relation
        m2m_rel = field.remote_field
        m2m_field = field
        field_name = m2m_field.m2m_field_name()
        reversed_field_name = m2m_field.m2m_reverse_field_name()
        return m2m_rel, m2m_field, field_name, reversed_field_name

    def save(self, obj, data, *args, **kwargs):
        """Delete intermediate models.

        This implementation deletes intermediate models, which were excluded
        and creates intermediate models only for newly added models.

        Parent `save` method deletes and recreates intermediate models for all
        instances which generates a lot of exceed Feed Entries, so overridden.

        """
        (
            _,
            m2m_field,
            field_name,
            reversed_field_name,
        ) = self.get_relation_field_params(obj)

        # retrieve intermediate model (AttendeeTeamMembership)
        intermediate_model = m2m_field.remote_field.through

        # should be returned following list:
        # [{'object': Instance01, 'properties': {}},
        # {'object': Instance02, 'properties': {}}]
        data = self.clean(data)

        # IDs of related instances in imported data
        imported_ids = {i["object"].id for i in data}

        # IDs of current instances
        manager = getattr(obj, self.attribute)
        current_ids = set(manager.values_list("id", flat=True))

        # Find instances to be excluded after import
        excluded_ids = current_ids - imported_ids
        intermediate_model.objects.filter(
            **{
                field_name: obj,
                f"{reversed_field_name}__id__in": excluded_ids,
            },
        ).delete()

        # Find instances to add after import
        added_ids = imported_ids - current_ids
        for instance in data:
            # process only newly added attendees
            if instance["object"].id not in added_ids:
                continue
            obj_data = instance["properties"].copy()
            obj_data.update(
                {
                    field_name: obj,
                    reversed_field_name: instance["object"],
                },
            )
            intermediate_obj = intermediate_model(**obj_data)
            try:
                intermediate_obj.full_clean()
            except Exception as exception:
                self._format_exception(exception)
            intermediate_obj.save()


class IntermediateManyToManyField(M2MField):
    """Resource field for M2M with custom ``through`` model.

    By default, ``django-import-export`` set up object attributes using
    ``setattr(obj, attribute_name, value)``, where ``value`` is ``QuerySet``
    of related model objects. But django forbid this when `ManyToManyField``
    used with custom ``through`` model.

    This field expects be used with custom widget that return not simple value,
    but dict with intermediate model attributes.

    For easy comments following models will be used:

        Artist:
            name
            bands ->

        Membership:
            artist
            band
            date_joined

        Band:
            title
            <- artists

    So this field should be used for exporting Artists with `bands` field.

    Save workflow is following:
        1. clean data (extract dicts)
        2. Remove current M2M instances of object
        3. Create new M2M instances based on current object

    """

    def save(self, obj, data, *args, **kwargs):
        """Add M2M relations for obj from data.

        Args:
            obj(model instance): object being imported
            data(OrderedDict): all extracted data for object

        Example:
            obj - Artist instance

        """
        if self.readonly:
            return

        (
            m2m_rel,
            m2m_field,
            field_name,
            reversed_field_name,
        ) = self.get_relation_field_params(obj)

        # retrieve intermediate model
        # IntermediateModel == Membership
        IntermediateModel = m2m_rel.through

        # should be returned following list:
        # [{'band': <Band obj>, 'date_joined': '2016-08-18'}]
        instances_data = self.clean(data)

        # remove current related objects,
        # i.e. clear artists's band
        IntermediateModel.objects.filter(**{field_name: obj}).delete()

        for rel_obj_data in instances_data:
            # add current and remote object to intermediate instance data
            # i.e. {'artist': <Artist obj>, 'band': rel_obj_data['properties']}
            obj_data = rel_obj_data["properties"].copy()
            obj_data.update(
                {
                    field_name: obj,
                    reversed_field_name: rel_obj_data["object"],
                },
            )
            intermediate_obj = IntermediateModel(**obj_data)
            try:
                intermediate_obj.full_clean()
            except Exception as e:
                self._format_exception(e)
            intermediate_obj.save()
