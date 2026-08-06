document.addEventListener('DOMContentLoaded', function() {
    setTimeout(function() {
        document.querySelectorAll('.alert').forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            setTimeout(function() { bsAlert.close(); }, 5000);
        });
    }, 100);
});

function togglePassword(fieldId) {
    var field = document.getElementById(fieldId);
    var icon = document.getElementById(fieldId + '-icon');
    if (field.type === 'password') {
        field.type = 'text';
        if (icon) icon.classList.replace('bi-eye', 'bi-eye-slash');
    } else {
        field.type = 'password';
        if (icon) icon.classList.replace('bi-eye-slash', 'bi-eye');
    }
}

function confirmDelete(form) {
    var msg = form.getAttribute('data-confirm-msg');
    return window.confirm(msg || 'Are you sure?');
}

document.addEventListener('submit', function(e) {
    var form = e.target;
    if (!form || form.tagName !== 'FORM') return;
    if (form.querySelector('input[name="_csrf_token"]')) return;
    var meta = document.querySelector('meta[name="csrf-token"]');
    if (!meta) return;
    var input = document.createElement('input');
    input.type = 'hidden';
    input.name = '_csrf_token';
    input.value = meta.getAttribute('content');
    form.appendChild(input);
});
