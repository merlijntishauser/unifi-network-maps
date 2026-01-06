document.addEventListener("DOMContentLoaded", () => {
  const legend = document.querySelector("[data-unifi-legend]");
  const sidebar = document.querySelector(".md-sidebar--secondary .md-sidebar__scrollwrap");
  if (!legend || !sidebar) {
    return;
  }
  const wrapper = document.createElement("div");
  wrapper.className = "unifi-legend-sidebar";
  const title = document.createElement("div");
  title.className = "unifi-legend-title";
  title.textContent = "Legend";
  wrapper.appendChild(title);
  wrapper.appendChild(legend.cloneNode(true));
  sidebar.appendChild(wrapper);
  legend.classList.add("unifi-legend-hidden");
});
