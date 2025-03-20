from django import dispatch

import_job_failed = dispatch.Signal()
export_job_failed = dispatch.Signal()
