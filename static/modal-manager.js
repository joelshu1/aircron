// Modal Manager Module
// Handles all modal operations: cron review, job creation, etc.

window.AirCron = window.AirCron || {};

// Modal helper functions for content formatting
window.AirCron.formatJobCard = function (jobDetail, statusType) {
  const { zone, job, cron_line, status } = jobDetail;

  // Status styling
  let statusClass = "";
  let statusText = "";
  if (status === "will_add") {
    statusClass = "bg-green-100 text-green-800";
    statusText = "Will Add";
  } else if (status === "will_remove") {
    statusClass = "bg-red-100 text-red-800";
    statusText = "Will Remove";
  } else {
    statusClass = "bg-gray-100 text-gray-600";
    statusText = "Unchanged";
  }

  // Format days
  let dayNames = "";
  if (job && Array.isArray(job.days)) {
    dayNames = job.days
      .map((day) => {
        const dayMap = {
          1: "Mon",
          2: "Tue",
          3: "Wed",
          4: "Thu",
          5: "Fri",
          6: "Sat",
          7: "Sun",
        };
        return dayMap[day];
      })
      .join(", ");
  }

  // Zone display
  let zoneDisplay = zone;
  let zoneHtml = "";
  if (!zone) {
    zoneDisplay = "Unknown Zone";
    if (status === "will_remove") {
      zoneHtml =
        '<div class="text-sm text-red-700 mb-2"><span class="font-medium">Zone:</span> <span class="inline-flex items-center"><span class="mr-1">⚠️</span>Unknown (could not parse from cron line)</span></div>';
    } else {
      zoneHtml =
        '<div class="text-sm text-blue-600 mb-2"><span class="font-medium">Zone:</span> Unknown</div>';
    }
  } else if (zone === "All Speakers") {
    zoneDisplay = "🔊 All Speakers";
    zoneHtml =
      '<div class="text-sm text-blue-600 mb-2"><span class="font-medium">Zone:</span> ' +
      zoneDisplay +
      "</div>";
  } else if (typeof zone === "string" && zone.startsWith("Custom:")) {
    const speakers = zone.replace("Custom:", "").split(",");
    zoneDisplay = "🎵 Custom (" + speakers.length + " speakers)";
    zoneHtml =
      '<div class="text-sm text-blue-600 mb-2"><span class="font-medium">Zone:</span> ' +
      zoneDisplay +
      "</div>";
  } else {
    zoneDisplay = "📻 " + zone;
    zoneHtml =
      '<div class="text-sm text-blue-600 mb-2"><span class="font-medium">Zone:</span> ' +
      zoneDisplay +
      "</div>";
  }

  // Label display
  let labelHtml =
    job && job.label
      ? '<span class="font-semibold text-blue-700">' + job.label + "</span>"
      : '<span class="font-medium text-gray-800">' +
        (job && job.action
          ? job.action.charAt(0).toUpperCase() + job.action.slice(1)
          : "Job") +
        "</span>";

  // Raw cron line for unknown zone
  let rawCronHtml = "";
  if (!zone && status === "will_remove" && cron_line) {
    rawCronHtml =
      '<div class="mt-2 text-xs text-gray-500"><span class="font-medium">Raw cron line:</span><pre class="bg-gray-100 rounded p-2 mt-1 overflow-x-auto">' +
      cron_line +
      "</pre></div>";
  }

  let speakersHtml = "";
  if (zone && typeof zone === "string" && zone.startsWith("Custom:")) {
    speakersHtml =
      '<div class="text-sm text-blue-600 mb-2"><span class="font-medium">Speakers:</span> ' +
      zone
        .replace("Custom:", "")
        .split(",")
        .map((s) => s.trim())
        .join(", ") +
      "</div>";
  }

  let uriHtml = "";
  if (job && job.action === "play" && job.args && job.args.uri) {
    uriHtml =
      '<div class="text-xs text-gray-500 font-mono truncate">' +
      job.args.uri +
      "</div>";
  }

  let volumeHtml = "";
  if (job && job.action === "volume" && job.args && job.args.volume) {
    const scopeLabel = !zone
      ? "Volume"
      : zone === "All Speakers"
      ? "Global app volume"
      : "Per-speaker volume";
    volumeHtml =
      '<div class="text-xs text-gray-500">' +
      scopeLabel +
      ": " +
      job.args.volume +
      "%</div>";
  }

  return (
    '<div class="border rounded-lg p-4 mb-3 hover:shadow-md transition ' +
    (status === "will_add"
      ? "border-green-200 bg-green-50"
      : status === "will_remove"
      ? "border-red-200 bg-red-50"
      : "border-gray-200 bg-gray-50") +
    '">' +
    '<div class="flex justify-between items-start"><div class="flex-1">' +
    '<div class="flex items-center space-x-2 mb-2">' +
    labelHtml +
    '<span class="text-sm text-gray-500">' +
    (job && job.time ? job.time : "") +
    "</span>" +
    '<span class="text-xs px-2 py-1 rounded-full ' +
    statusClass +
    '">' +
    statusText +
    "</span></div>" +
    zoneHtml +
    speakersHtml +
    '<div class="text-sm text-gray-600 mb-2"><span class="font-medium">Days:</span> ' +
    dayNames +
    "</div>" +
    uriHtml +
    volumeHtml +
    rawCronHtml +
    '<div class="cron-detail-line mt-2 text-xs font-mono text-gray-400 hidden">' +
    cron_line +
    "</div>" +
    "</div></div></div>"
  );
};

