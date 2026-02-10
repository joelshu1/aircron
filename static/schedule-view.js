// Schedule View Module
// Handles schedule rendering, filters, and add/edit/delete hooks

window.AirCron = window.AirCron || {};

const state = window.AirCron.state;

function zoneDisplay(zone) {
  if (zone === "All Speakers") return "All Speakers";
  if (zone.startsWith("Custom:")) {
    return zone.replace("Custom:", "").split(",").map((s) => s.trim()).join(" + ");
  }
  return zone;
}

function actionBadge(action) {
  const colors = {
    play: "bg-green-100 text-green-800",
    pause: "bg-yellow-100 text-yellow-800",
    resume: "bg-blue-100 text-blue-800",
    volume: "bg-purple-100 text-purple-800",
    connect: "bg-indigo-100 text-indigo-800",
    disconnect: "bg-rose-100 text-rose-800",
  };
  return colors[action] || "bg-gray-100 text-gray-800";
}

function getFilteredJobs() {
  if (!state.filters.length) return state.jobs;
  return state.jobs.filter((job) => state.filters.includes(job.zone));
}

function renderFilterPills() {
  const pills = document.getElementById("schedule-filter-pills");
  if (!pills) return;
  pills.innerHTML = "";

  if (!state.filters.length) {
    const empty = document.createElement("div");
    empty.className = "text-xs text-gray-500";
    empty.textContent = "Showing all zones";
    pills.appendChild(empty);
    return;
  }

  state.filters.forEach((zone) => {
    const pill = document.createElement("button");
    pill.type = "button";
    pill.className =
      "px-3 py-1 bg-blue-50 text-blue-700 text-xs rounded-full border border-blue-200 hover:bg-blue-100";
    pill.textContent = zoneDisplay(zone);
    pill.addEventListener("click", () => {
      state.filters = state.filters.filter((z) => z !== zone);
      renderFilters();
      renderSchedule();
    });
    pills.appendChild(pill);
  });
}

function renderFilters() {
  const list = document.getElementById("schedule-filters-list");
  if (!list) return;

  const zones = new Set();
  zones.add("All Speakers");
  (state.speakers || []).forEach((speaker) => zones.add(speaker));
  (state.jobs || []).forEach((job) => zones.add(job.zone));

  list.innerHTML = "";
  Array.from(zones)
    .filter(Boolean)
    .sort()
    .forEach((zone) => {
      const label = document.createElement("label");
      label.className = "flex items-center gap-2";

      const input = document.createElement("input");
      input.type = "checkbox";
      input.className = "rounded border-gray-300";
      input.checked = state.filters.includes(zone);
      input.addEventListener("change", () => {
        if (input.checked) {
          state.filters = [...new Set([...state.filters, zone])];
        } else {
          state.filters = state.filters.filter((z) => z !== zone);
        }
        renderFilterPills();
        renderSchedule();
      });

      const span = document.createElement("span");
      span.textContent = zoneDisplay(zone);

      label.appendChild(input);
      label.appendChild(span);
      list.appendChild(label);
    });

  renderFilterPills();
}

