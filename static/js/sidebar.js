document.addEventListener("DOMContentLoaded", function () {
    const sidebar = document.querySelector(".sidebar");
    if (!sidebar) return;
    const currentPath = normalizePath(window.location.pathname);
    const toggles = sidebar.querySelectorAll(".submenu-toggle");
    const links = sidebar.querySelectorAll('a[href]:not(.submenu-toggle)');

    function normalizePath(path) {
        if (!path) return "/";
        const anchor = document.createElement("a");
        anchor.href = path;
        let cleanPath = anchor.pathname || "/";
        return cleanPath.length > 1 ? cleanPath.replace(/\/+$/, "") : cleanPath;
    }

    function closeSiblingMenus(menuItem) {
        const currentLevel = menuItem.parentElement;
        if (!currentLevel) return;
        currentLevel.querySelectorAll(":scope > .menu-item.has-submenu.open").forEach(function (openItem) {
            if (openItem !== menuItem && !openItem.classList.contains("active-branch")) {
                openItem.classList.remove("open");
            }
        });
    }

    function openParents(element) {
        let parentMenu = element.closest(".submenu");
        while (parentMenu) {
            const parentItem = parentMenu.closest(".menu-item.has-submenu");
            if (parentItem) parentItem.classList.add("open", "active-branch");
            parentMenu = parentItem ? parentItem.parentElement.closest(".submenu") : null;
        }
    }

    function markActiveLink() {
        let bestMatch = null;
        let bestLength = -1;
        links.forEach(function (link) {
            const href = link.getAttribute("href");
            if (!href || href === "#" || href.startsWith("javascript:")) return;
            const linkPath = normalizePath(href);
            const isExact = currentPath === linkPath;
            const isSection = linkPath !== "/" && currentPath.startsWith(linkPath + "/");
            if ((isExact || isSection) && linkPath.length > bestLength) {
                bestMatch = link;
                bestLength = linkPath.length;
            }
        });
        if (!bestMatch) return;
        bestMatch.classList.add("active-sidebar-link");
        const activeItem = bestMatch.closest(".menu-item");
        if (activeItem) activeItem.classList.add("active-item");
        openParents(bestMatch);
        bestMatch.scrollIntoView({ block: "nearest" });
    }

    toggles.forEach(function (toggle) {
        toggle.addEventListener("click", function (event) {
            event.preventDefault();
            const parentItem = toggle.closest(".menu-item.has-submenu");
            if (!parentItem) return;
            const shouldOpen = !parentItem.classList.contains("open");
            closeSiblingMenus(parentItem);
            parentItem.classList.toggle("open", shouldOpen);
        });
    });

    markActiveLink();
});
