document.addEventListener("DOMContentLoaded", function () {

    const cityInput = document.querySelector("input[name='city']");
    const keywordInput = document.querySelector("input[name='keyword']");
    const table = document.querySelector("table tbody");
    const rows = Array.from(table.querySelectorAll("tr"));

    function filterTable() {
        const cityFilter = cityInput.value.toLowerCase();
        const keywordFilter = keywordInput.value.toLowerCase();

        rows.forEach(row => {
            const username = row.cells[0].textContent.toLowerCase();
            const bio = row.cells[1].textContent.toLowerCase();
            const location = row.cells[2].textContent.toLowerCase();

            const cityMatch = cityFilter === "" || location.includes(cityFilter);
            const keywordMatch = keywordFilter === "" || username.includes(keywordFilter) || bio.includes(keywordFilter);

            if (cityMatch && keywordMatch) {
                row.style.display = "";
            } else {
                row.style.display = "none";
            }
        });
    }

    cityInput.addEventListener("input", filterTable);
    keywordInput.addEventListener("input", filterTable);
});
