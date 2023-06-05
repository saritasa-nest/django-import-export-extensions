(function($) {
  $(document).ready(function() {
    const exportForm = $('#export-form');
    const formatField = exportForm.find('select[name="file_format"]'),
    resourceField = exportForm.find('select[name="resource"]');
    const formatData = JSON.parse($("#format-data").text());

    if (Object.keys(formatData).length > 0) {
      resourceField.on("change", function() {
        const selectedResourceIndex = resourceField.val();
        const selectedResourceFormats = formatData[selectedResourceIndex];

        formatField.empty();
        formatField.append(`<option value>---</option>`);
        selectedResourceFormats.forEach((format, index) => {
          const selected = format === "xlsx" ? "selected" : "";
          const formatOption = `<option value=${index.toString()} ${selected}>${format}</option>`;
          formatField.append(formatOption);
        });
      });
    }
  });
})(django.jQuery);
