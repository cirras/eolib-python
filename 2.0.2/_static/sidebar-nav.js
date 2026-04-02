(() => {
  const expandRootApiBranch = () => {
    const rootCheckbox = document.querySelector(
      ".sidebar-tree .toctree-l1.has-children > .toctree-checkbox",
    );

    if (!(rootCheckbox instanceof HTMLInputElement)) {
      return;
    }

    rootCheckbox.checked = true;
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", expandRootApiBranch, { once: true });
  } else {
    expandRootApiBranch();
  }
})();
