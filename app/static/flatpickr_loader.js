// Flatpickr loader for date-only pickers on activity form
// Requires flatpickr to be loaded in the page

document.addEventListener('DOMContentLoaded', function() {
    if (window.flatpickr) {
        flatpickr("input[name='start_date']", {
            dateFormat: "Y-m-d",
            allowInput: true,
            altInput: true,
            altFormat: "F j, Y",
        });
        flatpickr("input[name='end_date']", {
            dateFormat: "Y-m-d",
            allowInput: true,
            altInput: true,
            altFormat: "F j, Y",
        });
    }
});
