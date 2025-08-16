function initDataTable(selector, pageLength) {
  if (window.jQuery && $.fn.DataTable) {
    if ($.fn.DataTable.isDataTable(selector)) {
      $(selector).DataTable().destroy();
    }
    $(selector).DataTable({
      pageLength: pageLength,
      lengthMenu: [[pageLength, 50, 100, -1], [pageLength, 50, 100, 'All']]
    });
  }
}

document.addEventListener('DOMContentLoaded', function () {
  const table = document.getElementById('data-table');
  if (table) {
    const len = parseInt(table.getAttribute('data-page-length')) || 20;
    initDataTable('#data-table', len);
  }
});
