// Control Panel Drawer Module

window.AirCron = window.AirCron || {};

function setPanelOpen(open) {
  const panel = document.getElementById("control-panel");
  const overlay = document.getElementById("control-panel-overlay");
  if (!panel || !overlay) return;
  if (open) {
    panel.classList.remove("translate-x-full");
    overlay.classList.remove("hidden");
  } else {
    panel.classList.add("translate-x-full");
    overlay.classList.add("hidden");
  }
}

window.AirCron.toggleControlPanel = function (open) {
  setPanelOpen(open);
  if (open) {
    window.AirCron.refreshSpeakers();
    loadControlPlaylists();
  }
};

function updateSpeakerCheckboxes(root) {
  const allBox = root.querySelector('input[value="All Speakers"]');
  const others = Array.from(root.querySelectorAll("input")).filter(
    (cb) => cb.value !== "All Speakers"
  );
  if (!allBox) return;
  if (allBox.checked) {
    others.forEach((cb) => {
      cb.checked = false;
      cb.disabled = true;
      cb.parentElement.classList.add("opacity-50");
    });
  } else {
    others.forEach((cb) => {
      cb.disabled = false;
      cb.parentElement.classList.remove("opacity-50");
    });
  }
}

function updateControlSpeakerSelectionForVolumeTarget() {
  const list = document.getElementById("control-speakers-list");
  if (!list) return;
  const target = getControlVolumeTarget();
  const allBox = list.querySelector('input[value="All Speakers"]');
  const others = Array.from(list.querySelectorAll("input")).filter(
    (cb) => cb.value !== "All Speakers"
  );
  if (!allBox) return;

  if (target === "global") {
    allBox.checked = true;
    updateSpeakerCheckboxes(list);
    return;
  }

  if (allBox.checked) {
    allBox.checked = false;
  }
  updateSpeakerCheckboxes(list);
  if (!others.some((cb) => cb.checked) && others[0]) {
    others[0].checked = true;
  }
}

function buildZoneFromSelection(root) {
  const selected = Array.from(root.querySelectorAll("input:checked")).map(
    (cb) => cb.value
  );
  if (!selected.length) return "";
  if (selected.includes("All Speakers")) return "All Speakers";
  if (selected.length === 1) return selected[0];
  return `Custom:${selected.join(",")}`;
}

function getControlVolumeTarget() {
  const selected = document.querySelector(
    'input[name="control-volume-target"]:checked'
  );
  return selected ? selected.value : "global";
}

function updateVolumeApplyLabel() {
  const label = document.getElementById("control-volume-apply-text");
  if (!label) return;
  const target = getControlVolumeTarget();
  label.textContent =
    target === "global" ? "Apply Global Volume" : "Apply Per-Speaker Volume";
}

window.AirCron.renderControlPanelSpeakers = function () {
  const list = document.getElementById("control-speakers-list");
  if (!list) return;
  list.innerHTML = "";

  const speakers = window.AirCron.state.speakers || [];
  const items = ["All Speakers", ...speakers.filter((s) => s !== "All Speakers")];

  items.forEach((speaker) => {
    const label = document.createElement("label");
    label.className = "flex items-center gap-2 cursor-pointer";
    const input = document.createElement("input");
    input.type = "checkbox";
    input.value = speaker;
    input.addEventListener("change", () => updateSpeakerCheckboxes(list));
    const span = document.createElement("span");
    span.textContent = speaker;
    label.appendChild(input);
    label.appendChild(span);
    list.appendChild(label);
  });

  const allBox = list.querySelector('input[value="All Speakers"]');
  if (allBox) {
    allBox.checked = true;
    updateSpeakerCheckboxes(list);
  }
  updateControlSpeakerSelectionForVolumeTarget();
};

