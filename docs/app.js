const links = [...document.querySelectorAll(".nav a")];
const sections = links
  .map((link) => document.querySelector(link.getAttribute("href")))
  .filter(Boolean);

const observer = new IntersectionObserver(
  (entries) => {
    const visible = entries
      .filter((entry) => entry.isIntersecting)
      .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];

    if (!visible) {
      return;
    }

    links.forEach((link) => {
      link.classList.toggle("is-active", link.hash === `#${visible.target.id}`);
    });
  },
  { rootMargin: "-20% 0px -65% 0px", threshold: [0.1, 0.4, 0.8] },
);

sections.forEach((section) => observer.observe(section));

document.querySelectorAll("[data-copy]").forEach((button) => {
  button.addEventListener("click", async () => {
    const block = button.closest(".code-block");
    const code = block?.querySelector("code")?.innerText;

    if (!code) {
      return;
    }

    await navigator.clipboard.writeText(code);
    const original = button.textContent;
    button.textContent = "Copie";
    window.setTimeout(() => {
      button.textContent = original;
    }, 1400);
  });
});
