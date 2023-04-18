import os
import re
import typing
import unicodedata
from urllib.parse import unquote_plus

from django.conf import settings
from django.core.files.base import ContentFile
from django.db.models import Q

import requests
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE


def normalize_string_value(value: str) -> str:
    """Normalize string value.

    1. Remove leading and trailing whitespaces.
    2. Replace all space characters (' \t\n\r\x0b\x0c') with the Space char.
    3. Remove Unicode C0 controls to prevent problems with the creation of
    XLS(X) files with `openpyxl` lib.
    4. Normalize Unicode string, using `NFKC` form. See the details:
    https://docs.python.org/3/library/unicodedata.html#unicodedata.normalize

    """
    cleaned = " ".join(value.strip().split()).strip()
    return remove_illegal_characters(cleaned)


def get_default_file_mime_type() -> str:
    """Return default MIME type."""
    return settings.MIME_TYPES_MAP[".bin"]


def get_mime_type_by_file_url(file_url: str) -> str:
    """Retrieve file's mime type by file's url according to `MIME_TYPES_MAP`.

    If file extension not in `MIME_TYPES_MAP` it returns default mime type
    for binary files

    """
    file_extension = f".{get_file_extension(file_url)}"
    if file_extension in settings.MIME_TYPES_MAP:
        return settings.MIME_TYPES_MAP[file_extension]

    return get_default_file_mime_type()


def download_file(external_url: str) -> ContentFile:
    """Download file from external resource and return the file object."""
    mime_type = get_mime_type_by_file_url(external_url)
    data = requests.get(external_url)
    file = ContentFile(data.content)
    file.content_type = mime_type
    return file


def get_file_extension(url: str, lower: bool = True) -> str:
    """Extract file extension from path/URL.

    Args:
        url (str): Path to the file
        lower (boolean): Extension in lower
    Returns:
        String: extension of the file (lower or not)

    Example:
        'dir/subdir/file.ext' -> 'ext'

    """
    get_index = url.find("?")
    if get_index != -1:
        url = url[:get_index]  # remove GET params from URL
    ext = os.path.splitext(url)[1][1:]
    return ext.lower() if lower else ext


def remove_illegal_characters(value: str) -> str:
    """Remove `illegal` characters from string values.

    1. Remove Unicode C0 controls to prevent problems with the creation of
    XLS(X) files with `openpyxl` lib.
    2. Normalize Unicode string, using `NFKC` form. See the details:
    https://docs.python.org/3/library/unicodedata.html#unicodedata.normalize

    """
    return unicodedata.normalize(
        "NFKC",
        re.sub(ILLEGAL_CHARACTERS_RE, "", value),
    )


def get_clear_q_filter(str_value: str, attribute_name: str) -> Q:
    """Make clear Q filter for ``str_value``.

    For given string we must create regex pattern that isn't
    dependent on word's cases and extra whitespaces.

    First we build regular expression for ``str_value``
        Example:
            if str_value = 'Hello, world' then regex patter for it
            is r'^Hello\s+world$'

    Then for regex pattern we create Q filter.
        Example:
            If attribute_name is 'title' then Q filter is
            Q(title__iregex=r'^Hello\s+world$')

    Args:
        str_value: some string
        attribute_name: model's attribute name

    """  # noqa: W605
    q_regex_attr = f"{attribute_name}__iregex"

    words = [re.escape(value) for value in str_value.split()]
    pattern = r"\s+".join(words)
    pattern = r"^{0}$".format(pattern)

    return Q(**{q_regex_attr: pattern})


def clean_sequence_of_string_values(
    sequence: typing.Iterable[str],
    ignore_empty: bool = True,
) -> list[str]:
    """Clean sequence of string values.

    Normalize each string value.
    Remove empty items form sequence if `ignore_empty` is True.

    Args:
        sequence: list of strings
        ignore_empty: boolean value which defines should empty strings be
        removed from sequence or not

    Returns:
        cleared_sequence: list of cleared sequence items

    """
    sequence = (normalize_string_value(item) for item in sequence)
    if ignore_empty:
        return list(filter(None, sequence))

    return list(sequence)


def url_to_internal_value(file_url: str) -> str:
    """Convert file url to internal value."""
    file_url = unquote_plus(file_url)
    # manually remove scheme and domain parts, because file name may
    # contain '#' or '?' and they parsed incorrectly
    file_url = file_url.split("://")[-1]
    file_url_components = file_url.split("/")[1:]
    file_url = "/".join(file_url_components)

    if file_url.startswith(settings.MEDIA_URL[1:]):
        # In case of local storing crop the media prefix
        file_url = file_url[len(settings.MEDIA_URL) - 1:]

    elif (
        getattr(settings, "AWS_STORAGE_BUCKET_NAME", None)
        and settings.AWS_STORAGE_BUCKET_NAME in file_url
    ):
        # In case of S3 upload crop S3 bucket name
        file_url = file_url.split(f"{settings.AWS_STORAGE_BUCKET_NAME}/")[-1]

    return file_url
