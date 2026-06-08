// PASTI DIEKSEKUSI SETELAH HALAMAN LOAD
document.addEventListener("DOMContentLoaded", function () {

    window.openModal = function () {
        const modal = document.getElementById("addModal");
        console.log("openModal dipanggil", modal);
        if (modal) {
            modal.style.display = "flex";
        }
    };

    window.closeModal = function () {
        const modal = document.getElementById("addModal");
        if (modal) {
            modal.style.display = "none";
        }
    };

});
