// kliz site behaviour. Every section is readable without this file.

const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/* Clipboard ------------------------------------------------------------- */

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}

function flash(element, message, original) {
  element.textContent = message;
  window.setTimeout(() => {
    element.textContent = original;
  }, 1600);
}

document.querySelectorAll("[data-copy]").forEach((button) => {
  button.addEventListener("click", async () => {
    const code = button.closest(".code-block")?.querySelector("pre code")?.innerText;
    if (!code) return;
    const ok = await copyText(code);
    flash(button, ok ? "Copied" : "Select and copy", "Copy");
  });
});

document.querySelectorAll("[data-copy-text]").forEach((button) => {
  const state = button.querySelector(".install-state");
  button.addEventListener("click", async () => {
    const ok = await copyText(button.dataset.copyText);
    if (state) flash(state, ok ? "Copied" : "Select it", "Copy");
  });
});

/* Section entrances ----------------------------------------------------- */

const revealables = [...document.querySelectorAll("[data-reveal]")];

// The hero stage is always on the first screen, and its clip-path hides most
// of it from IntersectionObserver, so it opens on load instead.
document.querySelectorAll("[data-shutter]").forEach((stage) => {
  requestAnimationFrame(() => requestAnimationFrame(() => stage.classList.add("is-in")));
});

if (reduceMotion || !("IntersectionObserver" in window)) {
  revealables.forEach((element) => element.classList.add("is-in"));
} else {
  // Stagger siblings that enter together: heading, then text, then fragment.
  const observer = new IntersectionObserver(
    (entries) => {
      entries
        .filter((entry) => entry.isIntersecting)
        .forEach((entry, index) => {
          entry.target.style.setProperty("--delay", `${index * 80}ms`);
          entry.target.classList.add("is-in");
          observer.unobserve(entry.target);
        });
    },
    { rootMargin: "0px 0px -10% 0px", threshold: 0.12 },
  );
  revealables.forEach((element) => observer.observe(element));
}

/* The hero run: providers turn green one after the other ----------------- */

const run = document.querySelector("[data-run]");

function playRun() {
  if (!run) return;
  const steps = [...run.querySelectorAll("[data-step]")];
  run.classList.add("is-running");
  steps.forEach((step) => {
    step.classList.remove("is-active");
    step.classList.add("is-pending");
    step.querySelector(".run-status").textContent = "waiting";
  });

  const pace = reduceMotion ? 0 : 700;
  steps.forEach((step, index) => {
    window.setTimeout(() => {
      step.classList.remove("is-pending");
      step.classList.add("is-active");
      step.querySelector(".run-status").textContent = "sending";
    }, pace * (index * 2 + 1));
    window.setTimeout(() => {
      step.classList.remove("is-active");
      const status = step.querySelector(".run-status");
      status.textContent = status.dataset.done;
      if (index === steps.length - 1) run.classList.remove("is-running");
    }, pace * (index * 2 + 2));
  });
}

if (run) {
  run.querySelector("[data-run-replay]")?.addEventListener("click", playRun);
  window.setTimeout(playRun, reduceMotion ? 0 : 900);
}

/* URL rules: a port of kliz.normalize_url() and IndexNow's clean-URL check */

function checkUrl(raw) {
  const value = raw.trim();
  if (!value) return { error: "url must be a non-empty string" };

  const scheme = /^([a-z][a-z0-9+.-]*):/i.exec(value)?.[1]?.toLowerCase();
  if (scheme !== "http" && scheme !== "https") {
    return { error: "url must use the http or https scheme" };
  }

  let url;
  try {
    url = new URL(value);
  } catch {
    return { error: "url must include a hostname" };
  }
  if (!url.hostname) return { error: "url must include a hostname" };
  if (url.username || url.password) return { error: "url must not contain credentials" };
  if (url.hash.length > 1) return { error: "url must not contain a fragment" };

  url.hostname = url.hostname.replace(/\.+$/, "");
  url.hash = "";
  return {
    normalized: url.href,
    host: url.hostname,
    origin: url.origin,
    hasQuery: url.search.length > 1,
  };
}