window.AirCron.formatJobDiff = function (diffs) {
  if (!diffs || !diffs.length) return "";
  return (
    '<ul class="text-xs text-yellow-800 mt-2 ml-2 list-disc">' +
    diffs
      .map((d) => {
        let field = d.field.charAt(0).toUpperCase() + d.field.slice(1);
        let oldVal = Array.isArray(d.old) ? d.old.join(", ") : d.old;
        let newVal = Array.isArray(d.new) ? d.new.join(", ") : d.new;
        if (d.field === "days") {
          const dayMap = {
            1: "Mon",
            2: "Tue",
            3: "Wed",
            4: "Thu",
            5: "Fri",
            6: "Sat",
            7: "Sun",
          };
          oldVal = (d.old || []).map((day) => dayMap[day]).join(", ");
          newVal = (d.new || []).map((day) => dayMap[day]).join(", ");
        }
        if (d.field === "args") {
          oldVal = JSON.stringify(d.old);
          newVal = JSON.stringify(d.new);
        }
        return (
          "<li><b>" +
          field +
          ':</b> <span class="line-through">' +
          oldVal +
          '</span> → <span class="font-bold">' +
          newVal +
          "</span></li>"
        );
      })
      .join("") +
    "</ul>"
  );
};

// Close modal function
window.AirCron.closeModal = function () {
  const modalContainer = document.getElementById("modal-container");
  if (modalContainer) {
    modalContainer.parentNode.removeChild(modalContainer);
    // Recreate for next use
    const newModal = document.createElement("div");
    newModal.id = "modal-container";
    document.body.appendChild(newModal);
  }
};

// Show the cron review modal
window.AirCron.showCronReviewModal = function () {
  console.log("[AirCron] showCronReviewModal called");
  let modalContainer = document.getElementById("modal-container");
  if (!modalContainer) {
    // If missing, create it
    modalContainer = document.createElement("div");
    modalContainer.id = "modal-container";
    document.body.appendChild(modalContainer);
  }
  // Always clear any existing modal content to force a fresh load
  modalContainer.innerHTML = "";
  htmx
    .ajax("GET", "/modal/cron/review", {
      target: modalContainer,
      swap: "innerHTML",
      headers: { "Cache-Control": "no-cache" },
    })
    .then(() => {
      if (window.AirCron.initCronReviewModal) {
        window.AirCron.initCronReviewModal();
      }
    });
};

// Helper function to render status badge
function renderStatusBadge(status) {
  const statusMap = {
    will_add: { class: "bg-green-100 text-green-800", text: "Will Add" },
    will_remove: { class: "bg-red-100 text-red-800", text: "Will Remove" },
    unchanged: { class: "bg-gray-100 text-gray-600", text: "Unchanged" },
    changed: { class: "bg-yellow-100 text-yellow-800", text: "Changed" }
  };
  const config = statusMap[status] || statusMap.unchanged;
  return `<span class="text-xs px-2 py-1 rounded-full ${config.class}">${config.text}</span>`;
}

