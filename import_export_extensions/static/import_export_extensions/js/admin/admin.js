/*
This script show/hide error detail info by clicking appropriate link:
    - imported data (show content for each column in row)
    - stacktrace if debug is True
*/
(function($) {
  $(document).ready(function() {
    const showRowData = $('.show-error-detail'),
    dataStateAttr = 'state',
    openedState = 'opened',
    closedState = 'closed';

    showRowData.click(function(e) {
      const self = $(this);
      e.preventDefault();

      const state = self.data('state');

      if (state === openedState) {
        self.parents('li').find('div').hide(500);
        self.data(dataStateAttr, closedState);
      } else {
        self.parents('li').find('div').show(500);
        self.data(dataStateAttr, openedState);
      }
    });
  });
})(django.jQuery);
