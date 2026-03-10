const state = {
  eventSource: null,
  events: [],
};

const runtimeState = document.getElementById("runtime-state");
const runtimeCpu = document.getElementById("runtime-cpu");
const runtimeMemory = document.getElementById("runtime-memory");
const commandForm = document.getElementById("command-form");
const commandInput = document.getElementById("command-input");
const commandOutput = document.getElementById("command-output");
const commandStatus = document.getElementById("command-status");
const eventIndicator = document.getElementById("event-indicator");
const eventStream = document.getElementById("event-stream");
const servicesGrid = document.getElementById("services-grid");
const jobsList = document.getElementById("jobs-list");
const tasksList = document.getElementById("tasks-list");
const insightsList = document.getElementById("insights-list");
const toolsList = document.getElementById("tools-list");
const activityList = document.getElementById("activity-list");

async function fetchStatus() {
  const response = await fetch("/status");
  if (!response.ok) {
    throw new Error(`Status request failed: ${response.status}`);
  }
  return response.json();
}

async function sendCommand(text) {
  commandStatus.textContent = "Running";
  commandStatus.className = "badge live";
  commandOutput.textContent = "Executing command...";

  try {
    const response = await fetch("/command", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, confirmed: true }),
    });
    const payload = await response.json();
    commandOutput.textContent = payload.message || JSON.stringify(payload, null, 2);
    commandStatus.textContent = payload.status;
    commandStatus.className = payload.status === "completed" ? "badge live" : "badge warn";
    await refresh();
  } catch (error) {
    commandStatus.textContent = "Error";
    commandStatus.className = "badge warn";
    commandOutput.textContent = String(error);
  }
}

function renderStatus(payload) {
  const status = payload.status;
  runtimeState.textContent = status.runtime.state;
  runtimeCpu.textContent = status.resources.cpu_percent == null ? "-" : `${status.resources.cpu_percent}%`;
  runtimeMemory.textContent = status.resources.memory_percent == null ? "-" : `${status.resources.memory_percent}%`;

  servicesGrid.innerHTML = status.services
    .map(
      (service) => `
        <article class="service-card" data-state="${service.state}">
          <strong>${service.name}</strong>
          <span class="stack-meta">${service.state}</span>
        </article>
      `
    )
    .join("");

  jobsList.innerHTML = (status.jobs.length ? status.jobs : [{ message: "No automation jobs scheduled.", status: "idle" }])
    .map((job) => renderJob(job))
    .join("");

  tasksList.innerHTML = (payload.tasks.length ? payload.tasks : [{ goal: "No task history yet.", status: "idle", steps: [] }])
    .map((task) => renderTask(task))
    .join("");

  insightsList.innerHTML = renderInsights(status.insights);

  toolsList.innerHTML = status.tools
    .map(
      (tool) => `
        <article class="stack-item">
          <span class="stack-title">${tool.name}</span>
          <span class="stack-meta">${tool.description}</span>
        </article>
      `
    )
    .join("");

  activityList.innerHTML = (payload.activities.length ? payload.activities : [{ message: "No activity yet.", category: "system" }])
    .map(
      (activity) => `
        <article class="stack-item">
          <span class="stack-title">${activity.message}</span>
          <span class="stack-meta">${activity.category} · ${formatTime(activity.created_at)}</span>
        </article>
      `
    )
    .join("");

  bindCancelActions();
}

function renderJob(job) {
  const cancelButton =
    job.status === "scheduled"
      ? `<button class="inline-action ghost" data-job-id="${job.job_id}">Cancel</button>`
      : "";

  return `
    <article class="stack-item">
      <span class="stack-title">${job.message}</span>
      <span class="stack-meta">${job.cadence} · ${job.status}</span>
      <span class="stack-meta">Next run: ${job.next_run_at ? formatTime(job.next_run_at) : "n/a"}</span>
      ${cancelButton}
    </article>
  `;
}

function renderTask(task) {
  const steps = (task.steps || [])
    .map((step) => `${step.title} [${step.status}]`)
    .join(" · ");
  return `
    <article class="stack-item">
      <span class="stack-title">${task.goal}</span>
      <span class="stack-meta">${task.status}</span>
      <span class="stack-meta">${steps || "No steps recorded."}</span>
    </article>
  `;
}

function renderInsights(insights) {
  const patterns = insights.patterns || [];
  const edges = insights.graph?.edges || [];
  const patternBlock = patterns.length
    ? patterns
        .map(
          (pattern) => `
            <article class="stack-item">
              <span class="stack-title">${pattern.pattern}</span>
              <span class="stack-meta">Seen ${pattern.count} times</span>
            </article>
          `
        )
        .join("")
    : `<article class="stack-item"><span class="stack-title">No learned patterns yet.</span></article>`;

  const edgeBlock = edges.length
    ? edges
        .slice(0, 4)
        .map(
          (edge) => `
            <article class="stack-item">
              <span class="stack-title">${edge.predicate}</span>
              <span class="stack-meta">${edge.subject_key} -> ${edge.object_key}</span>
            </article>
          `
        )
        .join("")
    : `<article class="stack-item"><span class="stack-title">Knowledge graph is still sparse.</span></article>`;

  return `${patternBlock}${edgeBlock}`;
}

function pushEvent(event) {
  state.events.unshift(event);
  state.events = state.events.slice(0, 40);
  eventStream.innerHTML = state.events
    .map(
      (entry) => `
        <article class="event-item">
          <span class="event-topic">${entry.topic}</span>
          <div class="event-meta">${formatTime(entry.timestamp)}</div>
          <div class="event-meta">${escapeHtml(JSON.stringify(entry.payload))}</div>
        </article>
      `
    )
    .join("");
}

function bindCancelActions() {
  document.querySelectorAll("[data-job-id]").forEach((button) => {
    button.addEventListener("click", async () => {
      const jobId = button.getAttribute("data-job-id");
      await fetch(`/jobs/${jobId}/cancel`, { method: "POST" });
      await refresh();
    });
  });
}

function connectEvents() {
  if (state.eventSource) {
    state.eventSource.close();
  }
  const source = new EventSource("/stream/events");
  state.eventSource = source;
  eventIndicator.textContent = "Live";
  eventIndicator.className = "badge live";

  source.onmessage = (message) => {
    pushEvent(JSON.parse(message.data));
  };

  source.onerror = () => {
    eventIndicator.textContent = "Reconnecting";
    eventIndicator.className = "badge warn";
  };
}

function formatTime(value) {
  if (!value) return "n/a";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

async function refresh() {
  try {
    const payload = await fetchStatus();
    renderStatus(payload);
  } catch (error) {
    commandOutput.textContent = `Dashboard refresh failed: ${error}`;
    eventIndicator.textContent = "Offline";
    eventIndicator.className = "badge warn";
  }
}

commandForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = commandInput.value.trim();
  if (!text) return;
  await sendCommand(text);
});

document.querySelectorAll("[data-command]").forEach((button) => {
  button.addEventListener("click", async () => {
    const text = button.getAttribute("data-command");
    commandInput.value = text;
    await sendCommand(text);
  });
});

connectEvents();
refresh();
setInterval(refresh, 5000);
