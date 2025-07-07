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

  // Playlist modal save handler
  document.body.addEventListener("submit", function (e) {
    const form = e.target;
    if (form && form.id === "playlist-form") {
      e.preventDefault();
      const formData = new FormData(form);
      const data = {
        name: formData.get("name")?.trim() || "",
        description: formData.get("description")?.trim() || "",
        uri: formData.get("uri")?.trim() || "",
      };
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
              method === "POST" ? "Playlist saved" : "Playlist updated",
              "success"
            );
          }
          if (
            window.AirCron &&
            typeof window.AirCron.closeModal === "function"
          ) {
            window.AirCron.closeModal();
          }
          // Refresh playlists tab if present
          if (typeof loadPlaylistsContent === "function") {
            loadPlaylistsContent();
          }
        })
        .catch((err) => {
          if (window.AirCron && window.AirCron.showNotification) {
            window.AirCron.showNotification(
              err.message || "Failed to save playlist",
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
