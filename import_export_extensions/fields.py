from django.db.models.fields.reverse_related import ManyToManyRel

from import_export.fields import Field


class IntermediateManyToManyField(Field):
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

        m2m_rel, _, _ = self.get_relation_field_params(obj)

        if not obj.id:
            return m2m_rel.through.objects.none()

        through_model_accessor_name = self.get_through_model_accessor_name(
            obj,
            m2m_rel,
        )
        return getattr(obj, through_model_accessor_name).all()

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
            return m2m_rel, field_name, reversed_field_name

        # otherwise it is a forward relation
        m2m_rel = field.remote_field
        m2m_field = field
        field_name = m2m_field.m2m_field_name()
        reversed_field_name = m2m_field.m2m_reverse_field_name()
        return m2m_rel, field_name, reversed_field_name

    def get_through_model_accessor_name(self, obj, m2m_rel) -> str:
        """Shortcut to get through model accessor name."""
        for related_object in obj._meta.related_objects:
            if related_object.related_model is m2m_rel.through:
                return related_object.accessor_name

        raise ValueError(
            f"{obj._meta.model} has no relation with {m2m_rel.through}",
        )

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
            field_name,
            reversed_field_name,
        ) = self.get_relation_field_params(obj)

        # retrieve intermediate model
        # intermediate_model is the Membership model
        intermediate_model = m2m_rel.through

        # should be returned following list:
        # [{'band': <Band obj>, 'date_joined': '2016-08-18'}]
        instances_data = self.clean(data)

        # remove current related objects,
        # i.e. clear artists's band
        through_model_accessor_name = self.get_through_model_accessor_name(
            obj,
            m2m_rel,
        )
        getattr(obj, through_model_accessor_name).all().delete()

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
            intermediate_obj = intermediate_model(**obj_data)
            try:
                intermediate_obj.full_clean()
            except Exception as e:
                self._format_exception(e)
            intermediate_obj.save()
