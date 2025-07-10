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

  // Job modal save handler
  document.body.addEventListener("submit", function (e) {
    const form = e.target;
    if (form && form.id === "job-form") {
      e.preventDefault();
      const formData = new FormData(form);
      // Build zone string from selected speakers
      const speakers = formData
        .getAll("speakers")
        .map((s) => s.trim())
        .filter(Boolean);

      // Client-side validation to ensure at least one speaker is selected.
      if (speakers.length === 0) {
        if (window.AirCron && window.AirCron.showNotification) {
          window.AirCron.showNotification(
            "You must select at least one speaker.",
            "error"
          );
        } else {
          alert("You must select at least one speaker.");
        }
        // Re-enable the save button before stopping
        const saveBtn = form.querySelector("button[type='submit']");
        const savingIndicator = form.querySelector("#saving-indicator");
        const saveText = form.querySelector("#save-text");
        if (saveBtn) {
          saveBtn.disabled = false;
          savingIndicator.classList.add("hidden");
          saveText.classList.remove("hidden");
        }
        return; // Stop submission
      }

      let zone = "";
      if (speakers.length === 1) {
        zone = speakers[0];
      } else {
        // More than one speaker
        if (speakers.includes("All Speakers")) {
          zone = "All Speakers";
        } else {
          // Sort for consistent zone string: "Custom:A,B" not "Custom:B,A"
          zone = "Custom:" + speakers.sort().join(",");
        }
      }
      // Build job data
      const days = formData.getAll("days").map(Number);
      const time = formData.get("time");
      const action = formData.get("action");
      const label = formData.get("label")?.trim() || "";
      const service = formData.get("service")?.trim() || "spotify";
      const args = {};
      if (action === "play") {
        if (service === "applemusic") {
          args.playlist = formData.get("playlist")?.trim() || "";
        } else {
          args.uri = formData.get("uri")?.trim() || "";
        }
      } else if (action === "volume") {
        args.volume = Number(formData.get("volume"));
      }
      const data = { days, time, action, args, label, zone, service };
      const url = form.getAttribute("data-url");
      const method = form.getAttribute("data-method") || "POST";
      const saveBtn = form.querySelector("button[type='submit']");
      const savingIndicator = form.querySelector("#saving-indicator");
      const saveText = form.querySelector("#save-text");
      if (saveBtn && savingIndicator && saveText) {
        saveBtn.disabled = true;
        savingIndicator.classList.remove("hidden");
        saveText.classList.add("hidden");
      }
      fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      })
        .then(async (resp) => {
          if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            throw new Error(err.error || `HTTP ${resp.status}`);
          }
          return resp.json();
        })
        .then(() => {
          if (window.AirCron && window.AirCron.showNotification) {
            window.AirCron.showNotification(
              method === "POST" ? "Schedule saved" : "Schedule updated",
              "success"
            );
          }
          if (
            window.AirCron &&
            typeof window.AirCron.closeModal === "function"
          ) {
            window.AirCron.closeModal();
          }
        })
        .catch((err) => {
          if (window.AirCron && window.AirCron.showNotification) {
            window.AirCron.showNotification(
              err.message || "Failed to save schedule",
              "error"
            );
          }
        })
        .finally(() => {
          if (saveBtn && savingIndicator && saveText) {
            saveBtn.disabled = false;
            savingIndicator.classList.add("hidden");
            saveText.classList.remove("hidden");
          }
        });
    }
  });
});

window.editPlaylist = function (playlistId) {
  const modalContainer = document.getElementById("modal-container");
  if (!modalContainer) return;
  fetch(`/modal/playlist/edit/${playlistId}`)
    .then((resp) => {
      if (!resp.ok) throw new Error("Failed to load edit modal");
      return resp.text();
    })
    .then((html) => {
      modalContainer.innerHTML = html;
    })
    .catch((err) => {
      if (window.AirCron && window.AirCron.showNotification) {
        window.AirCron.showNotification(err.message, "error");
      }
    });
};

window.deletePlaylist = function (playlistId) {
  if (!confirm("Are you sure you want to delete this playlist?")) return;
  fetch(`/api/playlists/${playlistId}`, { method: "DELETE" })
    .then((resp) => {
      if (resp.status === 204) {
        if (window.AirCron && window.AirCron.showNotification) {
          window.AirCron.showNotification("Playlist deleted", "success");
        }
        if (typeof loadPlaylistsContent === "function") {
          loadPlaylistsContent();
        }
      } else {
        return resp.json().then((data) => {
          throw new Error(data.error || "Failed to delete playlist");
        });
      }
    })
    .catch((err) => {
      if (window.AirCron && window.AirCron.showNotification) {
        window.AirCron.showNotification(err.message, "error");
      }
    });
};
