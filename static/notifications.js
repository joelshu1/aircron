// Notifications Module
// Handles all toast notifications and status messages

function showNotification(message, type = "info") {
  const container = document.getElementById("notification-container");
  if (!container) return;

  const notification = document.createElement("div");
  notification.className = `notification ${type} show`;

  const colors = {
    info: "bg-blue-500",
    success: "bg-green-500",
    error: "bg-red-500",
    warning: "bg-yellow-500",
  };

  notification.innerHTML = `
    <div class="${colors[type]} text-white px-4 py-3 rounded-lg shadow-lg flex items-center justify-between">
      <span>${message}</span>
      <button onclick="this.parentElement.parentElement.remove()" class="ml-4 text-white hover:text-gray-200">
        ✕
      </button>
    </div>
  `;

  container.appendChild(notification);

  // Auto-remove after 4 seconds
  setTimeout(() => {
    if (notification.parentNode) {
      notification.remove();
    }
  }, 4000);
}

// Export to global namespace
window.AirCron = window.AirCron || {};
window.AirCron.showNotification = showNotification;
