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
const intelligenceForm = document.getElementById("intelligence-form");
const intelligencePrompt = document.getElementById("intelligence-prompt");
const intelligenceContext = document.getElementById("intelligence-context");
const intelligenceOutput = document.getElementById("intelligence-output");
const intelligenceStatus = document.getElementById("intelligence-status");
const eventIndicator = document.getElementById("event-indicator");
const eventStream = document.getElementById("event-stream");
const servicesGrid = document.getElementById("services-grid");
const intelligenceList = document.getElementById("intelligence-list");
const voiceState = document.getElementById("voice-state");
const voiceInput = document.getElementById("voice-input");
const voiceList = document.getElementById("voice-list");
const voiceStartButton = document.getElementById("voice-start");
const voiceStopButton = document.getElementById("voice-stop");
const voiceSimulateButton = document.getElementById("voice-simulate");
const visionState = document.getElementById("vision-state");
const visionList = document.getElementById("vision-list");
const visionOutput = document.getElementById("vision-output");
const visionScreenButton = document.getElementById("vision-screen");
const visionCameraButton = document.getElementById("vision-camera");
const startupList = document.getElementById("startup-list");
const processesList = document.getElementById("processes-list");
const windowsList = document.getElementById("windows-list");
const jobsList = document.getElementById("jobs-list");
const goalsList = document.getElementById("goals-list");
const workflowsList = document.getElementById("workflows-list");
const executionsList = document.getElementById("executions-list");
const confirmationsList = document.getElementById("confirmations-list");
const tasksList = document.getElementById("tasks-list");
const insightsList = document.getElementById("insights-list");
const toolsList = document.getElementById("tools-list");
const activityList = document.getElementById("activity-list");
const reviewGoalsButton = document.getElementById("review-goals");

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

async function sendIntelligencePrompt(prompt, contextText) {
  intelligenceStatus.textContent = "Running";
  intelligenceStatus.className = "badge live";
  intelligenceOutput.textContent = "Sending prompt to active intelligence provider...";

  let context = {};
  try {
    context = contextText.trim() ? JSON.parse(contextText) : {};
  } catch (error) {
    intelligenceStatus.textContent = "Context Error";
    intelligenceStatus.className = "badge warn";
    intelligenceOutput.textContent = `Invalid JSON context: ${error}`;
    return;
  }

  try {
    const response = await fetch("/intelligence/respond", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt, context }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || `Request failed: ${response.status}`);
    }
    intelligenceStatus.textContent = payload.provider;
    intelligenceStatus.className = "badge live";
    intelligenceOutput.textContent =
      `${payload.text}\n\nProvider: ${payload.provider}\nModel: ${payload.model}\nMetadata: ${JSON.stringify(payload.metadata, null, 2)}`;
    await refresh();
  } catch (error) {
    intelligenceStatus.textContent = "Error";
    intelligenceStatus.className = "badge warn";
    intelligenceOutput.textContent = String(error);
  }
}