function showTooltip(content, x, y) {
  hideTooltip();
  const tooltip = document.createElement("div");
  tooltip.id = "speaker-tooltip";
  tooltip.className =
    "absolute bg-black text-white text-xs rounded py-1 px-2 z-10 whitespace-nowrap";
  tooltip.style.left = `${x + 10}px`;
  tooltip.style.top = `${y - 30}px`;
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
  const hourlyTable = document.getElementById("schedule-hourly-table");
  if (!hourlyTable) return;

  const jobs = getFilteredJobs().filter((job) =>
    job.days.includes(state.selectedDay)
  );

  const jobsByHour = new Map();
  jobs.forEach((job) => {
    const hour = parseInt(job.time.split(":")[0], 10);
    if (!jobsByHour.has(hour)) jobsByHour.set(hour, []);
    jobsByHour.get(hour).push(job);
  });

  let html = "";

  for (let hour = 0; hour < 24; hour++) {
    const hourJobs = (jobsByHour.get(hour) || []).sort((a, b) =>
      a.time.localeCompare(b.time)
    );
    const timeStr = hour.toString().padStart(2, "0") + ":00";

    html += `<tr class="schedule-hour-row hover:bg-gray-50 cursor-pointer" data-hour="${hour}">
      <td class="py-2 px-3 text-sm font-medium text-gray-900 border-r">${timeStr}</td>
      <td class="py-2 px-3">`;

    if (!hourJobs.length) {
      html += `<span class="text-gray-400 text-xs">No jobs</span>`;
    } else {
      hourJobs.forEach((job) => {
        const speakers =
          job.zone === "All Speakers"
            ? ["All Speakers"]
            : job.zone.startsWith("Custom:")
            ? job.zone.replace("Custom:", "").split(",")
            : [job.zone];

        let actionText = job.action;
        if (job.action === "play" && job.args.uri) {
          actionText = "Play Playlist";
        } else if (job.action === "play" && job.args.playlist) {
          actionText = "Play Playlist";
        } else if (job.action === "volume" && job.args.volume !== undefined) {
          const volumeScope =
            job.zone === "All Speakers" ? "Global app volume" : "Per-speaker volume";
          actionText = `${volumeScope} ${job.args.volume}%`;
        } else if (job.action === "resume") {
          actionText = "Resume Playback";
        } else if (job.action === "pause") {
          actionText = "Pause Playback";
        }

        const serviceLabel = job.service === "applemusic" ? "🍎" : "🎵";
        const zoneLabel = zoneDisplay(job.zone);

        html += `<div class="flex flex-wrap items-center gap-2 mb-1 p-2 rounded ${actionBadge(
          job.action
        )}" style="pointer-events:auto;">
          <span class="font-semibold text-blue-700">${job.label || actionText}</span>
          <span class="text-xs text-gray-500">${job.time}</span>
          <span class="text-xs text-gray-500">${serviceLabel}</span>
          <span class="text-xs text-gray-600">(${zoneLabel})</span>
          <span class="inline-block align-middle mr-1 cursor-pointer speaker-tooltip text-xs" data-speakers="${speakers
            .map((s) => s.trim())
            .join(", ")}" tabindex="0" aria-label="Speakers">🔈</span>
          <span class="text-sm font-medium">${actionText}</span>
          <button type="button" class="text-blue-500 hover:text-blue-700 text-xs edit-job-btn" data-zone="${job.zone}" data-id="${job.id}" title="Edit" tabindex="0">✏️</button>
          <button type="button" class="text-red-500 hover:text-red-700 text-xs delete-job-btn" data-zone="${job.zone}" data-id="${job.id}" title="Delete" tabindex="0">🗑</button>
        </div>`;
      });
    }

    html += `</td></tr>`;
  }

  hourlyTable.innerHTML = html;

  hourlyTable.querySelectorAll(".schedule-hour-row").forEach((row) => {
    row.addEventListener("click", () => {
      const hour = row.dataset.hour || "0";
      const time = `${hour.padStart(2, "0")}:00`;
      window.AirCron.openAddSchedule({ day: state.selectedDay, time });
    });
  });

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

  hourlyTable.querySelectorAll(".edit-job-btn").forEach((btn) => {
    btn.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      const zone = this.dataset.zone;
      const id = this.dataset.id;
      window.AirCron.openModal(
        `/modal/edit/${encodeURIComponent(zone)}/${id}`
      );
    });
  });

  hourlyTable.querySelectorAll(".delete-job-btn").forEach((btn) => {
    btn.addEventListener("click", async function (e) {
      e.preventDefault();
      e.stopPropagation();
      if (!confirm("Delete this job?")) return;
      const zone = this.dataset.zone;
      const id = this.dataset.id;

      try {
        // First, delete the job
        const deleteResp = await fetch(`/api/jobs/${encodeURIComponent(zone)}/${id}`, {
          method: "DELETE"
        });

        if (!deleteResp.ok) {
          const data = await deleteResp.json();
          throw new Error(data.error || "Delete failed");
        }

        // Refresh jobs if the function exists
        if (typeof window.AirCron.refreshJobs === "function") {
          await window.AirCron.refreshJobs();
        }

        // Apply cron changes
        const cronApplyResp = await window.AirCron.applyCron();

        // Only show success after all operations complete
        if (window.AirCron.showNotification) {
          window.AirCron.showNotification("Job deleted and cron updated", "success");
        }
      } catch (err) {
        if (window.AirCron.showNotification) {
          window.AirCron.showNotification(err.message || "Failed to delete job", "error");
        }
        console.error("Delete job error:", err);
        // Refresh jobs to ensure UI is in sync even after error
        if (typeof window.AirCron.refreshJobs === "function") {
          try {
            await window.AirCron.refreshJobs();
          } catch (refreshErr) {
            console.error("Failed to refresh jobs after delete error:", refreshErr);
          }
        }
      }
    });
  });
}

function renderSchedule() {
  renderHourlyTable();
}

window.AirCron.refreshJobs = function () {
  return fetch("/api/jobs/all")
    .then((r) => r.json())
    .then((data) => {
      state.jobs = data.jobs || [];
      renderFilters();
      renderSchedule();
    })
    .catch(() => {
      state.jobs = [];
      renderSchedule();
    });
};

window.AirCron.renderFilters = renderFilters;

window.AirCron.openAddSchedule = function ({ day, time } = {}) {
  const params = new URLSearchParams();
  if (day) params.set("day", day);
  if (time) params.set("time", time);
  const query = params.toString();
  const url = `/modal/add/${encodeURIComponent("All Speakers")}${
    query ? `?${query}` : ""
  }`;
  window.AirCron.openModal(url);
};

document.addEventListener("DOMContentLoaded", function () {
  const daySelector = document.getElementById("schedule-day-selector");
  if (daySelector) {
    daySelector.querySelectorAll(".day-btn").forEach((btn) => {
      btn.addEventListener("click", function () {
        daySelector.querySelectorAll(".day-btn").forEach((b) => {
          b.classList.remove(
            "bg-blue-600",
            "text-white",
            "border-blue-700",
            "font-semibold",
            "shadow-sm"
          );
          b.classList.add("bg-white", "text-gray-700", "border-gray-300", "hover:bg-blue-50");
          b.setAttribute("aria-pressed", "false");
        });

        this.classList.remove("bg-white", "text-gray-700", "border-gray-300", "hover:bg-blue-50");
        this.classList.add(
          "bg-blue-600",
          "text-white",
          "border-blue-700",
          "font-semibold",
          "shadow-sm"
        );
        this.setAttribute("aria-pressed", "true");

        state.selectedDay = parseInt(this.dataset.day, 10);
        renderSchedule();
      });
    });
  }

  const filterToggle = document.getElementById("schedule-filter-toggle");
  const filterPanel = document.getElementById("schedule-filters-panel");
  if (filterToggle && filterPanel) {
    filterToggle.addEventListener("click", () => {
      filterPanel.classList.toggle("hidden");
    });
  }

  const addButton = document.getElementById("schedule-add-schedule-btn");
  if (addButton) {
    addButton.addEventListener("click", () => {
      window.AirCron.openAddSchedule({ day: state.selectedDay });
    });
  }

  window.AirCron.refreshSpeakers();
  window.AirCron.refreshJobs();
});
