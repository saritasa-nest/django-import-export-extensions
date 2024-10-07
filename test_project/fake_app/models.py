from django.db import models
from django.utils.translation import gettext_lazy as _


class Instrument(models.Model):
    """Model representing Instrument."""

    title = models.CharField(max_length=100)

    class Meta:
        verbose_name = _("Instrument")
        verbose_name_plural = _("Instruments")

    def __str__(self) -> str:
        """Return string representation."""
        return self.title


class Artist(models.Model):
    """Model representing artist."""

    name = models.CharField(max_length=100, unique=True)
    bands = models.ManyToManyField(
        "Band",
        through="Membership",
        related_name="artists",
    )

    instrument = models.ForeignKey(
        Instrument,
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = _("Artist")
        verbose_name_plural = _("Artists")

    def __str__(self) -> str:
        """Return string representation."""
        return self.name


class Band(models.Model):
    """Model representing band."""

    title = models.CharField(max_length=100)

    class Meta:
        verbose_name = _("Band")
        verbose_name_plural = _("Bands")

    def __str__(self) -> str:
        """Return string representation."""
        return self.title


class Membership(models.Model):
    """Model representing membership."""

    artist = models.ForeignKey(
        Artist,
        on_delete=models.CASCADE,
    )
    band = models.ForeignKey(
        Band,
        on_delete=models.CASCADE,
    )
    date_joined = models.DateField()

    class Meta:
        verbose_name = _("Membership")
        verbose_name_plural = _("Memberships")

    def __str__(self) -> str:
        """Return string representation."""
        return f"<{self.artist}> joined <{self.band}> on <{self.date_joined}>"