function payloadFor(result) {
  return JSON.stringify(
    {
      host: result.host,
      key: "your-indexnow-key",
      keyLocation: `${result.origin}/your-indexnow-key.txt`,
      urlList: [result.normalized],
    },
    null,
    2,
  ).replace(/\[\n\s+("[^"]*")\n\s+\]/, "[$1]");
}

const tryInput = document.getElementById("try-url");
const verdict = document.querySelector("[data-verdict]");
const payload = document.querySelector("[data-payload]");
const payloadLabel = document.querySelector("[data-payload-label]");

function setVerdict(prefix, code) {
  verdict.textContent = prefix;
  if (code) {
    const element = document.createElement("code");
    element.textContent = code;
    verdict.append(element);
  }
}

function renderTry() {
  const result = checkUrl(tryInput.value);
  verdict.classList.remove("is-rejected", "is-warn");

  if (result.error) {
    verdict.classList.add("is-rejected");
    setVerdict("Rejected before sending:", result.error);
    payloadLabel.textContent = "Nothing is sent for this URL";
    payload.textContent = `NotificationResult(\n    success=False,\n    retryable=False,\n    error="${result.error}",\n)`;
    return;
  }

  if (result.hasQuery) {
    verdict.classList.add("is-warn");
    setVerdict("IndexNow needs allow_query=True for this one. Normalized:", result.normalized);
  } else {
    setVerdict("Accepted as", result.normalized);
  }
  payloadLabel.textContent = "IndexNow request body";
  payload.textContent = payloadFor(result);
}

if (tryInput && verdict && payload) {
  tryInput.addEventListener("input", renderTry);
  document.querySelectorAll("[data-example]").forEach((button) => {
    button.addEventListener("click", () => {
      tryInput.value = button.dataset.example;
      renderTry();
    });
  });
  renderTry();
}

/* Tabs ----------------------------------------------------------------- */

document.querySelectorAll("[data-tabs]").forEach((root) => {
  const tabs = [...root.querySelectorAll('[role="tab"]')];

  function select(tab, focus = false) {
    tabs.forEach((other) => {
      const selected = other === tab;
      other.setAttribute("aria-selected", String(selected));
      other.tabIndex = selected ? 0 : -1;
      document.getElementById(other.getAttribute("aria-controls")).hidden = !selected;
    });
    if (focus) tab.focus();
  }

  tabs.forEach((tab, index) => {
    tab.addEventListener("click", () => select(tab));
    tab.addEventListener("keydown", (event) => {
      const moves = { ArrowRight: 1, ArrowLeft: -1 };
      if (event.key in moves) {
        event.preventDefault();
        select(tabs[(index + moves[event.key] + tabs.length) % tabs.length], true);
      } else if (event.key === "Home" || event.key === "End") {
        event.preventDefault();
        select(event.key === "Home" ? tabs[0] : tabs[tabs.length - 1], true);
      }
    });
  });
});

/* FAQ: one answer open; on wide screens it is mirrored in a large pane ---- */

const faq = document.querySelector(".faq");
const pane = document.querySelector("[data-faq-pane]");

if (faq && pane) {
  faq.classList.add("has-pane");
  const buttons = [...faq.querySelectorAll("[data-faq] button")];

  function open(button) {
    buttons.forEach((other) => {
      const expanded = other === button;
      other.setAttribute("aria-expanded", String(expanded));
      document.getElementById(other.getAttribute("aria-controls")).hidden = !expanded;
    });
    const answer = document.getElementById(button.getAttribute("aria-controls"));
    pane.replaceChildren(...[...answer.children].map((child) => child.cloneNode(true)));
  }

  buttons.forEach((button) => {
    button.addEventListener("click", () => open(button));
    button.addEventListener("focus", () => open(button));
    if (window.matchMedia("(hover: hover)").matches) {
      button.addEventListener("mouseenter", () => open(button));
    }
  });
  open(buttons[0]);
}

/* Setup generator ----------------------------------------------------- */

const setup = document.querySelector("[data-setup]");

function setupText(origin, mode) {
  if (mode === "cli") {
    return [
      `KEY=$(kliz indexnow keygen --write public/ --site ${origin})`,
      "# deploy public/, then:",
      'export KLIZ_INDEXNOW_API_KEY="$KEY"',
      `export KLIZ_INDEXNOW_KEY_LOCATION="${origin}/$KEY.txt"`,
      `kliz indexnow verify-key --site ${origin}`,
      `kliz notify --sitemap ${origin}/sitemap.xml`,
    ].join("\n");
  }
  return [
    "# .github/workflows/indexing.yml",
    "name: Search engine indexing",
    "on:",
    "  deployment_status:",
    "",
    "jobs:",
    "  index:",
    "    if: >-",
    "      github.event.deployment_status.state == 'success' &&",
    "      github.event.deployment_status.environment == 'Production'",
    "    runs-on: ubuntu-latest",
    "    steps:",
    "      - uses: freddychoudja/kliz-@v0.3.1",
    "        with:",
    `          sitemap: ${origin}/sitemap.xml`,
    "          indexnow-api-key: ${{ secrets.INDEXNOW_KEY }}",
    `          indexnow-key-location: ${origin}/\${{ secrets.INDEXNOW_KEY }}.txt`,
  ].join("\n");
}

if (setup) {
  const site = setup.querySelector("#setup-site");
  const out = setup.querySelector("[data-setup-out]");
  const error = setup.querySelector("[data-setup-error]");
  const label = setup.querySelector("[data-setup-label]");

  function current() {
    const result = checkUrl(site.value);
    const mode = setup.querySelector('input[name="mode"]:checked').value;
    if (result.error) {
      site.setAttribute("aria-invalid", "true");
      error.textContent = "Enter your site's address, like https://example.com";
      return null;
    }
    site.removeAttribute("aria-invalid");
    error.textContent = "";
    return setupText(result.origin, mode);
  }

  function render() {
    const text = current();
    if (text) out.textContent = text;
  }

  setup.addEventListener("input", render);
  setup.addEventListener("submit", async (event) => {
    event.preventDefault();
    const text = current();
    if (!text) {
      site.focus();
      return;
    }
    out.textContent = text;
    const ok = await copyText(text);
    flash(label, ok ? "Copied. Paste it into your project." : "Select the text above to copy it", "Copy setup");
  });
  render();
}
