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
