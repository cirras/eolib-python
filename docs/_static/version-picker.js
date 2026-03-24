(() => {
  const container = document.querySelector("[data-eolib-version-picker]");
  const warning = document.querySelector("[data-eolib-version-warning]");
  const warningLink = warning?.querySelector("[data-eolib-version-warning-link]");
  if (!container) {
    return;
  }

  const button = container.querySelector("[data-eolib-version-button]");
  const currentLabel = container.querySelector("[data-eolib-version-current]");
  const menu = container.querySelector("[data-eolib-version-menu]");
  if (!(button instanceof HTMLButtonElement) || !(currentLabel instanceof HTMLElement) || !(menu instanceof HTMLElement)) {
    return;
  }

  const currentVersion = container.dataset.currentVersion || "";
  const currentPageName = container.dataset.pageName || "index";
  const versionRoot = container.dataset.versionRoot || "index.html";
  const versionRootUrl = new URL(versionRoot, window.location.href);
  const siteRootUrl = new URL("../", versionRootUrl);
  const versionsUrl = new URL("versions.json", siteRootUrl);
  const MENU_MARGIN = 8;
  const MENU_HORIZONTAL_OFFSET = 15;
  let selectedVersion = currentVersion;

  if (menu.parentElement !== document.body) {
    document.body.append(menu);
  }

  const normalizeEntry = (entry) => {
    if (!entry || typeof entry !== "object") {
      return null;
    }

    const { aliases, builder, title, version } = entry;
    if (typeof version !== "string" || typeof title !== "string") {
      return null;
    }

    const normalizedAliases = Array.isArray(aliases)
      ? aliases.filter((alias) => typeof alias === "string")
      : [];

    return {
      aliases: normalizedAliases,
      builder: builder === "sphinx" ? "sphinx" : "mkdocs",
      title,
      version,
    };
  };

  const currentHash = () => window.location.hash || "";

  const sphinxTargetFor = (version) => {
    const pagePath = currentPageName === "index" ? "" : `${currentPageName}.html`;
    return new URL(pagePath ? `${version}/${pagePath}` : `${version}/`, siteRootUrl);
  };

  const mkdocsTargetFor = (version) => {
    if (currentPageName === "index") {
      return new URL(`${version}/`, siteRootUrl);
    }

    if (!currentPageName.startsWith("reference/")) {
      return new URL(`${version}/`, siteRootUrl);
    }

    const referenceName = currentPageName.slice("reference/".length);
    const mkdocsPath = `reference/${referenceName.replaceAll(".", "/")}/`;
    return new URL(`${version}/${mkdocsPath}`, siteRootUrl);
  };

  const buildTarget = (entry) => {
    const url = entry.builder === "sphinx"
      ? sphinxTargetFor(entry.version)
      : mkdocsTargetFor(entry.version);

    const hash = currentHash();
    if (hash) {
      url.hash = hash;
    }
    return url;
  };

  const positionMenu = () => {
    if (menu.hidden) {
      return;
    }

    const buttonRect = button.getBoundingClientRect();
    const viewportWidth = document.documentElement.clientWidth;
    const viewportHeight = document.documentElement.clientHeight;

    menu.style.minWidth = `${Math.max(buttonRect.width + 16, 120)}px`;
    menu.style.maxHeight = `${Math.max(160, viewportHeight - (MENU_MARGIN * 2) - 24)}px`;

    const menuRect = menu.getBoundingClientRect();
    const availableBelow = viewportHeight - buttonRect.bottom - MENU_MARGIN;
    const availableAbove = buttonRect.top - MENU_MARGIN;
    const openAbove = menuRect.height > availableBelow && availableAbove > availableBelow;

    const top = openAbove
      ? Math.max(MENU_MARGIN, buttonRect.top - menuRect.height - 6)
      : Math.min(viewportHeight - menuRect.height - MENU_MARGIN, buttonRect.bottom + 6);
    const left = Math.min(
      Math.max(MENU_MARGIN, buttonRect.left - MENU_HORIZONTAL_OFFSET),
      viewportWidth - menuRect.width - MENU_MARGIN
    );

    menu.style.top = `${top}px`;
    menu.style.left = `${left}px`;
  };

  const handleViewportChange = () => {
    positionMenu();
  };

  const closeMenu = () => {
    button.setAttribute("aria-expanded", "false");
    menu.hidden = true;
    window.removeEventListener("resize", handleViewportChange);
    document.removeEventListener("scroll", handleViewportChange, true);
  };

  const openMenu = () => {
    button.setAttribute("aria-expanded", "true");
    menu.hidden = false;
    positionMenu();
    window.addEventListener("resize", handleViewportChange);
    document.addEventListener("scroll", handleViewportChange, true);
  };

  const toggleMenu = () => {
    if (menu.hidden) {
      openMenu();
    } else {
      closeMenu();
    }
  };

  const setOptions = (entries) => {
    menu.replaceChildren();

    const selectedEntry = entries.find((entry) => entry.version === currentVersion) ?? entries[0];
    selectedVersion = selectedEntry?.version ?? "";
    if (selectedEntry) {
      currentLabel.textContent = selectedEntry.title;
    }

    for (const entry of entries) {
      const item = document.createElement("li");
      item.setAttribute("role", "option");
      item.className = "sidebar-version-picker-option";
      if (entry.version === selectedVersion) {
        item.dataset.current = "true";
        item.setAttribute("aria-selected", "true");
      } else {
        item.setAttribute("aria-selected", "false");
      }

      const optionButton = document.createElement("button");
      optionButton.type = "button";
      optionButton.className = "sidebar-version-picker-option-button";
      optionButton.textContent = entry.title;
      optionButton.addEventListener("click", () => {
        selectedVersion = entry.version;
        window.location.assign(buildTarget(entry).toString());
      });

      item.append(optionButton);
      menu.append(item);
    }

    const interactive = entries.length >= 2;
    button.disabled = !interactive;
    if (!interactive) {
      closeMenu();
    }
  };

  const setWarningState = (entries) => {
    if (!(warning instanceof HTMLElement) || !(warningLink instanceof HTMLAnchorElement)) {
      return;
    }

    const announcement = warning.closest(".announcement");
    if (!(announcement instanceof HTMLElement)) {
      return;
    }

    const latestEntry = entries.find((entry) => entry.version === "latest" || entry.aliases.includes("latest"));
    if (!latestEntry || latestEntry.version === currentVersion) {
      delete announcement.dataset.eolibVersionWarningActive;
      warning.hidden = true;
      warningLink.removeAttribute("href");
      return;
    }

    warningLink.href = buildTarget(latestEntry).toString();
    warning.hidden = false;
    announcement.dataset.eolibVersionWarningActive = "true";
  };

  button.addEventListener("click", () => {
    if (!button.disabled) {
      toggleMenu();
    }
  });

  document.addEventListener("click", (event) => {
    if (!container.contains(event.target) && !menu.contains(event.target)) {
      closeMenu();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeMenu();
    }
  });

  fetch(versionsUrl)
    .then((response) => {
      if (!response.ok) {
        throw new Error(`Failed to load ${versionsUrl}`);
      }
      return response.json();
    })
    .then((payload) => {
      const entries = payload.map(normalizeEntry).filter(Boolean);
      if (!entries.length) {
        button.disabled = true;
        return;
      }

      setOptions(entries);
      setWarningState(entries);
    })
    .catch(() => {
      button.disabled = true;
      closeMenu();
    });
})();