// Helper function to render a single changed job card
function renderChangedJobCard(chg) {
  const oldJob = chg.old_job;
  const diffs = chg.diffs;
  const dayNames = (oldJob.days || [])
    .map((d) => ({ 1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat", 7: "Sun" }[d]))
    .join(", ");
  const uriHtml =
    oldJob.action === "play" && oldJob.args && oldJob.args.uri
      ? '<div class="text-xs text-gray-500 font-mono truncate">' + oldJob.args.uri + "</div>"
      : "";
  const volumeHtml =
    oldJob.action === "volume" && oldJob.args && oldJob.args.volume
      ? '<div class="text-xs text-gray-500">Volume: ' + oldJob.args.volume + "%</div>"
      : "";
  const diffHtml = window.AirCron.formatJobDiff(diffs);

  return (
    '<div class="border rounded-lg p-4 mb-3 border-yellow-300 bg-yellow-50">' +
    '<div class="flex items-center space-x-2 mb-2">' +
    '<span class="font-semibold text-blue-700">' +
    (oldJob.label || oldJob.action) +
    "</span>" +
    '<span class="text-sm text-gray-500">' +
    oldJob.time +
    "</span>" +
    renderStatusBadge("changed") +
    "</div>" +
    '<div class="text-sm text-blue-600 mb-2">' +
    '<span class="font-medium">Zone:</span> ' +
    oldJob.zone +
    "</div>" +
    '<div class="text-sm text-gray-600 mb-2">' +
    '<span class="font-medium">Days:</span> ' +
    dayNames +
    "</div>" +
    uriHtml +
    volumeHtml +
    diffHtml +
    "</div>"
  );
}

// Helper function to render section header with job cards
function renderJobSection(title, jobs, type) {
  if (!jobs.length) return "";
  const emoji = type === "add" ? "✓" : type === "remove" ? "✗" : "→";
  const colorClass = type === "add" ? "green" : type === "remove" ? "red" : "gray";
  return (
    `<div class="mb-6">
      <h4 class="font-medium text-${colorClass}-700 mb-3">
        ${emoji} ${jobs.length} job${jobs.length !== 1 ? "s" : ""} will be ${
      type === "add" ? "added" : type === "remove" ? "removed" : "remain unchanged"
    }:
      </h4>
      <div class="space-y-3">
        ${jobs.map((job) => window.AirCron.formatJobCard(job, type)).join("")}
      </div>
    </div>`
  );
}

// Helper function to build the modal HTML content
function buildModalHTML(data) {
  if (!data.has_changes) {
    return `
      <div class="text-center py-8">
        <div class="text-green-600 text-5xl mb-4">✓</div>
        <h3 class="text-lg font-medium text-gray-900 mb-2">All jobs are up to date</h3>
        <p class="text-gray-600">No changes needed. All stored jobs are already applied to cron.</p>
      </div>
    `;
  }

  // Group job details by status
  const jobsToAdd = data.job_details.filter((job) => job.status === "will_add");
  const jobsToRemove = data.job_details.filter((job) => job.status === "will_remove");
  const jobsUnchanged = data.job_details.filter((job) => job.status === "unchanged");
  const changedJobs = data.changed_jobs || [];

  let content = `
    <div class="mb-6">
      <h3 class="text-lg font-medium text-gray-900 mb-4">
        Summary: ${data.total_changes} change${data.total_changes !== 1 ? "s" : ""} will be made
      </h3>
  `;

  if (changedJobs.length > 0) {
    content += `
      <div class="mb-6">
        <h4 class="font-medium text-yellow-700 mb-3">
          ⚡ ${changedJobs.length} job${changedJobs.length !== 1 ? "s" : ""} will be changed:
        </h4>
        <div class="space-y-3">
          ${changedJobs.map(renderChangedJobCard).join("")}
        </div>
      </div>
    `;
  }

  content += renderJobSection(jobsToAdd, "add") +
             renderJobSection(jobsToRemove, "remove") +
             renderJobSection(jobsUnchanged, "unchanged");

  content += "</div>";
  return content;
}

// Helper function to update button states based on data
function updateButtonStates(data) {
  const applyBtn = document.getElementById("apply-changes-btn");
  const toggleBtn = document.getElementById("toggle-cron-details");

  if (data.has_changes) {
    if (applyBtn) {
      applyBtn.disabled = false;
      applyBtn.textContent = `Apply ${data.total_changes} Change${data.total_changes !== 1 ? "s" : ""}`;
    }
    if (toggleBtn) {
      toggleBtn.classList.remove("hidden");
    }
  } else {
    if (applyBtn) {
      applyBtn.disabled = true;
      applyBtn.textContent = "No Changes Needed";
    }
    if (toggleBtn) {
      toggleBtn.classList.add("hidden");
    }
  }
}

// Helper function to show error in modal
function showError(contentElement, message, retryable = false) {
  contentElement.innerHTML = `
    <div class="text-red-600 text-center py-8">
      <p>Error loading preview: ${message}</p>
      ${retryable ? `
        <button onclick="window.AirCron.initCronReviewModal()" class="mt-3 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">
          Retry
        </button>
      ` : ""}
    </div>
  `;
}

// Helper function to show loading state
function showLoadingState(contentElement) {
  contentElement.innerHTML = `
    <div class="text-center py-8">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
      <p class="mt-2 text-gray-600">Loading preview...</p>
    </div>
  `;
}

// Initialize cron review modal (called after HTMX loads content)
window.AirCron.initCronReviewModal = function () {
  console.log("[AirCron] initCronReviewModal called");

  // Local modal state
  let reviewData = null;

  // Define modal functions in local scope
  function closeReviewModal() {
    document.getElementById("modal-container").innerHTML = "";
  }

  function loadReviewContent() {
    console.log("[AirCron] loadReviewContent called");
    reviewData = null;

    const contentElement = document.getElementById("review-content");
    if (!contentElement) {
      console.error("Review content element not found");
      return;
    }

    // Show loading state
    showLoadingState(contentElement);

    fetch("/api/cron/preview")
      .then((response) => {
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return response.json();
      })
      .then((data) => {
        console.log("Received cron preview data:", data);
        reviewData = data;

        if (data.error) {
          showError(contentElement, data.error);
          return;
        }

        // Build and render the modal HTML using helper functions
        contentElement.innerHTML = buildModalHTML(data);

        // Update button states
        updateButtonStates(data);
      })
      .catch((error) => {
        console.error("Error loading cron preview:", error);
        showError(contentElement, error.message, true);
      });
  }

  function applyChanges() {
    const btn = document.getElementById("apply-changes-btn");
    if (!btn) return;

    const originalText = btn.textContent;
    btn.disabled = true;
    btn.innerHTML =
      '<span class="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2 inline-block"></span>Applying...';

    fetch("/api/cron/apply", { method: "POST" })
      .then((response) => {
        if (!response.ok) {
          return response.json().then((data) => {
            throw new Error(
              data.error || `HTTP ${response.status}: ${response.statusText}`
            );
          });
        }
        return response.json();
      })
      .then((data) => {
        if (data.ok) {
          closeReviewModal();

          const statusEl = document.getElementById("status-message");
          if (statusEl) {
            statusEl.innerHTML =
              '<div class="text-green-200">✓ Successfully applied to crontab</div>';
            setTimeout(() => {
              statusEl.innerHTML = "";
            }, 3000);
          }

          // Refresh current zone
          if (
            window.AirCron &&
            window.AirCron.refreshZone &&
            window.currentZone
          ) {
            window.AirCron.refreshZone(window.currentZone);
          }
          // Always refresh allJobs after apply to avoid stale state
          fetch("/api/jobs/all")
            .then((r) => r.json())
            .then((data) => {
              window.allJobs = data.jobs || [];
              if (window.AirCron.renderHourlyTable) {
                window.AirCron.renderHourlyTable();
              }
            });
        } else {
          throw new Error(data.error || "Failed to apply changes");
        }
      })
      .catch((error) => {
        btn.disabled = false;
        btn.textContent = originalText;
        console.error("Error applying cron changes:", error);

        const statusEl = document.getElementById("status-message");
        if (statusEl) {
          statusEl.innerHTML = `<div class="text-red-200">✗ Error: ${error.message}</div>`;
          setTimeout(() => {
            statusEl.innerHTML = "";
          }, 5000);
        }
      });
  }

  // Attach event handlers to modal elements
  const closeBtns = document.querySelectorAll(
    '#modal-container button[onclick="closeReviewModal()"]'
  );
  closeBtns.forEach((btn) => {
    btn.onclick = closeReviewModal;
  });

  const applyBtn = document.getElementById("apply-changes-btn");
  if (applyBtn) {
    applyBtn.onclick = applyChanges;
  }

  // Start loading content
  loadReviewContent();
};
