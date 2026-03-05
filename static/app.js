// --- Tab switching ---

document.querySelectorAll(".tab").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach((c) => c.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById("tab-" + btn.dataset.tab).classList.add("active");
  });
});

// --- Helpers ---

async function apiPost(path, body) {
  const res = await fetch("/api" + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function showLoading(el, text) {
  el.innerHTML = '<div class="loading">' + escapeHtml(text) + "</div>";
}

function showError(el, msg) {
  el.innerHTML = '<div class="error">' + escapeHtml(msg) + "</div>";
}

function truncate(str, len) {
  if (!str) return "";
  return str.length > len ? str.slice(0, len) + "..." : str;
}

// --- Search ---

async function doSearch() {
  const query = document.getElementById("search-query").value.trim();
  if (!query) return;

  const results = document.getElementById("search-results");
  const collection = document.getElementById("search-collection").value;
  const k = parseInt(document.getElementById("search-k").value) || 10;

  showLoading(results, "Searching...");

  try {
    const data = await apiPost("/search", { query, collection, k });
    if (data.count === 0) {
      results.innerHTML = '<div class="error">No results found</div>';
      return;
    }
    results.innerHTML = data.results
      .map(
        (r) => `
      <div class="email-card">
        <div class="meta">
          <span>${escapeHtml(r.from || "unknown")}</span>
          <span>${escapeHtml(r.date || "")}</span>
        </div>
        <div class="subject">${escapeHtml(r.subject || "(no subject)")}</div>
        <div class="body">${escapeHtml(truncate(r.cleaned_body, 500))}</div>
      </div>`
      )
      .join("");
  } catch (e) {
    showError(results, e.message);
  }
}

document.getElementById("search-query").addEventListener("keydown", (e) => {
  if (e.key === "Enter") doSearch();
});

// --- Ask ---

async function doAsk() {
  const question = document.getElementById("ask-query").value.trim();
  if (!question) return;

  const results = document.getElementById("ask-results");
  const collection = document.getElementById("ask-collection").value;

  showLoading(results, "Thinking...");

  try {
    const data = await apiPost("/ask", { question, collection });
    const sourcesHtml = data.sources
      .map((s) => `${escapeHtml(s.subject || "(no subject)")} - ${escapeHtml(s.from || "")}`)
      .join("<br>");

    results.innerHTML = `
      <div class="answer-box">
        <h3>Answer</h3>
        ${escapeHtml(data.answer)}
        <div class="sources">
          <strong>Sources (${data.sources.length} emails):</strong><br>
          ${sourcesHtml}
        </div>
      </div>`;
  } catch (e) {
    showError(results, e.message);
  }
}

document.getElementById("ask-query").addEventListener("keydown", (e) => {
  if (e.key === "Enter") doAsk();
});

// --- Storyline ---

async function doStoryline() {
  const topic = document.getElementById("storyline-topic").value.trim();
  if (!topic) return;

  const results = document.getElementById("storyline-results");
  const collection = document.getElementById("storyline-collection").value;
  const k = parseInt(document.getElementById("storyline-k").value) || 20;

  showLoading(results, "Generating storyline (this may take a moment)...");

  try {
    const data = await apiPost("/storyline", { topic, collection, k });
    results.innerHTML = `
      <div class="storyline-box">
        <div class="meta-bar">
          <span>Based on ${data.email_count} emails</span>
          <span>${escapeHtml(data.date_range.earliest)} to ${escapeHtml(data.date_range.latest)}</span>
        </div>
        ${escapeHtml(data.storyline)}
      </div>`;
  } catch (e) {
    showError(results, e.message);
  }
}

document.getElementById("storyline-topic").addEventListener("keydown", (e) => {
  if (e.key === "Enter") doStoryline();
});

// --- Upload ---

const dropZone = document.getElementById("drop-zone");
const fileInput = document.getElementById("file-input");

dropZone.addEventListener("click", () => fileInput.click());

dropZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropZone.classList.add("dragover");
});

dropZone.addEventListener("dragleave", () => {
  dropZone.classList.remove("dragover");
});

dropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropZone.classList.remove("dragover");
  if (e.dataTransfer.files.length) uploadFile(e.dataTransfer.files[0]);
});

fileInput.addEventListener("change", () => {
  if (fileInput.files.length) uploadFile(fileInput.files[0]);
});

async function uploadFile(file) {
  const status = document.getElementById("upload-status");
  const collection = document.getElementById("upload-collection").value;

  dropZone.classList.add("uploading");
  status.innerHTML = '<div class="loading">Uploading ' + escapeHtml(file.name) + "...</div>";

  try {
    const form = new FormData();
    form.append("file", file);

    const res = await fetch("/api/upload?collection=" + encodeURIComponent(collection), {
      method: "POST",
      body: form,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || "Upload failed");
    }

    const data = await res.json();
    status.innerHTML = `
      <div class="email-card">
        <div class="subject">Upload started</div>
        <div class="body">File: ${escapeHtml(data.filename)}\nCollection: ${escapeHtml(data.collection)}\nStatus: Processing in background\n\nYour emails are being parsed and indexed. This may take a few minutes for large archives.</div>
      </div>`;

    // Refresh collections after a short delay
    setTimeout(loadCollections, 3000);
  } catch (e) {
    showError(status, e.message);
  } finally {
    dropZone.classList.remove("uploading");
    fileInput.value = "";
  }
}

// --- Collections ---

async function loadCollections() {
  const el = document.getElementById("collections-list");
  try {
    const res = await fetch("/api/collections");
    const data = await res.json();

    if (!data.collections || data.collections.length === 0) {
      el.innerHTML = '<div class="collection-item"><span>No collections yet</span></div>';
      return;
    }

    el.innerHTML = data.collections
      .map(
        (c) => `
      <div class="collection-item">
        <span>${escapeHtml(c.name)}</span>
        <span class="count">${c.count} emails</span>
      </div>`
      )
      .join("");
  } catch (e) {
    el.innerHTML = '<div class="error">Could not load collections</div>';
  }
}

// --- Health check ---

async function checkHealth() {
  const el = document.getElementById("health-status");
  try {
    const res = await fetch("/api/health");
    const data = await res.json();
    const llmBadge = data.llm_configured
      ? '<span class="badge badge-ok">LLM: ' + escapeHtml(data.llm_provider) + "</span>"
      : '<span class="badge badge-err">No LLM key</span>';
    el.innerHTML = '<span class="badge badge-ok">Connected</span> ' + llmBadge;
  } catch {
    el.innerHTML = '<span class="badge badge-err">Disconnected</span>';
  }
}

// --- Init ---

checkHealth();
loadCollections();
