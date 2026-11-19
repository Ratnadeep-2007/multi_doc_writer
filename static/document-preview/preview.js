(() => {
  "use strict";

  const preview = document.getElementById("document-preview");
  const form = document.getElementById("docs-form");
  if (!preview || !form) return;
  const documents = JSON.parse(preview.dataset.documents);

  preview.innerHTML = [
    '<header class="preview-heading"><div>',
    '<h2 id="document-preview-title">Live document preview</h2>',
    '<p>Preview the current Word templates with your form values.</p>',
    '</div><span class="preview-count"></span></header>',
    '<div class="preview-workspace">',
    '<nav class="preview-menu" aria-label="Document previews"><p>Document package</p><ul></ul>',
    '<label class="preview-picker">Choose a document <select></select></label></nav>',
    '<div class="preview-reader"><div class="preview-toolbar"><div>',
    '<span class="preview-active" aria-live="polite"></span>',
    '<button class="preview-zoom" type="button" aria-pressed="false" disabled>Actual size</button></div>',
    '<div class="preview-navigation"><button type="button" aria-label="Previous document">\u2190</button>',
    '<span class="preview-position"></span><button type="button" aria-label="Next document">\u2192</button></div></div>',
    '<div class="preview-message"><p class="preview-status" role="status">Loading the Word template\u2026</p>',
    '<button type="button" class="preview-retry" hidden>Try again</button></div>',
    '<div class="preview-stage" tabindex="0" role="region" aria-label="Word document pages" aria-busy="true">',
    '<div class="preview-document-frame" hidden></div></div></div></div>'
  ].join("");

  const menu = preview.querySelector("ul");
  const picker = preview.querySelector("select");
  const active = preview.querySelector(".preview-active");
  const position = preview.querySelector(".preview-position");
  const stage = preview.querySelector(".preview-stage");
  const frame = preview.querySelector(".preview-document-frame");
  const status = preview.querySelector(".preview-status");
  const retry = preview.querySelector(".preview-retry");
  const zoom = preview.querySelector(".preview-zoom");
  const [previous, next] = preview.querySelectorAll(".preview-navigation button");
  preview.querySelector(".preview-count").textContent = documents.length + " documents";

  let current = 0;
  let started = false;
  let actualSize = false;
  let revision = 0;
  let timer;
  let request;
  let rendered;

  function setStatus(message, failed = false) {
    status.textContent = message;
    retry.hidden = !failed;
  }

  function fitDocument() {
    if (!rendered) return;
    const width = rendered.offsetWidth;
    if (!width) return;
    const style = getComputedStyle(stage);
    const available = stage.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight);
    const zoomLevel = actualSize ? 1 : Math.min(1, Math.max(1, available) / width);
    rendered.style.transform = "scale(" + zoomLevel + ")";
    frame.style.width = Math.floor(width * zoomLevel) + "px";
    frame.style.height = Math.ceil(rendered.offsetHeight * zoomLevel) + "px";
  }

  function fitFloatingGraphics(content, isSticker) {
    for (const img of content.querySelectorAll("header img")) {
      // Some page-aligned Word pictures are positioned relative to a browser paragraph.
      const page = img.closest("section.preview-word");
      const anchor = img.parentElement;
      if (!page || !anchor.style.left || anchor.style.width !== "0px") continue;
      const pageBounds = page.getBoundingClientRect();
      const picture = img.getBoundingClientRect();
      if (picture.width && picture.right > pageBounds.right) {
        const margin = parseFloat(getComputedStyle(page).paddingRight);
        const delta = picture.right - pageBounds.right + margin;
        const left = parseFloat(getComputedStyle(anchor).left);
        anchor.style.left = (left - delta) + "px";
      }
    }

    if (!isSticker) return;
    const table = content.querySelector("foreignObject table");
    const shape = table?.closest("svg");
    if (shape) {
      // Keep the real template's outlined auto-fit text box around the reflowed table.
      const height = table.getBoundingClientRect().bottom - shape.getBoundingClientRect().top + 4;
      shape.style.height = Math.ceil(height) + "px";
      shape.style.outline = "3.25pt double #202020";
      shape.style.outlineOffset = "5px";
      shape.style.overflow = "visible";
    }
  }

  async function renderWord(bytes, isSticker) {
    const surface = document.createElement("div");
    surface.className = "preview-docx-surface";
    const shadow = surface.attachShadow({ mode: "open" });
    const styles = document.createElement("div");
    const content = document.createElement("div");
    shadow.append(styles, content);
    await window.docx.renderAsync(bytes, content, styles, {
      className: "preview-word",
      useBase64URL: true,
      ignoreLastRenderedPageBreak: false,
      renderAltChunks: false
    });
    const browserStyles = document.createElement("style");
    browserStyles.textContent = [
      ".preview-word-wrapper {padding:0; background:transparent; align-items:flex-start;}",
      ".preview-word-wrapper > section.preview-word {margin-bottom:14px; box-shadow:none;}",
      ".preview-word-wrapper > section.preview-word:last-child {margin-bottom:0;}"
    ].join("\n");
    shadow.append(browserStyles);
    await Promise.all(Array.from(content.querySelectorAll("img"), img => img.decode().catch(() => {})));
    return { surface, content, isSticker };
  }

  async function loadDocument(version, index) {
    const template = documents[index];
    const controller = new AbortController();
    request = controller;
    try {
      const response = await fetch(template.url, {
        method: "POST",
        body: new FormData(form),
        cache: "no-store",
        signal: controller.signal
      });
      if (!response.ok) throw new Error("Word preview request failed");
      const bytes = await response.arrayBuffer();
      if (version !== revision) return;
      const word = await renderWord(bytes, template.sticker);
      if (version !== revision) return;

      rendered = word.surface;
      frame.replaceChildren(rendered);
      frame.hidden = false;
      fitFloatingGraphics(word.content, word.isSticker);
      fitDocument();
      zoom.disabled = false;
      setStatus("");
    } catch (error) {
      if (version !== revision || error.name === "AbortError") return;
      setStatus("The Word preview could not be loaded.", true);
    } finally {
      if (version === revision) {
        stage.setAttribute("aria-busy", "false");
        request = null;
      }
    }
  }

  function refresh(delay = 0) {
    clearTimeout(timer);
    request?.abort();
    const version = ++revision;
    stage.setAttribute("aria-busy", "true");
    setStatus("Rendering the Word template\u2026");
    timer = setTimeout(() => loadDocument(version, current), delay);
  }

  function show(index, load = true) {
    if (index !== current) {
      stage.scrollTop = 0;
      stage.scrollLeft = 0;
      frame.hidden = true;
      rendered = null;
      frame.replaceChildren();
      zoom.disabled = true;
    }
    current = index;
    active.textContent = documents[index].title;
    position.textContent = (index + 1) + " / " + documents.length;
    picker.value = String(index);
    previous.disabled = index === 0;
    next.disabled = index === documents.length - 1;
    buttons.forEach((button, buttonIndex) => {
      if (buttonIndex === index) button.setAttribute("aria-current", "true");
      else button.removeAttribute("aria-current");
    });
    if (load) {
      started = true;
      refresh();
    }
  }

  const buttons = documents.map(({ title }, index) => {
    const row = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = title;
    button.addEventListener("click", () => show(index));
    row.append(button);
    menu.append(row);
    picker.add(new Option(title, String(index)));
    return button;
  });

  picker.addEventListener("change", () => show(Number(picker.value)));
  previous.addEventListener("click", () => show(current - 1));
  next.addEventListener("click", () => show(current + 1));
  retry.addEventListener("click", () => refresh());
  zoom.addEventListener("click", () => {
    actualSize = !actualSize;
    zoom.setAttribute("aria-pressed", String(actualSize));
    zoom.textContent = actualSize ? "Fit width" : "Actual size";
    fitDocument();
  });
  form.addEventListener("document-values-changed", () => {
    if (started) refresh(320);
  });
  new ResizeObserver(fitDocument).observe(stage);
  show(0, false);
  preview.hidden = false;

  const observer = new IntersectionObserver(entries => {
    if (!entries.some(entry => entry.isIntersecting)) return;
    observer.disconnect();
    if (!started) {
      started = true;
      refresh();
    }
  }, { rootMargin: "200px 0px" });
  observer.observe(preview);
})();
