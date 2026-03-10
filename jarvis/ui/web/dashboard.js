const state = {
  eventSource: null,
  events: [],
};

const runtimeState = document.getElementById("runtime-state");
const runtimeCpu = document.getElementById("runtime-cpu");
const runtimeMemory = document.getElementById("runtime-memory");
const runtimeQueued = document.getElementById("runtime-queued");
const commandForm = document.getElementById("command-form");
const commandInput = document.getElementById("command-input");
const commandOutput = document.getElementById("command-output");
const commandStatus = document.getElementById("command-status");
const queueButton = document.getElementById("queue-command");
const eventIndicator = document.getElementById("event-indicator");
const eventStream = document.getElementById("event-stream");
const servicesGrid = document.getElementById("services-grid");
const startupList = document.getElementById("startup-list");
const jobsList = document.getElementById("jobs-list");
const executionsList = document.getElementById("executions-list");
const confirmationsList = document.getElementById("confirmations-list");
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

async function queueCommand(text) {
  commandStatus.textContent = "Queued";
  commandStatus.className = "badge neutral";
  commandOutput.textContent = "Submitting command to background queue...";

  try {
    const response = await fetch("/command/async", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, confirmed: true }),
    });
    const payload = await response.json();
    commandOutput.textContent = `Queued ${payload.request_id}\n\n${payload.text}`;
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
  runtimeQueued.textContent = `${status.command_queue.queued}/${status.command_queue.running}`;

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

  startupList.innerHTML = renderStartup(status.startup);

  jobsList.innerHTML = (status.jobs.length ? status.jobs : [{ message: "No automation jobs scheduled.", status: "idle" }])
    .map((job) => renderJob(job))
    .join("");

  executionsList.innerHTML = (payload.executions.length ? payload.executions : [{ text: "No queued executions yet.", status: "idle" }])
    .map((execution) => renderExecution(execution))
    .join("");

  confirmationsList.innerHTML = (payload.confirmations.length ? payload.confirmations : [{ text: "No pending confirmations.", status: "idle" }])
    .map((confirmation) => renderConfirmation(confirmation))
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

function renderStartup(startup) {
  if (!startup) {
    return `
      <article class="stack-item">
        <span class="stack-title">Startup status unavailable.</span>
      </article>
    `;
  }

  const state = startup.installed ? "Installed" : "Not installed";
  const details = startup.details || {};
  const extra = [
    startup.message,
    details.status ? `Task: ${details.status}` : "",
    details.last_result ? `Last result: ${details.last_result}` : "",
  ]
    .filter(Boolean)
    .join(" ");

  const actions = startup.supported
    ? `
        <button class="inline-action ghost" data-startup-action="install" data-startup-mode="api">Install API</button>
        <button class="inline-action ghost" data-startup-action="install" data-startup-mode="background">Install Background</button>
        <button class="inline-action ghost" data-startup-action="uninstall">Remove</button>
      `
    : "";

  return `
    <article class="stack-item">
      <span class="stack-title">${state}</span>
      <span class="stack-meta">${startup.platform} Â· ${startup.mode} Â· ${startup.task_name}</span>
      <span class="stack-meta">${extra || "No startup details available."}</span>
      ${actions}
    </article>
  `;
}

function renderExecution(execution) {
  const cancelButton =
    execution.status === "queued" || execution.status === "in_progress"
      ? `<button class="inline-action ghost" data-request-id="${execution.request_id}">Cancel</button>`
      : "";

  return `
    <article class="stack-item">
      <span class="stack-title">${execution.text}</span>
      <span class="stack-meta">${execution.status} · queued ${formatTime(execution.queued_at)}</span>
      <span class="stack-meta">${execution.message || execution.error || "Awaiting execution output."}</span>
      ${cancelButton}
    </article>
  `;
}

function renderTask(task) {
  const steps = (task.steps || []).map((step) => `${step.title} [${step.status}]`).join(" · ");
  return `
    <article class="stack-item">
      <span class="stack-title">${task.goal}</span>
      <span class="stack-meta">${task.status}</span>
      <span class="stack-meta">${steps || "No steps recorded."}</span>
    </article>
  `;
}

function renderConfirmation(confirmation) {
  const actions =
    confirmation.status === "pending"
      ? `
          <button class="inline-action ghost" data-confirmation-id="${confirmation.confirmation_id}" data-decision="approve">Approve</button>
          <button class="inline-action ghost" data-confirmation-id="${confirmation.confirmation_id}" data-decision="reject">Reject</button>
        `
      : "";

  return `
    <article class="stack-item">
      <span class="stack-title">${confirmation.text || "Confirmation"}</span>
      <span class="stack-meta">${confirmation.risk_level || "unknown"} · ${confirmation.status}</span>
      <span class="stack-meta">${confirmation.reason || "No reason provided."}</span>
      ${actions}
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

  document.querySelectorAll("[data-request-id]").forEach((button) => {
    button.addEventListener("click", async () => {
      const requestId = button.getAttribute("data-request-id");
      await fetch(`/commands/${requestId}/cancel`, { method: "POST" });
      await refresh();
    });
  });

  document.querySelectorAll("[data-confirmation-id]").forEach((button) => {
    button.addEventListener("click", async () => {
      const confirmationId = button.getAttribute("data-confirmation-id");
      const decision = button.getAttribute("data-decision");
      await fetch(`/confirmations/${confirmationId}/${decision}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      await refresh();
    });
  });

  document.querySelectorAll("[data-startup-action]").forEach((button) => {
    button.addEventListener("click", async () => {
      const action = button.getAttribute("data-startup-action");
      if (action === "install") {
        const mode = button.getAttribute("data-startup-mode") || "api";
        await fetch("/startup/install", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ mode }),
        });
      } else {
        await fetch("/startup/uninstall", { method: "POST" });
      }
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
  return value.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
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

queueButton.addEventListener("click", async () => {
  const text = commandInput.value.trim();
  if (!text) return;
  await queueCommand(text);
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
