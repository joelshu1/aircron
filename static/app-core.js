// AirCron Core Module
// Main application coordinator and global namespace

// Initialize global namespace
window.AirCron = window.AirCron || {};

// Core utility functions
window.AirCron.refreshZone = function (zoneName) {
  if (zoneName) {
    htmx.ajax(
      "GET",
      `/zone/${encodeURIComponent(zoneName)}`,
      "#schedules-content"
    );
  }
};

window.AirCron.updateAddScheduleButton = function (zoneName) {
  const btn = document.getElementById("add-schedule-btn");
  if (btn) {
    btn.setAttribute("hx-get", `/modal/add/${encodeURIComponent(zoneName)}`);
  }
};

window.AirCron.refreshCronJobsZone = function (zoneName) {
  if (zoneName) {
    htmx.ajax(
      "GET",
      `/zone/${encodeURIComponent(zoneName)}?cron=1`,
      "#cron-jobs-content"
    );
  }
};

// HTMX event handlers for cross-module coordination
if (window.htmx) {
  document.body.addEventListener("htmx:afterSwap", function (evt) {
    // Check if the modal was swapped in
    const modal = document.getElementById("job-form");
    if (modal && typeof loadSavedPlaylists === "function") {
      loadSavedPlaylists();
    }
  });
}

// Patch closeModal to also reload the sidebar after job add/edit
const originalCloseModal = window.AirCron.closeModal;
window.AirCron.closeModal = function () {
  if (typeof originalCloseModal === "function") originalCloseModal();
  // Find the active tab and reload the sidebar accordingly
  if (
    document
      .getElementById("tab-content-cron-jobs")
      .classList.contains("active")
  ) {
    // Reload the current zone in cron jobs tab (which also reloads sidebar)
    const activeZoneBtn = document.querySelector("#sidebar button.bg-blue-100");
    const zone = activeZoneBtn
      ? activeZoneBtn.textContent.trim().replace(/^([▾▸🎵]+)\s*/, "")
      : "All Speakers";
    window.AirCron.refreshCronJobsZone(zone);
  } else {
    // Reload the current zone in schedules tab
    const activeZoneBtn = document.querySelector("#sidebar button.bg-blue-100");
    const zone = activeZoneBtn
      ? activeZoneBtn.textContent.trim().replace(/^([▾▸🎵]+)\s*/, "")
      : "All Speakers";
    window.AirCron.refreshZone(zone);
  }
};
