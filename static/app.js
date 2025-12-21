// AirCron UI - Main Coordinator
// Clean, modular architecture with separation of concerns

// Ensure the namespace exists (modules extend it)
window.AirCron = window.AirCron || {};

document.addEventListener("DOMContentLoaded", function () {
  console.log("🚀 AirCron UI initialized");
});

window.editPlaylist = function (playlistId) {
  if (window.AirCron && window.AirCron.openModal) {
    window.AirCron.openModal(`/modal/playlist/edit/${playlistId}`);
    return;
  }
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
