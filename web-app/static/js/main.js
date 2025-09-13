document.addEventListener("DOMContentLoaded", function () {
  const loader = document.getElementById("loader");
  const usersTable = document.getElementById("users-table");

  // Simula caricamento di 2 secondi prima di mostrare la tabella
  setTimeout(() => {
    loader.classList.add("d-none");
    usersTable.classList.remove("d-none");

    // Mostra gradualmente ogni riga
    const rows = usersTable.querySelectorAll("tbody tr");
    rows.forEach((row, index) => {
      setTimeout(() => {
        row.classList.add("show");
      }, index * 200); // ogni 200ms una nuova riga appare
    });
  }, 2000);
});
