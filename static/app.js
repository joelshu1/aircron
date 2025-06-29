// AirCron UI JavaScript helpers

// Utility functions
function showNotification(message, type = "info") {
  const statusContainer = document.getElementById("status-message");
  if (!statusContainer) return;

  const colorClass = type === "error" ? "text-red-200" : "text-green-200";
  const icon = type === "error" ? "✗" : "✓";

  statusContainer.innerHTML = `<div class="${colorClass}">${icon} ${message}</div>`;

  setTimeout(
    () => {
      statusContainer.innerHTML = "";
    },
    type === "error" ? 5000 : 3000
  );
}

// Handle HTMX form submissions
document.addEventListener("DOMContentLoaded", function () {
  // Format job form data to JSON
  document.body.addEventListener("htmx:configRequest", function (evt) {
    if (
      evt.detail.path.includes("/api/jobs/") &&
      (evt.detail.verb === "post" || evt.detail.verb === "put")
    ) {
      const formData = evt.detail.parameters;
      const jobData = {
        days: [],
        time: formData.time,
        action: formData.action,
        args: {},
      };

      // Collect selected days
      const dayInputs = document.querySelectorAll('input[name="days"]:checked');
      dayInputs.forEach((input) => {
        jobData.days.push(parseInt(input.value));
      });

      // Collect action-specific args
      if (formData.action === "play" && formData.uri) {
        jobData.args.uri = formData.uri;
      } else if (formData.action === "volume" && formData.volume) {
        jobData.args.volume = parseInt(formData.volume);
      }
      // Add label
      if (formData.label) {
        jobData.label = formData.label;
      }

      // Replace form data with JSON
      evt.detail.parameters = jobData;
      evt.detail.headers["Content-Type"] = "application/json";
    }
  });

  // Only run if the tab exists
  const daySelector = document.getElementById("schedule-day-selector");
  const hourlyTable = document.getElementById("schedule-hourly-table");
  if (!daySelector || !hourlyTable) return;

  let selectedDay = 1; // 1=Mon, 7=Sun
  let allJobs = window.allJobs || [];

  // Helper: get jobs for a given day and hour
  function getJobsForDayHour(day, hour) {
    // allJobs: [{...job...}]
    return allJobs.filter(
      (job) =>
        job.days.includes(day) && parseInt(job.time.split(":")[0]) === hour
    );
  }

  // Tooltip logic
  let tooltipDiv = null;
  function showTooltip(content, x, y) {
    if (!tooltipDiv) {
      tooltipDiv = document.createElement("div");
      tooltipDiv.style.position = "fixed";
      tooltipDiv.style.zIndex = 10000;
      tooltipDiv.style.background = "#222";
      tooltipDiv.style.color = "#fff";
      tooltipDiv.style.fontSize = "12px";
      tooltipDiv.style.padding = "4px 10px";
      tooltipDiv.style.borderRadius = "6px";
      tooltipDiv.style.pointerEvents = "none";
      document.body.appendChild(tooltipDiv);
    }
    tooltipDiv.textContent = content;
    tooltipDiv.style.display = "block";
    tooltipDiv.style.left = x + 12 + "px";
    tooltipDiv.style.top = y + 8 + "px";
  }
  function hideTooltip() {
    if (tooltipDiv) tooltipDiv.style.display = "none";
  }

  function renderHourlyTable() {
    let html = "";
    for (let h = 0; h < 24; h++) {
      const jobs = getJobsForDayHour(selectedDay, h);
      html += `<tr><td class='px-2 py-1 border-b text-sm text-gray-500'>${h
        .toString()
        .padStart(2, "0")}:00</td><td class='px-2 py-1 border-b'>`;
      if (jobs.length === 0) {
        html += `<span class='text-gray-300'>—</span>`;
      } else {
        jobs.forEach((job) => {
          let speakers = job.zone.startsWith("Custom:")
            ? job.zone.replace("Custom:", "").split(",")
            : [job.zone];
          // Use a single icon with tooltip for all speakers
          let speakerIcon = `<span class='inline-block align-middle mr-1 cursor-pointer speaker-tooltip' data-speakers='${speakers
            .map((s) => s.trim())
            .join(", ")}' tabindex='0' aria-label='Speakers'>🔈</span>`;
          let actionColor =
            {
              play: "bg-green-100 text-green-800",
              pause: "bg-yellow-100 text-yellow-800",
              resume: "bg-blue-100 text-blue-800",
              volume: "bg-purple-100 text-purple-800",
            }[job.action] || "bg-gray-100 text-gray-800";
          html += `<div class='flex items-center gap-2 mb-1 p-2 rounded ${actionColor}' style='pointer-events:auto;'>
            <span class='font-semibold text-blue-700'>${
              job.label ||
              job.action.charAt(0).toUpperCase() + job.action.slice(1)
            }</span>
            <span class='text-xs text-gray-500'>${job.time}</span>
            ${speakerIcon}
            <span class='text-xs text-gray-400 capitalize'>${job.action}</span>
            <button type='button' class='text-blue-500 hover:text-blue-700 text-xs edit-job-btn' data-zone='${
              job.zone
            }' data-id='${job.id}' title='Edit' tabindex='0'>✏️</button>
            <button type='button' class='text-red-500 hover:text-red-700 text-xs delete-job-btn' data-zone='${
              job.zone
            }' data-id='${job.id}' title='Delete' tabindex='0'>🗑</button>
          </div>`;
        });
      }
      html += `</td></tr>`;
    }
    hourlyTable.innerHTML = html;

    // Tooltip event delegation
    hourlyTable.querySelectorAll(".speaker-tooltip").forEach((el) => {
      el.addEventListener("mouseenter", function (e) {
        showTooltip(this.dataset.speakers, e.clientX, e.clientY);
      });
      el.addEventListener("mousemove", function (e) {
        showTooltip(this.dataset.speakers, e.clientX, e.clientY);
      });
      el.addEventListener("mouseleave", hideTooltip);
      el.addEventListener("focus", function (e) {
        showTooltip(
          this.dataset.speakers,
          e.target.getBoundingClientRect().left,
          e.target.getBoundingClientRect().bottom
        );
      });
      el.addEventListener("blur", hideTooltip);
    });

    // Edit/delete event delegation
    hourlyTable.querySelectorAll(".edit-job-btn").forEach((btn) => {
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        const zone = this.dataset.zone;
        const id = this.dataset.id;
        htmx.ajax("GET", `/modal/edit/${encodeURIComponent(zone)}/${id}`, {
          target: "#modal-container",
          swap: "innerHTML",
        });
      });
    });
    hourlyTable.querySelectorAll(".delete-job-btn").forEach((btn) => {
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        if (!confirm("Delete this job?")) return;
        const zone = this.dataset.zone;
        const id = this.dataset.id;
        fetch(`/api/jobs/${encodeURIComponent(zone)}/${id}`, {
          method: "DELETE",
        })
          .then((r) => {
            if (r.ok) {
              allJobs = allJobs.filter(
                (j) => !(j.zone === zone && j.id === id)
              );
              window.allJobs = allJobs;
              renderHourlyTable();
              showNotification("Job deleted", "info");
            } else {
              r.json().then((data) =>
                showNotification(data.error || "Delete failed", "error")
              );
            }
          })
          .catch(() => showNotification("Delete failed", "error"));
      });
    });
  }

  // Day selector click (fix styling)
  daySelector.querySelectorAll(".day-btn").forEach((btn) => {
    btn.addEventListener("click", function () {
      selectedDay = parseInt(this.dataset.day);
      daySelector
        .querySelectorAll(".day-btn")
        .forEach((b) =>
          b.classList.remove(
            "bg-blue-500",
            "text-white",
            "text-blue-900",
            "border-blue-700",
            "font-bold"
          )
        );
      this.classList.add(
        "bg-blue-500",
        "text-white",
        "border-blue-700",
        "font-bold"
      );
      renderHourlyTable();
    });
  });

  // Initial highlight and render
  const firstDayBtn = daySelector.querySelector('[data-day="1"]');
  if (firstDayBtn)
    firstDayBtn.classList.add(
      "bg-blue-500",
      "text-white",
      "border-blue-700",
      "font-bold"
    );
  // Fetch jobs if not present
  if (!window.allJobs) {
    fetch("/api/jobs/all")
      .then((r) => r.json())
      .then((data) => {
        allJobs = data.jobs || [];
        window.allJobs = allJobs;
        renderHourlyTable();
      });
  } else {
    renderHourlyTable();
  }
});

