function initDataTable(selector, pageLength) {
  if (window.jQuery && $.fn.DataTable) {
    if ($.fn.DataTable.isDataTable(selector)) {
      $(selector).DataTable().destroy();
    }
    const options = {
      pageLength: pageLength,
      lengthMenu: [[pageLength, 50, 100, -1], [pageLength, 50, 100, 'All']]
    };
    if ($(`${selector} th.no-sort`).length) {
      options.columnDefs = [{ targets: 'no-sort', orderable: false, searchable: false }];
    }
    $(selector).DataTable(options);
  }
}

document.addEventListener('DOMContentLoaded', function () {
  const table = document.getElementById('data-table');
  if (table) {
    const len = parseInt(table.getAttribute('data-page-length')) || 20;
    initDataTable('#data-table', len);
  }
});
