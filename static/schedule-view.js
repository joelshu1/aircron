// Schedule View Module
// Handles the hourly table view and schedule visualization

window.AirCron = window.AirCron || {};

// Utility functions for schedule display
function getJobsForDayHour(day, hour) {
  if (!window.allJobs) return [];
  const filtered = window.allJobs.filter(
    (job) => job.days.includes(day) && parseInt(job.time.split(":")[0]) === hour
  );
  if (filtered.length > 0) {
    console.log(
      `Found ${filtered.length} jobs for day ${day} hour ${hour}:`,
      filtered
    );
  }
  return filtered;
}

function showTooltip(content, x, y) {
  hideTooltip();
  const tooltip = document.createElement("div");
  tooltip.id = "speaker-tooltip";
  tooltip.className =
    "absolute bg-black text-white text-xs rounded py-1 px-2 z-10 whitespace-nowrap";
  tooltip.style.left = x + 10 + "px";
  tooltip.style.top = y - 30 + "px";
  tooltip.textContent = content;
  document.body.appendChild(tooltip);

  setTimeout(() => {
    if (tooltip.parentNode) {
      tooltip.style.opacity = "0";
      setTimeout(() => tooltip.remove(), 200);
    }
  }, 2000);
}

function hideTooltip() {
  const existing = document.getElementById("speaker-tooltip");
  if (existing) existing.remove();
}

function renderHourlyTable() {
  // Try both possible table IDs
  let hourlyTable = document.getElementById("schedule-hourly-table");
  if (!hourlyTable) {
    hourlyTable = document.querySelector("#hourly-table tbody");
  }

  // Try both possible day selector IDs
  let daySelector = document.getElementById("schedule-day-selector");
  if (!daySelector) {
    daySelector = document.getElementById("day-selector");
  }

  if (!hourlyTable || !daySelector) {
    console.log("Missing elements:", {
      hourlyTable: !!hourlyTable,
      daySelector: !!daySelector,
    });
    return;
  }

  const selectedDay = parseInt(
    daySelector.querySelector(".bg-blue-600, .bg-blue-500")?.dataset.day || "1"
  );

  console.log(
    "Rendering table for day:",
    selectedDay,
    "with jobs:",
    window.allJobs?.length || 0
  );

  let html = "";

  for (let hour = 0; hour < 24; hour++) {
    const jobs = getJobsForDayHour(selectedDay, hour);
    if (jobs.length > 0) {
      console.log(`Hour ${hour}: found ${jobs.length} jobs`);
    }
    const timeStr = hour.toString().padStart(2, "0") + ":00";

    html += `<tr class='hover:bg-gray-50'><td class='py-2 px-3 text-sm font-medium text-gray-900 border-r'>${timeStr}</td><td class='py-2 px-3'>`;

    if (jobs.length === 0) {
      html += `<span class='text-gray-400 text-xs'>No jobs</span>`;
    } else {
      jobs.forEach((job) => {
        const speakers =
          job.zone === "All Speakers"
            ? ["All Speakers"]
            : job.zone.startsWith("Custom:")
            ? job.zone.replace("Custom:", "").split(",")
            : [job.zone];

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

        // Create descriptive action text
        let actionText = job.action;
        if (job.action === "play" && job.args.uri) {
          actionText = "Play Playlist";
        } else if (job.action === "volume" && job.args.volume !== undefined) {
          actionText = `Volume → ${job.args.volume}%`;
        } else if (job.action === "resume") {
          actionText = "Resume Playback";
        } else if (job.action === "pause") {
          actionText = "Pause Playback";
        }

        html += `<div class='flex items-center gap-2 mb-1 p-2 rounded ${actionColor}' style='pointer-events:auto;'>
          <span class='font-semibold text-blue-700'>${
            job.label || actionText
          }</span>
          <span class='text-xs text-gray-500'>${job.time}</span>
          ${speakerIcon}
          <span class='text-sm font-medium'>${actionText}</span>
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
      fetch(`/api/jobs/${encodeURIComponent(zone)}/${id}`, { method: "DELETE" })
        .then((r) => {
          if (r.ok) {
            window.allJobs = window.allJobs.filter(
              (j) => !(j.zone === zone && j.id === id)
            );
            renderHourlyTable();
            if (window.AirCron.showNotification) {
              window.AirCron.showNotification("Job deleted", "info");
            }
          } else {
            r.json().then((data) => {
              if (window.AirCron.showNotification) {
                window.AirCron.showNotification(
                  data.error || "Delete failed",
                  "error"
                );
              }
            });
          }
        })
        .catch(() => {
          if (window.AirCron.showNotification) {
            window.AirCron.showNotification("Delete failed", "error");
          }
        });
    });
  });
}

// Initialize schedule view when DOM is ready
document.addEventListener("DOMContentLoaded", function () {
  // Try both possible day selector IDs
  let daySelector = document.getElementById("schedule-day-selector");
  if (!daySelector) {
    daySelector = document.getElementById("day-selector");
  }
  if (!daySelector) {
    console.log("No day selector found for schedule view");
    return;
  }

  console.log("Found day selector:", daySelector.id);

  // Day selector click handlers
  daySelector.querySelectorAll(".day-btn").forEach((btn) => {
    btn.addEventListener("click", function () {
      // Reset all buttons to default state
      daySelector.querySelectorAll(".day-btn").forEach((b) => {
        b.classList.remove(
          "bg-blue-600",
          "text-white",
          "border-blue-700",
          "font-bold",
          "shadow-sm"
        );
        b.classList.add("bg-white", "text-gray-700", "border-gray-300");
      });

      // Set this button to active state
      this.classList.remove("bg-white", "text-gray-700", "border-gray-300");
      this.classList.add(
        "bg-blue-600",
        "text-white",
        "border-blue-700",
        "font-bold",
        "shadow-sm"
      );

      renderHourlyTable();
    });
  });

  // Initial highlight and render
  const firstDayBtn = daySelector.querySelector('[data-day="1"]');
  if (firstDayBtn) {
    firstDayBtn.classList.remove(
      "bg-white",
      "text-gray-700",
      "border-gray-300"
    );
    firstDayBtn.classList.add(
      "bg-blue-600",
      "text-white",
      "border-blue-700",
      "font-bold",
      "shadow-sm"
    );
  }

  // Always fetch jobs to ensure fresh data
  console.log("Loading jobs data...");
  fetch("/api/jobs/all")
    .then((r) => r.json())
    .then((data) => {
      console.log("Jobs loaded:", data);
      window.allJobs = data.jobs || [];
      renderHourlyTable();
    })
    .catch((error) => {
      console.error("Error loading jobs:", error);
      window.allJobs = [];
      renderHourlyTable();
    });
});

// Export functions to global namespace
window.AirCron.renderHourlyTable = renderHourlyTable;
