import functools
import uuid


def upload_file_to(
    instance,
    filename: str,
    main_folder_name: str,
) -> str:
    """Upload instance's `file` to unique folder.

    Args:
        instance (typing.Union[ImportJob, ExportJob]): instance of job model
        main_folder_name(str): main folder -> import or export
        filename (str): file name of document's file

    Returns:
        str: Generated path for document's file.

    """
    return (
        "import_export_extensions/"
        f"{main_folder_name}/{uuid.uuid4()}/{filename}"
    )


upload_export_file_to = functools.partial(
    upload_file_to,
    main_folder_name="export",
)
upload_import_file_to = functools.partial(
    upload_file_to,
    main_folder_name="import",
)
