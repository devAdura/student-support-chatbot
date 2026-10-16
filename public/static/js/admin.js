const csrf = document.querySelector('meta[name="csrf-token"]').content;
const notice = document.getElementById("notice");
async function api(path, method = "GET", data) {
  const r = await fetch(path, {
    method,
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
    ...(data === undefined ? {} : { body: JSON.stringify(data) }),
  });
  const b = await r.json();
  if (!r.ok) throw new Error(b.error || "Request failed.");
  return b;
}
async function load() {
  const data = await api("/api/admin/data");
  document.getElementById("login").classList.add("hidden");
  document.getElementById("dashboard").classList.remove("hidden");
  const stats = document.getElementById("stats");
  stats.replaceChildren();
  for (const [value, label] of [
    [data.stats.total, "Questions"],
    [data.stats.fallbacks, "Needs clarification"],
    [
      `${(data.stats.average_latency * 1000).toFixed(0)} ms`,
      "Average engine time",
    ],
    [
      `${data.stats.helpful} / ${data.stats.helpful + data.stats.unhelpful}`,
      "Helpful / rated",
    ],
  ]) {
    const card = document.createElement("div");
    card.className = "stat";
    const strong = document.createElement("strong");
    strong.textContent = value;
    card.append(strong, document.createTextNode(label));
    stats.append(card);
  }
  const entries = document.getElementById("entries");
  entries.replaceChildren();
  for (const entry of data.entries) {
    const f = document.createElement("form");
    f.className = "admin-entry";
    const h = document.createElement("h3");
    h.textContent = entry.title;
    f.append(h);
    const label = document.createElement("label");
    label.textContent = "Response";
    const t = document.createElement("textarea");
    t.value = entry.response;
    t.required = true;
    t.maxLength = 3000;
    label.append(t);
    f.append(label);
    const sourceLabel = document.createElement("label");
    sourceLabel.textContent = "Verified source or general guidance label";
    const source = document.createElement("input");
    source.value = entry.source;
    source.required = true;
    source.maxLength = 3000;
    sourceLabel.append(source);
    f.append(sourceLabel);
    const exLabel = document.createElement("label");
    exLabel.textContent = "Example questions (one per line, 2 to 30)";
    const examples = document.createElement("textarea");
    examples.value = entry.examples.join("\n");
    examples.required = true;
    exLabel.append(examples);
    f.append(exLabel);
    const b = document.createElement("button");
    b.className = "primary";
    b.textContent = "Save guidance";
    f.append(b);
    f.onsubmit = async (e) => {
      e.preventDefault();
      b.disabled = true;
      try {
        await api(
          `/api/admin/knowledge/${encodeURIComponent(entry.intent)}`,
          "PUT",
          {
            response: t.value,
            source: source.value,
            examples: examples.value
              .split("\n")
              .map((s) => s.trim())
              .filter(Boolean),
          },
        );
        notice.textContent = `Saved ${entry.title}.`;
      } catch (err) {
        notice.textContent = err.message;
      } finally {
        b.disabled = false;
      }
    };
    entries.append(f);
  }
}
document.getElementById("login").onsubmit = async (e) => {
  e.preventDefault();
  try {
    await api("/api/admin/login", "POST", {
      password: document.getElementById("password").value,
    });
    document.getElementById("password").value = "";
    notice.textContent = "";
    await load();
  } catch (err) {
    notice.textContent = err.message;
  }
};
document.getElementById("logout").onclick = async () => {
  try {
    await api("/api/admin/logout", "POST", {});
    document.getElementById("dashboard").classList.add("hidden");
    document.getElementById("login").classList.remove("hidden");
    notice.textContent = "Signed out.";
  } catch (e) {
    notice.textContent = e.message;
  }
};
load().catch(() => {});
