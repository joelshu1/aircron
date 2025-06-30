// AirCron UI - Main Coordinator
// Clean, modular architecture with separation of concerns

// Ensure the namespace exists (modules extend it)
window.AirCron = window.AirCron || {};

// Application initialization
document.addEventListener("DOMContentLoaded", function () {
  console.log("🚀 AirCron UI initialized with modular architecture");

  // Global application state
  window.allJobs = window.allJobs || [];

  // Initialize any legacy compatibility if needed
  if (typeof initLegacyFeatures === "function") {
    initLegacyFeatures();
  }
});
