// Fills in the contact e-mail at load time so the address is not present as
// plain text in the served HTML (basic protection against address harvesters).
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll("[data-mail-user]").forEach(function (el) {
    var addr = el.dataset.mailUser + "@" + el.dataset.mailDomain;
    el.setAttribute("href", "mailto:" + addr);
    if (el.hasAttribute("data-mail-show")) el.textContent = addr;
  });
});
