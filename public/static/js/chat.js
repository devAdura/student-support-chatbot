const csrf = document.querySelector('meta[name="csrf-token"]').content;
const messages = document.getElementById("chatMessages");
const input = document.getElementById("message");
const error = document.getElementById("error");
let busy = false;
async function api(path, method = "GET", data) {
  const res = await fetch(path, {
    method,
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
    ...(data === undefined ? {} : { body: JSON.stringify(data) }),
  });
  const body = await res.json();
  if (!res.ok)
    throw new Error(body.error || "Something went wrong. Please try again.");
  return body;
}
function addMessage(text, kind, details = {}) {
  const row = document.createElement("div");
  row.className = `message-row ${kind}${details.historical ? "" : " motion-safe:animate-message-in"}`;
  if (kind === "bot") {
    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.textContent = "C";
    row.append(avatar);
  }
  const body = document.createElement("div");
  body.className = "message-body";
  const bubble = document.createElement("div");
  bubble.className = "message-text";
  bubble.textContent = text;
  body.append(bubble);
  if (kind === "bot") {
    const meta = document.createElement("div");
    meta.className = "message-meta";
    meta.textContent = details.source || "Campus Companion · Here to help";
    body.append(meta);
    if (details.id) {
      const feedback = document.createElement("div");
      feedback.className = "feedback";
      for (const [rating, label] of [
        [1, "Helpful"],
        [-1, "Not helpful"],
      ]) {
        const b = document.createElement("button");
        b.type = "button";
        b.textContent = label;
        b.classList.toggle("selected", details.rating === rating);
        b.setAttribute("aria-pressed", String(details.rating === rating));
        b.onclick = async () => {
          try {
            await api("/api/feedback", "POST", {
              query_id: details.id,
              rating,
            });
            for (const el of feedback.children) {
              el.classList.remove("selected");
              el.setAttribute("aria-pressed", "false");
            }
            b.classList.add("selected");
            b.setAttribute("aria-pressed", "true");
            error.textContent = "";
          } catch (e) {
            error.textContent = e.message;
          }
        };
        feedback.append(b);
      }
      body.append(feedback);
    }
  }
  row.append(body);
  messages.append(row);
  messages.scrollTop = messages.scrollHeight;
  return row;
}
function welcome() {
  addMessage(
    "Hi, welcome in! 👋\n\nI’m your campus companion. Ask me about registration, fees, exams or student services, and we’ll find your next step together.",
    "bot",
  );
}
async function send(text) {
  if (busy || !text.trim()) return;
  busy = true;
  document.getElementById("send").disabled = true;
  error.textContent = "";
  addMessage(text, "user");
  input.value = "";
  document.getElementById("count").textContent = "0 / 1000";
  const pending = addMessage("Finding your next step…", "bot");
  pending.dataset.pending = "true";
  try {
    const data = await api("/api/chat", "POST", { message: text });
    pending.remove();
    addMessage(data.response, "bot", {
      id: data.query_id,
      source: data.source,
    });
  } catch (e) {
    pending.remove();
    error.textContent = e.message;
    input.value = text;
  } finally {
    busy = false;
    document.getElementById("send").disabled = false;
    input.focus();
  }
}
document.getElementById("chatForm").addEventListener("submit", (e) => {
  e.preventDefault();
  send(input.value.trim());
});
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
    e.preventDefault();
    send(input.value.trim());
  }
});
input.addEventListener("input", () => {
  document.getElementById("count").textContent = `${input.value.length} / 1000`;
});
document
  .querySelectorAll("[data-question]")
  .forEach((b) => b.addEventListener("click", () => send(b.dataset.question)));
async function clear() {
  if (busy) return;
  try {
    await api("/api/history", "DELETE");
    messages.replaceChildren();
    welcome();
    error.textContent = "";
    input.focus();
  } catch (e) {
    error.textContent = e.message;
  }
}
document.getElementById("clearChat").onclick = clear;
document.getElementById("newChat").onclick = clear;
(async () => {
  try {
    const [history, topics] = await Promise.all([
      api("/api/history"),
      api("/api/topics"),
    ]);
    welcome();
    for (const m of history.messages) {
      addMessage(m.message, "user", { historical: true });
      addMessage(m.response, "bot", {
        id: m.id,
        rating: m.rating,
        historical: true,
      });
    }
    for (const topic of topics.topics) {
      const b = document.createElement("button");
      b.className = "nav-item";
      b.textContent = topic.title;
      b.onclick = () => send(topic.title);
      document.getElementById("topics").append(b);
    }
  } catch (e) {
    welcome();
    error.textContent = "Could not load saved conversation. " + e.message;
  }
})();
