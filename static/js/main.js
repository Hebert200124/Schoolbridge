document.addEventListener('DOMContentLoaded', function() {
    setTimeout(function() {
        document.querySelectorAll('.alert').forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            setTimeout(function() { bsAlert.close(); }, 5000);
        });
    }, 100);
});
