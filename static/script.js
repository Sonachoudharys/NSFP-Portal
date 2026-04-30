/* ============================================================
   NATIONAL SCHEME FRAUD PORTAL — NSFP v2.0
   script.js | Developed by Sona Choudhary | 2026
   ============================================================ */

document.addEventListener("DOMContentLoaded", function () {

    // ─── DARK / LIGHT MODE TOGGLE ─────────────────────────────

    const toggle      = document.getElementById("darkToggle");
    const darkIcon    = document.getElementById("darkIcon");
    const darkLabel   = document.getElementById("darkLabel");

    // Auto night mode (19:00 – 06:00) only on first visit
    const saved = localStorage.getItem("nsfp_theme");

    if (!saved) {
        const hour = new Date().getHours();
        if (hour >= 19 || hour <= 6) {
            applyTheme("dark");
        } else {
            applyTheme("light");
        }
    } else {
        applyTheme(saved);
    }

    if (toggle) {
        toggle.addEventListener("click", function () {
            const isDark = document.body.classList.contains("dark");
            applyTheme(isDark ? "light" : "dark");
        });
    }

    function applyTheme(theme) {
        if (theme === "dark") {
            document.body.classList.remove("light");
            document.body.classList.add("dark");
            if (darkIcon)  darkIcon.textContent  = "☀";
            if (darkLabel) darkLabel.textContent  = "Light Mode";
        } else {
            document.body.classList.remove("dark");
            document.body.classList.add("light");
            if (darkIcon)  darkIcon.textContent  = "🌙";
            if (darkLabel) darkLabel.textContent  = "Dark Mode";
        }
        localStorage.setItem("nsfp_theme", theme);
    }

    // ─── ACTIVE NAV LINK HIGHLIGHT ────────────────────────────

    const currentPath = window.location.pathname;
    document.querySelectorAll(".nav-link").forEach(link => {
        if (link.getAttribute("href") && link.getAttribute("href") === currentPath) {
            link.classList.add("active");
        }
    });

    // ─── PREDICT RESULT DISPLAY ───────────────────────────────

    const resultEl = document.getElementById("predictResult");
    const params   = new URLSearchParams(window.location.search);

    if (resultEl && params.has("result")) {
        const r = decodeURIComponent(params.get("result"));
        resultEl.style.display = "block";
        if (r.includes("FRAUD")) {
            resultEl.classList.add("fraud");
            resultEl.textContent = "🚨 " + r;
        } else {
            resultEl.classList.add("genuine");
            resultEl.textContent = "✅ " + r;
        }

        // Scroll to result
        resultEl.scrollIntoView({ behavior: "smooth", block: "nearest" });

        // Auto-hide after 8 seconds
        setTimeout(() => {
            resultEl.style.transition = "opacity 0.5s";
            resultEl.style.opacity    = "0";
            setTimeout(() => resultEl.style.display = "none", 500);
        }, 8000);
    }

    // ─── FORM LOADING STATE ───────────────────────────────────

    const predictForm = document.getElementById("predictForm");
    const submitBtn   = document.getElementById("submitBtn");

    if (predictForm && submitBtn) {
        predictForm.addEventListener("submit", function () {
            const btnText   = submitBtn.querySelector(".btn-text");
            const btnLoader = submitBtn.querySelector(".btn-loader");
            if (btnText)   btnText.style.display   = "none";
            if (btnLoader) btnLoader.style.display = "inline";
            submitBtn.disabled = true;
        });
    }

    // ─── TABLE ROW COLORING ───────────────────────────────────
    // Color fraud rows red, genuine green in beneficiary table

    document.querySelectorAll(".table-scroll table tbody tr").forEach(row => {
        const cells = row.querySelectorAll("td");
        cells.forEach(cell => {
            const val = cell.textContent.trim();
            if (val === "1") {
                // fraud_predicted = 1 → red tint
                row.style.borderLeft = "3px solid rgba(239,68,68,0.5)";
                cell.style.color     = "#f87171";
                cell.style.fontWeight = "700";
            }
        });
    });

    // ─── TOPBAR BREADCRUMB UPDATE ─────────────────────────────

    const breadcrumbMap = {
        "/dashboard": "Dashboard",
        "/heatmap":   "India Fraud Map",
        "/accuracy":  "Model Accuracy",
        "/report":    "Download Report",
    };

    const crumb = document.querySelector(".breadcrumb-current");
    if (crumb && breadcrumbMap[currentPath]) {
        crumb.textContent = breadcrumbMap[currentPath];
    }

    // ─── PANEL ENTRANCE ANIMATION ─────────────────────────────

    const panels = document.querySelectorAll(".panel, .stat-card");
    if ("IntersectionObserver" in window) {
        const obs = new IntersectionObserver(entries => {
            entries.forEach((entry, i) => {
                if (entry.isIntersecting) {
                    entry.target.style.animationPlayState = "running";
                    obs.unobserve(entry.target);
                }
            });
        }, { threshold: 0.1 });

        panels.forEach(p => {
            p.style.animationPlayState = "paused";
            obs.observe(p);
        });
    }

});
