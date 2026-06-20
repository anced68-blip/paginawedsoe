document.addEventListener("DOMContentLoaded", () => {
    const cards = document.querySelectorAll(".panel, .kpi-card, .auth-card, .auth-hero, .profile-hero");
    cards.forEach((card, index) => {
        card.style.opacity = 0;
        card.style.transform = "translateY(14px)";
        setTimeout(() => {
            card.style.transition = "0.45s ease";
            card.style.opacity = 1;
            card.style.transform = "translateY(0)";
        }, 70 * index);
    });

    document.querySelectorAll(".check-switch input").forEach((check) => {
        const row = check.closest("tr");
        const points = row ? row.querySelector("input[type='number']") : null;

        const sync = () => {
            if (!points) return;
            if (!check.checked) {
                points.dataset.lastValue = points.value || "0";
                points.value = 0;
                points.disabled = true;
            } else {
                points.disabled = false;
                if (points.value === "0" && points.dataset.lastValue) {
                    points.value = points.dataset.lastValue;
                }
            }
        };

        check.addEventListener("change", sync);
        sync();
    });
});
