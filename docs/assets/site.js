(() => {
  const buttons = document.querySelectorAll("[data-copy-target]");
  for (const button of buttons) {
    button.addEventListener("click", async () => {
      const target = document.getElementById(button.dataset.copyTarget);
      if (!target) return;
      const original = button.textContent;
      try {
        await navigator.clipboard.writeText(target.textContent);
        button.textContent = "Copied";
      } catch (_) {
        button.textContent = "Select + copy";
      }
      window.setTimeout(() => { button.textContent = original; }, 1600);
    });
  }
})();
