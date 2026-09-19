const state = { file: null };

const byId = (id) => document.getElementById(id);
const uploadForm = byId("upload-form");
const fileInput = byId("file-input");
const uploadButton = byId("upload-button");
const uploadMessage = byId("upload-message");
const progress = byId("upload-progress");

function setView(view) {
  document.querySelectorAll(".mode-switch__button").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.view === view);
  });
  document.querySelectorAll(".view-panel").forEach((panel) => {
    panel.classList.toggle("is-active", panel.id === `${view}-view`);
  });
}

document.querySelectorAll(".mode-switch__button").forEach((button) => {
  button.addEventListener("click", () => setView(button.dataset.view));
});

document.querySelectorAll(".capability-grid article").forEach((card, index) => {
  if (index === 0) card.addEventListener("click", () => setView("chat"));
});

function setFile(file) {
  state.file = file || null;
  byId("selected-file").textContent = file
    ? `${file.name} · ${(file.size / 1024).toFixed(1)} KB`
    : "No file selected";
  uploadButton.disabled = !file;
  uploadMessage.textContent = "";
  uploadMessage.classList.remove("is-error");
}

byId("choose-file").addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", () => setFile(fileInput.files[0]));

["dragenter", "dragover"].forEach((eventName) => {
  uploadForm.addEventListener(eventName, (event) => {
    event.preventDefault();
    uploadForm.classList.add("is-dragging");
  });
});
["dragleave", "drop"].forEach((eventName) => {
  uploadForm.addEventListener(eventName, (event) => {
    event.preventDefault();
    uploadForm.classList.remove("is-dragging");
  });
});
uploadForm.addEventListener("drop", (event) => setFile(event.dataTransfer.files[0]));

async function parseResponse(response) {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.detail || "The request could not be completed.");
  return payload;
}

async function loadHealth() {
  const status = byId("service-status");
  const pill = status.closest(".status-pill");
  try {
    const response = await fetch("/api/health");
    const payload = await parseResponse(response);
    if (!payload.groq_configured || !payload.qdrant_configured) throw new Error();
    status.textContent = "Services ready";
    pill.classList.remove("is-error");
  } catch {
    status.textContent = "Service setup required";
    pill.classList.add("is-error");
  }
}

async function loadDocuments() {
  const list = byId("document-list");
  try {
    const payload = await parseResponse(await fetch("/api/documents"));
    byId("document-count").textContent = payload.documents.length;
    if (!payload.documents.length) {
      list.innerHTML = '<p class="empty-state">No indexed documents yet.</p>';
      return;
    }
    list.innerHTML = payload.documents.map((document) => `
      <article class="document-row">
        <div><strong>${escapeHtml(document.name)}</strong><small>Trusted knowledge source</small></div>
        <span class="document-status">${escapeHtml(document.status)}</span>
        <time>${new Date(document.created_at).toLocaleDateString()}</time>
      </article>`).join("");
  } catch (error) {
    list.innerHTML = `<p class="empty-state">${escapeHtml(error.message)}</p>`;
  }
}

uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!state.file) return;
  if (state.file.size > 4 * 1024 * 1024) {
    uploadMessage.textContent = "Choose a file smaller than 4 MB for the public deployment.";
    uploadMessage.classList.add("is-error");
    return;
  }
  const body = new FormData();
  body.append("file", state.file);
  uploadButton.disabled = true;
  progress.hidden = false;
  uploadMessage.textContent = "Validating, embedding, and indexing…";
  try {
    const result = await parseResponse(await fetch("/api/documents", { method: "POST", body }));
    uploadMessage.textContent = `Ready · ${result.chunk_count} searchable chunks indexed.`;
    setFile(null);
    fileInput.value = "";
    await loadDocuments();
  } catch (error) {
    uploadMessage.textContent = error.message;
    uploadMessage.classList.add("is-error");
  } finally {
    progress.hidden = true;
    uploadButton.disabled = !state.file;
  }
});

function escapeHtml(value) {
  const node = document.createElement("div");
  node.textContent = String(value ?? "");
  return node.innerHTML;
}

function appendMessage(role, content, sources = []) {
  const conversation = byId("conversation");
  const article = document.createElement("article");
  article.className = `message message--${role}`;
  const sourceMarkup = sources.map((source) => `
    <div class="source-card">
      <strong>[${escapeHtml(source.source_id)}] ${escapeHtml(source.filename)} · page ${escapeHtml(source.page_start || "N/A")}</strong>
      <p>${escapeHtml(source.text)}</p>
    </div>`).join("");
  article.innerHTML = role === "user"
    ? `<div class="message__bubble">${escapeHtml(content)}</div>`
    : `<span class="message__avatar">EA</span><div class="message__bubble">${escapeHtml(content)}${sourceMarkup}</div>`;
  conversation.append(article);
  conversation.scrollTop = conversation.scrollHeight;
}

byId("chat-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const input = byId("question-input");
  const question = input.value.trim();
  if (!question) return;
  appendMessage("user", question);
  input.value = "";
  const pending = "Retrieving authorized evidence…";
  appendMessage("assistant", pending);
  const placeholder = byId("conversation").lastElementChild;
  try {
    const result = await parseResponse(await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    }));
    placeholder.remove();
    appendMessage("assistant", result.answer, result.sources);
  } catch (error) {
    placeholder.remove();
    appendMessage("assistant", error.message);
  }
});

byId("refresh-documents").addEventListener("click", loadDocuments);
loadHealth();
loadDocuments();
