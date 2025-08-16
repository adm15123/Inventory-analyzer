function changeList(selectedList) {
  const baseUrl = typeof baseMaterialUrl !== 'undefined' ? baseMaterialUrl : '';
  window.location.href = baseUrl + '?list=' + selectedList;
}

function recalcRow(row) {
  const lp = parseFloat(row.querySelector('input.last-price').value) || 0;
  const qty = parseFloat(row.querySelector('input.quantity').value) || 0;
  row.querySelector('.total').innerText = (lp * qty).toFixed(2);
}

function currentListId() {
  const lookup = document.getElementById('lookupSupply').value;
  return lookup === 'supply3' ? 'supply3List' :
    lookup === 'supply2' ? 'supply2List' : 'supply1List';
}

function updateListAttributes() {
  const listId = currentListId();
  document.querySelectorAll('.product').forEach(p => p.setAttribute('list', listId));
}

function attachRowEvents(row) {
  const qty = row.querySelector('input.quantity');
  if (qty) {
    qty.addEventListener('change', function () { recalcRow(row); });
  }
  const prod = row.querySelector('.product');
  if (prod) {
    prod.setAttribute('list', currentListId());
    prod.addEventListener('change', function () {
      const val = this.value.trim().toLowerCase();
      const lookup = document.getElementById('lookupSupply').value;
      const prodArray =
        lookup === 'supply3' ? supply3Products :
        lookup === 'supply2' ? supply2Products :
        supply1Products;
      const matches = prodArray.filter(p => (p.Description || p.description || '').toLowerCase() === val);
      if (matches.length) {
        const latest = matches.reduce((a, b) => new Date(b.Date || b.date) > new Date(a.Date || a.date) ? b : a);
        row.querySelector('input.last-price').value = latest['Price per Unit'] || latest['price per unit'] || latest.Price || latest.price;
        const unitInput = row.querySelector('input.unit');
        if (unitInput) { unitInput.value = latest.Unit || latest.unit || ''; }
        recalcRow(row);
      }
    });
  }
  const lp = row.querySelector('input.last-price');
  if (lp) {
    lp.addEventListener('change', function () { recalcRow(row); });
  }
  const rm = row.querySelector('.remove-item');
  if (rm) {
    rm.addEventListener('click', function () { row.remove(); });
  }
}

function updatePredeterminedRows() {
  const lookup = document.getElementById('lookupSupply').value;
  const prodArray =
    lookup === 'supply3' ? supply3Products :
    lookup === 'supply2' ? supply2Products :
    supply1Products;
  const rows = document.querySelectorAll('#material-list tr.predetermined');
  rows.forEach(function (r) {
    const desc = r.querySelector('.product').value.trim().toLowerCase();
    const matches = prodArray.filter(p => (p.Description || p.description || '').toLowerCase() === desc);
    if (matches.length) {
      const latest = matches.reduce((a, b) => {
        const da = new Date(a.Date || a.date);
        const db = new Date(b.Date || b.date);
        return db > da ? b : a;
      });
      r.querySelector('input.last-price').value = latest['Price per Unit'] || latest['price per unit'] || latest.Price || latest.price;
      const unitInput = r.querySelector('input.unit');
      if (unitInput) { unitInput.value = latest.Unit || latest.unit || ''; }
      recalcRow(r);
    }
  });
  updateListAttributes();
}

document.addEventListener('DOMContentLoaded', function () {
  updatePredeterminedRows();
  updateListAttributes();
  document.getElementById('lookupSupply').addEventListener('change', function () {
    updatePredeterminedRows();
    updateListAttributes();
  });
  const predRows = document.querySelectorAll('#material-list tr.predetermined');
  predRows.forEach(r => attachRowEvents(r));
  new Sortable(document.getElementById('material-list'), {
    handle: '.drag-handle',
    animation: 150
  });
  document.getElementById('add-item').addEventListener('click', function () {
    const table = document.getElementById('material-list');
    const row = table.insertRow();
    row.innerHTML = '<td><input type="number" class="form-control quantity" placeholder="Quantity"></td>' +
      '<td><input type="text" class="form-control product" placeholder="Enter product" list="' + currentListId() + '"></td>' +
      '<td><input type="text" class="form-control unit" placeholder="Unit"></td>' +
      '<td><input type="number" step="0.01" class="form-control last-price" placeholder="Last price"></td>' +
      '<td class="total">0.00</td>' +
      '<td><span class="btn btn-secondary drag-handle" aria-label="Drag"><i class="bi bi-arrows-move"></i></span> ' +
      '<button type="button" class="btn btn-danger remove-item" aria-label="Remove"><i class="bi bi-trash"></i></button></td>';
    attachRowEvents(row);
    updateListAttributes();
  });
  document.getElementById('export-pdf').addEventListener('click', function () {
    const includePrice = confirm('Would you like to include the price in the PDF?');
    document.getElementById('include_price').value = includePrice ? 'yes' : 'no';
    const productData = [];
    const rows = document.querySelectorAll('#material-list tr');
    rows.forEach(function (r) {
      const product = r.querySelector('.product').value;
      const unit = r.querySelector('input.unit').value;
      const lastPrice = r.querySelector('input.last-price').value;
      const quantity = r.querySelector('input.quantity').value;
      const total = r.querySelector('.total').innerText;
      productData.push({ description: product, unit: unit, last_price: lastPrice, quantity: quantity, total: total });
    });
    document.getElementById('product_data').value = JSON.stringify(productData);
    document.getElementById('material-form').submit();
  });
  document.getElementById('save-template').addEventListener('click', function () {
    const name = document.getElementById('template-name').value.trim();
    if (!name) { alert('Template name required'); return; }
    const rows = document.querySelectorAll('#material-list tr');
    const productData = [];
    rows.forEach(function (r) {
      const product = r.querySelector('.product').value;
      const unit = r.querySelector('input.unit').value;
      const lastPrice = r.querySelector('input.last-price').value;
      const quantity = r.querySelector('input.quantity').value;
      const total = r.querySelector('.total').innerText;
      productData.push({ description: product, unit: unit, last_price: lastPrice, quantity: quantity, total: total });
    });
    fetch('/save_template', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: 'template_name=' + encodeURIComponent(name) + '&product_data=' + encodeURIComponent(JSON.stringify(productData))
    }).then(() => location.reload());
  });
});