// Global functions for templates
window.AirCron = {
  showNotification,

  // Close modal
  closeModal: function () {
    document.getElementById("modal-container").innerHTML = "";
  },

  // Show the cron review modal
  showCronReviewModal: function () {
    const modalContainer = document.getElementById("modal-container");
    if (!modalContainer) {
      console.error("Modal container not found!");
      return;
    }
    htmx.ajax("GET", "/modal/cron/review", {
      target: modalContainer,
      swap: "innerHTML",
    });
  },

  // Refresh current zone
  refreshZone: function (zoneName) {
    if (zoneName) {
      htmx.ajax(
        "GET",
        `/zone/${encodeURIComponent(zoneName)}`,
        "#schedules-content"
      );
    }
  },

  // Update 'Add Schedule' button's zone context
  updateAddScheduleButton: function (zoneName) {
    const btn = document.getElementById("add-schedule-btn");
    if (btn) {
      btn.setAttribute("hx-get", `/modal/add/${encodeURIComponent(zoneName)}`);
    }
  },
};

// Ensure playlist picker is always loaded when job modal is inserted via HTMX
if (window.htmx) {
  document.body.addEventListener("htmx:afterSwap", function (evt) {
    // Check if the modal was swapped in
    const modal = document.getElementById("job-form");
    if (modal && typeof loadSavedPlaylists === "function") {
      loadSavedPlaylists();
    }
  });
}
