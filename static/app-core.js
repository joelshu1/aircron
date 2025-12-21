// AirCron Core Module
// Shared utilities and UI state

window.AirCron = window.AirCron || {};

window.AirCron.state = window.AirCron.state || {
  jobs: [],
  speakers: [],
  filters: [],
  selectedDay: 1,
};

window.AirCron.closeModal = function () {
  const modalContainer = document.getElementById("modal-container");
  if (modalContainer) {
    modalContainer.innerHTML = "";
  }
};

window.AirCron.openModal = function (url) {
  const modalContainer = document.getElementById("modal-container");
  if (!modalContainer) return;
  if (window.htmx) {
    htmx.ajax("GET", url, { target: modalContainer, swap: "innerHTML" });
  } else {
    fetch(url)
      .then((resp) => resp.text())
      .then((html) => {
        modalContainer.innerHTML = html;
      });
  }
};

window.AirCron.showStatus = function (message, type = "info") {
  const statusEl = document.getElementById("status-message");
  if (!statusEl) return;
  const colorMap = {
    info: "text-blue-200",
    success: "text-green-200",
    error: "text-red-200",
    warning: "text-yellow-200",
  };
  statusEl.innerHTML = `<div class="${colorMap[type] || colorMap.info}">${message}</div>`;
  setTimeout(() => {
    if (statusEl.innerHTML) statusEl.innerHTML = "";
  }, 4000);
};

window.AirCron.applyCron = function () {
  return fetch("/api/cron/apply", { method: "POST" })
    .then((resp) => {
      if (!resp.ok) {
        return resp.json().then((data) => {
          throw new Error(data.error || "Failed to apply cron");
        });
      }
      return resp.json();
    })
    .then(() => {
      window.AirCron.showStatus("✓ Applied to cron", "success");
    })
    .catch((err) => {
      window.AirCron.showStatus(`✗ ${err.message}`, "error");
    });
};

window.AirCron.refreshSpeakers = function () {
  return fetch("/api/speakers/refresh", { method: "POST" })
    .then((resp) => resp.json())
    .then((data) => {
      window.AirCron.state.speakers = data.speakers || [];
      if (window.AirCron.renderFilters) {
        window.AirCron.renderFilters();
      }
      if (window.AirCron.renderControlPanelSpeakers) {
        window.AirCron.renderControlPanelSpeakers();
      }
    })
    .catch(() => {
      window.AirCron.showStatus("Failed to refresh speakers", "error");
    });
};