function loadControlPlaylists() {
  fetch("/api/playlists")
    .then((resp) => {
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);
      }
      return resp.json();
    })
    .then((data) => {
      const select = document.getElementById("control-playlist");
      if (!select) return;
      const service =
        document.getElementById("control-service")?.value || "spotify";
      select.innerHTML = `<option value="">Play current / last</option>`;
      (data.playlists || [])
        .filter((p) => p.service === service)
        .forEach((playlist) => {
          const option = document.createElement("option");
          option.value =
            service === "spotify" ? playlist.uri || "" : playlist.playlist || "";
          option.textContent = playlist.name;
          select.appendChild(option);
        });
    })
    .catch((err) => {
      console.error("Failed to load playlists:", err);
      if (window.AirCron.showNotification) {
        window.AirCron.showNotification("Failed to load playlists", "error");
      }
    });
}

function sendControlAction(action, args = {}, options = {}) {
  const service =
    document.getElementById("control-service")?.value || "spotify";
  const list = document.getElementById("control-speakers-list");
  const zone = options.zone || (list ? buildZoneFromSelection(list) : "All Speakers");
  if (!zone) {
    window.AirCron.showNotification("Select at least one speaker", "error");
    return;
  }

  return fetch("/api/control", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, service, zone, args }),
  })
    .then((resp) => {
      if (!resp.ok) {
        return resp.json().then((data) => {
          throw new Error(data.error || "Control action failed");
        });
      }
    })
    .then(() => {
      if (window.AirCron.showNotification) {
        window.AirCron.showNotification("Action sent", "success");
      }
    })
    .catch((err) => {
      if (window.AirCron.showNotification) {
        window.AirCron.showNotification(err.message, "error");
      }
    });
}

document.addEventListener("DOMContentLoaded", function () {
  const closeBtn = document.getElementById("control-panel-close");
  const overlay = document.getElementById("control-panel-overlay");
  const serviceSelect = document.getElementById("control-service");
  const volumeInput = document.getElementById("control-volume");
  const volumeDisplay = document.getElementById("control-volume-display");

  if (closeBtn) closeBtn.addEventListener("click", () => setPanelOpen(false));
  if (overlay) overlay.addEventListener("click", () => setPanelOpen(false));

  if (serviceSelect) {
    serviceSelect.addEventListener("change", loadControlPlaylists);
  }

  if (volumeInput && volumeDisplay) {
    volumeDisplay.textContent = `${volumeInput.value}%`;
    volumeInput.addEventListener("input", () => {
      volumeDisplay.textContent = `${volumeInput.value}%`;
    });
  }

  const connectBtn = document.getElementById("control-connect");
  const disconnectBtn = document.getElementById("control-disconnect");
  const playBtn = document.getElementById("control-play");
  const pauseBtn = document.getElementById("control-pause");
  const volumeApply = document.getElementById("control-volume-apply");
  const volumeTargets = document.querySelectorAll(
    'input[name="control-volume-target"]'
  );

  volumeTargets.forEach((radio) => {
    radio.addEventListener("change", () => {
      updateVolumeApplyLabel();
      updateControlSpeakerSelectionForVolumeTarget();
    });
  });
  updateVolumeApplyLabel();

  if (connectBtn) connectBtn.addEventListener("click", () => sendControlAction("connect"));
  if (disconnectBtn) disconnectBtn.addEventListener("click", () => sendControlAction("disconnect"));
  if (pauseBtn) pauseBtn.addEventListener("click", () => sendControlAction("pause"));

  if (playBtn) {
    playBtn.addEventListener("click", () => {
      const service =
        document.getElementById("control-service")?.value || "spotify";
      const playlistValue = document.getElementById("control-playlist")?.value;
      if (playlistValue) {
        const args =
          service === "spotify"
            ? { uri: playlistValue }
            : { playlist: playlistValue };
        sendControlAction("play", args);
      } else {
        sendControlAction("resume");
      }
    });
  }

  if (volumeApply) {
    volumeApply.addEventListener("click", () => {
      const volume = document.getElementById("control-volume")?.value || "50";
      const volumeTarget = getControlVolumeTarget();
      const list = document.getElementById("control-speakers-list");
      let zone = list ? buildZoneFromSelection(list) : "";
      if (volumeTarget === "global") {
        zone = "All Speakers";
      } else if (!zone || zone === "All Speakers") {
        window.AirCron.showNotification(
          "Select specific speakers for per-speaker volume",
          "error"
        );
        return;
      }
      sendControlAction("volume", { volume: Number(volume) }, { zone });
    });
  }
});