async function captureVision(source) {
  if (!visionOutput) return;
  visionOutput.textContent = `Capturing ${source}...`;
  try {
    const response = await fetch(`/vision/${source}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ save_artifact: true, include_ocr: source === "screen" }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || `Request failed: ${response.status}`);
    }
    visionOutput.textContent = JSON.stringify(payload, null, 2);
    await refresh();
  } catch (error) {
    visionOutput.textContent = String(error);
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
      `,
    )
    .join("");

  intelligenceList.innerHTML = renderIntelligence(status.intelligence);
  voiceState.textContent = status.voice?.listening ? "Listening" : "Idle";
  voiceState.className = status.voice?.listening ? "badge live" : "badge neutral";
  voiceList.innerHTML = renderVoice(status.voice);
  visionState.textContent = status.vision?.last_source ? status.vision.last_source : "Idle";
  visionState.className = status.vision?.screen?.available || status.vision?.camera?.available ? "badge live" : "badge neutral";
  visionList.innerHTML = renderVision(status.vision);
  startupList.innerHTML = renderStartup(status.startup);
  processesList.innerHTML = renderProcesses(status.processes);
  windowsList.innerHTML = renderWindows(status.windows);

  jobsList.innerHTML = (status.jobs.length ? status.jobs : [{ message: "No automation jobs scheduled.", status: "idle" }])
    .map((job) => renderJob(job))
    .join("");

  goalsList.innerHTML = (status.goals.length ? status.goals : [{ title: "No persistent goals yet.", status: "idle" }])
    .map((goal) => renderGoal(goal, status.proactive_review))
    .join("");

  workflowsList.innerHTML = (status.workflows.length ? status.workflows : [{ title: "No workflows stored yet.", status: "idle", steps: [] }])
    .map((workflow) => renderWorkflow(workflow))
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
      `,
    )
    .join("");

  activityList.innerHTML = (payload.activities.length ? payload.activities : [{ message: "No activity yet.", category: "system" }])
    .map(
      (activity) => `
        <article class="stack-item">
          <span class="stack-title">${activity.message}</span>
          <span class="stack-meta">${activity.category} &middot; ${formatTime(activity.created_at)}</span>
        </article>
      `,
    )
    .join("");

  bindActionHandlers();
}

function renderJob(job) {
  const cancelButton =
    job.status === "scheduled"
      ? `<button class="inline-action ghost" data-job-id="${job.job_id}">Cancel</button>`
      : "";

  return `
    <article class="stack-item">
      <span class="stack-title">${job.message}</span>
      <span class="stack-meta">${job.cadence} &middot; ${job.status}</span>
      <span class="stack-meta">Next run: ${job.next_run_at ? formatTime(job.next_run_at) : "n/a"}</span>
      ${cancelButton}
    </article>
  `;
}

function renderGoal(goal, proactiveReview) {
  if (!goal.goal_id) {
    return `
      <article class="stack-item">
        <span class="stack-title">${goal.title}</span>
        <span class="stack-meta">${goal.status}</span>
      </article>
    `;
  }

  const actions = [];
  if (goal.status === "active") {
    actions.push(`<button class="inline-action ghost" data-goal-id="${goal.goal_id}" data-goal-status="completed">Complete</button>`);
    actions.push(`<button class="inline-action ghost" data-goal-id="${goal.goal_id}" data-goal-status="paused">Pause</button>`);
    actions.push(`<button class="inline-action ghost" data-goal-id="${goal.goal_id}" data-goal-status="blocked">Block</button>`);
  }
  if (goal.status === "paused" || goal.status === "blocked") {
    actions.push(`<button class="inline-action ghost" data-goal-id="${goal.goal_id}" data-goal-status="active">Resume</button>`);
  }

  const nextAction = goal.next_action || goal.detail || "No next action recorded.";
  const reviewNote = goal.metadata?.last_review_note;
  const reviewStamp =
    proactiveReview && proactiveReview.last_review_at
      ? `Last review ${formatTime(proactiveReview.last_review_at)}`
      : "No proactive review yet";

  return `
    <article class="stack-item">
      <span class="stack-title">${goal.title}</span>
      <span class="stack-meta">${goal.status} &middot; priority ${goal.priority}</span>
      <span class="stack-meta">${nextAction}</span>
      <span class="stack-meta">${reviewNote || reviewStamp}</span>
      ${actions.join("")}
    </article>
  `;
}

function renderWorkflow(workflow) {
  if (!workflow.workflow_id) {
    return `
      <article class="stack-item">
        <span class="stack-title">${workflow.title}</span>
        <span class="stack-meta">${workflow.status}</span>
      </article>
    `;
  }

  const actions = [];
  if (workflow.status === "pending" || workflow.status === "failed" || workflow.status === "requires_confirmation" || workflow.status === "cancelled" || workflow.status === "completed") {
    actions.push(`<button class="inline-action ghost" data-workflow-id="${workflow.workflow_id}" data-workflow-action="run">Run</button>`);
  }
  if (workflow.status === "queued" || workflow.status === "in_progress") {
    actions.push(`<button class="inline-action ghost" data-workflow-id="${workflow.workflow_id}" data-workflow-action="cancel">Cancel</button>`);
  }

  const steps = (workflow.steps || []).map((step) => `${step.title} [${step.status}]`).join(" | ");
  return `
    <article class="stack-item">
      <span class="stack-title">${workflow.title}</span>
      <span class="stack-meta">${workflow.status} &middot; ${workflow.steps.length} steps</span>
      <span class="stack-meta">${steps || "No workflow steps recorded."}</span>
      ${actions.join("")}
    </article>
  `;
}

function renderIntelligence(intelligence) {
  if (!intelligence) {
    return `
      <article class="stack-item">
        <span class="stack-title">Intelligence status unavailable.</span>
      </article>
    `;
  }

  const fallback =
    intelligence.configured_provider !== intelligence.active_provider
      ? `Fallback active: configured ${intelligence.configured_provider}, running ${intelligence.active_provider}.`
      : "Primary provider active.";
  const keyStatus = intelligence.has_gemini_api_key ? "API key present" : "API key missing";

  return `
    <article class="stack-item">
      <span class="stack-title">${intelligence.active_provider} &middot; ${intelligence.model}</span>
      <span class="stack-meta">Configured: ${intelligence.configured_provider}</span>
      <span class="stack-meta">${fallback}</span>
      <span class="stack-meta">${keyStatus}</span>
      <span class="stack-meta">${intelligence.endpoint}</span>
    </article>
  `;
}

function renderVoice(voice) {
  if (!voice) {
    return `
      <article class="stack-item">
        <span class="stack-title">Voice status unavailable.</span>
      </article>
    `;
  }

  const providerSummary = [
    `Audio: ${voice.audio?.provider || "unknown"} (${voice.audio?.available ? "available" : "missing"})`,
    `Wake: ${voice.wake?.provider || "unknown"} (${voice.wake?.available ? "available" : "missing"})`,
    `STT: ${voice.stt?.provider || "unknown"} (${voice.stt?.available ? "available" : "missing"})`,
    `TTS: ${voice.tts?.provider || "unknown"} (${voice.tts?.available ? "available" : "fallback"})`,
  ].join(" | ");

  return `
    <article class="stack-item">
      <span class="stack-title">${voice.listening ? "Always-on listening active" : "Listening is idle"}</span>
      <span class="stack-meta">${providerSummary}</span>
      <span class="stack-meta">Wake word: ${voice.wake_word}</span>
      <span class="stack-meta">Last transcript: ${voice.last_transcript || "n/a"}</span>
      <span class="stack-meta">Last response: ${voice.last_response || "n/a"}</span>
      <span class="stack-meta">Last error: ${voice.last_error || "none"}</span>
    </article>
  `;
}

function renderVision(vision) {
  if (!vision) {
    return `
      <article class="stack-item">
        <span class="stack-title">Vision status unavailable.</span>
      </article>
    `;
  }

  const providerSummary = [
    `Screen: ${vision.screen?.provider || "unknown"} (${vision.screen?.available ? "available" : "missing"})`,
    `Camera: ${vision.camera?.provider || "unknown"} (${vision.camera?.available ? "available" : "missing"})`,
    `OCR: ${vision.ocr?.provider || "unknown"} (${vision.ocr?.available ? "available" : "missing"})`,
  ].join(" | ");

  return `
    <article class="stack-item">
      <span class="stack-title">${vision.captures || 0} captures recorded</span>
      <span class="stack-meta">${providerSummary}</span>
      <span class="stack-meta">Last source: ${vision.last_source || "n/a"}</span>
      <span class="stack-meta">Artifact: ${vision.last_artifact_path || "n/a"}</span>
      <span class="stack-meta">OCR snippet: ${vision.last_ocr_text || "n/a"}</span>
      <span class="stack-meta">Last error: ${vision.last_error || "none"}</span>
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

  const stateLabel = startup.installed ? "Installed" : "Not installed";
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
      <span class="stack-title">${stateLabel}</span>
      <span class="stack-meta">${startup.platform} &middot; ${startup.mode} &middot; ${startup.task_name}</span>
      <span class="stack-meta">${extra || "No startup details available."}</span>
      ${actions}
    </article>
  `;
}

function renderProcesses(processState) {
  if (!processState) {
    return `
      <article class="stack-item">
        <span class="stack-title">Process state unavailable.</span>
      </article>
    `;
  }
  const processes = processState.processes || [];
  if (!processes.length) {
    const message = processState.error || "No processes reported.";
    return `
      <article class="stack-item">
        <span class="stack-title">${message}</span>
      </article>
    `;
  }
  return processes
    .map((process) => {
      const cpu = process.cpu_percent == null ? "-" : `${process.cpu_percent}%`;
      const memory = process.memory_percent == null ? "-" : `${Number(process.memory_percent).toFixed(1)}%`;
      return `
        <article class="stack-item">
          <span class="stack-title">${process.name}</span>
          <span class="stack-meta">PID ${process.pid} &middot; ${process.status || "unknown"} &middot; CPU ${cpu} &middot; MEM ${memory}</span>
          <button class="inline-action ghost" data-process-pid="${process.pid}">Terminate</button>
        </article>
      `;
    })
    .join("");
}

function renderWindows(windowState) {
  if (!windowState) {
    return `
      <article class="stack-item">
        <span class="stack-title">Window state unavailable.</span>
      </article>
    `;
  }
  const windows = windowState.windows || [];
  if (!windows.length) {
    const message = windowState.error || "No windows reported.";
    return `
      <article class="stack-item">
        <span class="stack-title">${message}</span>
      </article>
    `;
  }
  return windows
    .map((windowItem) => {
      const title = String(windowItem.title || "Untitled");
      const stateBits = [];
      if (windowItem.is_active) stateBits.push("active");
      if (windowItem.is_minimized) stateBits.push("minimized");
      if (windowItem.is_maximized) stateBits.push("maximized");
      const stateLabel = stateBits.length ? stateBits.join(" · ") : "normal";
      return `
        <article class="stack-item">
          <span class="stack-title">${escapeHtml(title)}</span>
          <span class="stack-meta">${stateLabel} &middot; ${windowItem.width || 0}x${windowItem.height || 0}</span>
          <button class="inline-action ghost" data-window-action="focus" data-window-title="${escapeAttribute(title)}">Focus</button>
          <button class="inline-action ghost" data-window-action="minimize" data-window-title="${escapeAttribute(title)}">Minimize</button>
          <button class="inline-action ghost" data-window-action="maximize" data-window-title="${escapeAttribute(title)}">Maximize</button>
        </article>
      `;
    })
    .join("");
}

function renderExecution(execution) {
  const cancelButton =
    execution.status === "queued" || execution.status === "in_progress"
      ? `<button class="inline-action ghost" data-request-id="${execution.request_id}">Cancel</button>`
      : "";

  return `
    <article class="stack-item">
      <span class="stack-title">${execution.text}</span>
      <span class="stack-meta">${execution.status} &middot; queued ${formatTime(execution.queued_at)}</span>
      <span class="stack-meta">${execution.message || execution.error || "Awaiting execution output."}</span>
      ${cancelButton}
    </article>
  `;
}

function renderTask(task) {
  const steps = (task.steps || []).map((step) => `${step.title} [${step.status}]`).join(" | ");
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
      <span class="stack-meta">${confirmation.risk_level || "unknown"} &middot; ${confirmation.status}</span>
      <span class="stack-meta">${confirmation.reason || "No reason provided."}</span>
      ${actions}
    </article>
  `;
}

function renderInsights(insights) {
  const suggestions = insights.suggestions || [];
  const projects = insights.projects || [];
  const goals = insights.goals || [];
  const patterns = insights.patterns || [];
  const edges = insights.graph?.edges || [];

  const suggestionBlock = suggestions.length
    ? suggestions
        .map(
          (suggestion) => `
            <article class="stack-item">
              <span class="stack-title">${suggestion.title}</span>
              <span class="stack-meta">${suggestion.category} &middot; priority ${suggestion.priority}</span>
              <span class="stack-meta">${suggestion.detail}</span>
            </article>
          `,
        )
        .join("")
    : `<article class="stack-item"><span class="stack-title">No proactive suggestions yet.</span></article>`;

  const goalBlock = goals.length
    ? goals
        .map(
          (goal) => `
            <article class="stack-item">
              <span class="stack-title">${goal.title}</span>
              <span class="stack-meta">${goal.status} &middot; priority ${goal.priority}</span>
              <span class="stack-meta">${goal.next_action || goal.detail}</span>
            </article>
          `,
        )
        .join("")
    : `<article class="stack-item"><span class="stack-title">No active goals in memory yet.</span></article>`;

  const projectBlock = projects.length
    ? projects
        .map(
          (project) => `
            <article class="stack-item">
              <span class="stack-title">${project.project_name}</span>
              <span class="stack-meta">${project.status}</span>
              <span class="stack-meta">${project.summary}</span>
            </article>
          `,
        )
        .join("")
    : `<article class="stack-item"><span class="stack-title">No active project context yet.</span></article>`;

  const patternBlock = patterns.length
    ? patterns
        .map(
          (pattern) => `
            <article class="stack-item">
              <span class="stack-title">${pattern.pattern}</span>
              <span class="stack-meta">Seen ${pattern.count} times</span>
            </article>
          `,
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
          `,
        )
        .join("")
    : `<article class="stack-item"><span class="stack-title">Knowledge graph is still sparse.</span></article>`;

  return `${suggestionBlock}${goalBlock}${projectBlock}${patternBlock}${edgeBlock}`;
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
      `,
    )
    .join("");
}

function bindActionHandlers() {
  document.querySelectorAll("[data-job-id]").forEach((button) => {
    button.onclick = async () => {
      const jobId = button.getAttribute("data-job-id");
      await fetch(`/jobs/${jobId}/cancel`, { method: "POST" });
      await refresh();
    };
  });

  document.querySelectorAll("[data-request-id]").forEach((button) => {
    button.onclick = async () => {
      const requestId = button.getAttribute("data-request-id");
      await fetch(`/commands/${requestId}/cancel`, { method: "POST" });
      await refresh();
    };
  });

  document.querySelectorAll("[data-confirmation-id]").forEach((button) => {
    button.onclick = async () => {
      const confirmationId = button.getAttribute("data-confirmation-id");
      const decision = button.getAttribute("data-decision");
      await fetch(`/confirmations/${confirmationId}/${decision}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      await refresh();
    };
  });

  document.querySelectorAll("[data-startup-action]").forEach((button) => {
    button.onclick = async () => {
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
    };
  });

  document.querySelectorAll("[data-goal-id]").forEach((button) => {
    button.onclick = async () => {
      const goalId = button.getAttribute("data-goal-id");
      const status = button.getAttribute("data-goal-status");
      await fetch(`/goals/${goalId}/status`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
      await refresh();
    };
  });

  document.querySelectorAll("[data-workflow-id]").forEach((button) => {
    button.onclick = async () => {
      const workflowId = button.getAttribute("data-workflow-id");
      const action = button.getAttribute("data-workflow-action");
      await fetch(`/workflows/${workflowId}/${action}`, { method: "POST" });
      await refresh();
    };
  });

  document.querySelectorAll("[data-process-pid]").forEach((button) => {
    button.onclick = async () => {
      const pid = Number(button.getAttribute("data-process-pid"));
      const response = await fetch("/processes/terminate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pid, confirmed: false }),
      });
      const payload = await response.json();
      commandOutput.textContent = payload.message || JSON.stringify(payload, null, 2);
      commandStatus.textContent = payload.status || "pending";
      commandStatus.className = payload.status === "completed" ? "badge live" : "badge warn";
      await refresh();
    };
  });

  document.querySelectorAll("[data-window-action]").forEach((button) => {
    button.onclick = async () => {
      const action = button.getAttribute("data-window-action");
      const title = button.getAttribute("data-window-title");
      const response = await fetch(`/windows/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title }),
      });
      const payload = await response.json();
      commandOutput.textContent = payload.message || JSON.stringify(payload, null, 2);
      commandStatus.textContent = payload.ok === false ? "failed" : action;
      commandStatus.className = payload.ok === false ? "badge warn" : "badge live";
      await refresh();
    };
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

function escapeAttribute(value) {
  return escapeHtml(value).replaceAll("\"", "&quot;").replaceAll("'", "&#39;");
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

intelligenceForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const prompt = intelligencePrompt.value.trim();
  if (!prompt) return;
  await sendIntelligencePrompt(prompt, intelligenceContext.value);
});

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

