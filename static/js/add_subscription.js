document.addEventListener("DOMContentLoaded", function () {

    // Beautiful date picker
    flatpickr("input[type='date']", {

        dateFormat: "Y-m-d",

        allowInput: false,

        clickOpens: true,

        disableMobile: true

    });

    // Enter key navigation
    const fields = document.querySelectorAll(
        "input, select"
    );

    fields.forEach((field, index) => {

        field.addEventListener("keydown", function (e) {

            if (e.key === "Enter") {

                e.preventDefault();

                if (index + 1 < fields.length) {
                    fields[index + 1].focus();
                }

            }

        });

    });

});