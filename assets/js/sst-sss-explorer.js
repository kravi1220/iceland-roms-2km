(function () {
  async function main() {
    const manifest = await loadJSON("data/sst_sss_dates.json");
    const dates = manifest.dates.map((d) => d.date);

    const slider = document.getElementById("date-slider");
    const varSel = document.getElementById("sst-sss-var-select");
    const dateLabel = document.getElementById("date-label");
    const img = document.getElementById("sst-sss-img");
    const prevBtn = document.getElementById("date-prev");
    const nextBtn = document.getElementById("date-next");
    const satDateNote = document.getElementById("sat-date-note");

    slider.min = 0;
    slider.max = dates.length - 1;
    slider.value = dates.length - 1;

    function render() {
      const i = parseInt(slider.value, 10);
      const date = dates[i];
      const variable = varSel.value;
      dateLabel.textContent = date;
      img.src = `assets/img/sst_sss/${variable}_${date}.png`;
      const rec = manifest.dates[i];
      const satKey = variable === "sst" ? "avhrr_date" : "cmems_date";
      const satLabel = variable === "sst" ? "AVHRR" : "CMEMS SSS";
      satDateNote.textContent = rec[satKey] === date
        ? `Satellite (${satLabel}) matched exactly to ${date}.`
        : `Satellite (${satLabel}) date nearest to ${date} is ${rec[satKey]}.`;
    }

    slider.addEventListener("input", render);
    varSel.addEventListener("change", render);
    prevBtn.addEventListener("click", () => {
      slider.value = Math.max(0, parseInt(slider.value, 10) - 1);
      render();
    });
    nextBtn.addEventListener("click", () => {
      slider.value = Math.min(dates.length - 1, parseInt(slider.value, 10) + 1);
      render();
    });

    render();
  }

  document.addEventListener("DOMContentLoaded", main);
})();
