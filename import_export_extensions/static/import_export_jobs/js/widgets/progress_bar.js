/*
  Script is used to update progress bar value using get requests to url:

   /admin/import_export_extensions/importjob/<job_id>/progress/

  This script is used in two places:

    - ``ProgressBarWidget`` that adds progress bar to ModelAdmin.
    - ``import_job_status_view`` and ``export_job_status_view`` that
    displays current job status

*/

// GET requests interval in milliseconds
const requestInterval = 1000;

// Job statuses that mean that job is completed
const jobIsCompleted = [
  'Cancelled',
  'Parsed',
  'Imported',
  'Input_Error',
  'Parse_Error',
  'Exported',
  'Export_Error',
];

(function($) {
  $(document).ready(function() {
    // Retrieve URL for `data-url` attribute of `progress_bar`
    const progressBar = $('#progress-bar');
    if (!progressBar) {
      return;
    }
    const url = progressBar.data('url');

    if (!url) {
      return;
    }

    function updateProgressBarValue(url) {
      // Retrieve URL for `data-url` attribute of `progress-bar`
      $.get(url, function(data) {
        if ($.inArray(data.status, jobIsCompleted) !== -1) {
          // If job is completed -- reload the page
          location.reload();
        } else {
          $('#current-job-status').html(data.status);
          // If job isn't completed -- update progress bar and current status
          if (data.percent !== undefined) {
            progressBar.val(data.percent);
            progressBar.attr("data-label",  data.current + '/' + data.total + ' (' +data.percent + '%)');
          }
          // Reset function timeout
          setTimeout(updateProgressBarValue, requestInterval, url);
        }
      });
    }
    updateProgressBarValue(url);
  });
}(django.jQuery));