if (reviewGoalsButton) {
  reviewGoalsButton.addEventListener("click", async () => {
    await fetch("/goals/review", { method: "POST" });
    await refresh();
  });
}

if (voiceStartButton) {
  voiceStartButton.addEventListener("click", async () => {
    await fetch("/voice/start", { method: "POST" });
    await refresh();
  });
}

if (voiceStopButton) {
  voiceStopButton.addEventListener("click", async () => {
    await fetch("/voice/stop", { method: "POST" });
    await refresh();
  });
}

if (voiceSimulateButton) {
  voiceSimulateButton.addEventListener("click", async () => {
    const text = voiceInput.value.trim();
    if (!text) return;
    await fetch("/voice/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, strict_wake: true }),
    });
    await refresh();
  });
}

if (visionScreenButton) {
  visionScreenButton.addEventListener("click", async () => {
    await captureVision("screen");
  });
}

if (visionCameraButton) {
  visionCameraButton.addEventListener("click", async () => {
    await captureVision("camera");
  });
}

document.querySelectorAll("[data-command]").forEach((button) => {
  button.addEventListener("click", async () => {
    const text = button.getAttribute("data-command");
    commandInput.value = text;
    await sendCommand(text);
  });
});

document.querySelectorAll("[data-intelligence-prompt]").forEach((button) => {
  button.addEventListener("click", async () => {
    const prompt = button.getAttribute("data-intelligence-prompt");
    intelligencePrompt.value = prompt;
    await sendIntelligencePrompt(prompt, intelligenceContext.value);
  });
});

connectEvents();
refresh();
setInterval(refresh, 5000);
