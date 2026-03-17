document.addEventListener("DOMContentLoaded", () => {

    // === 1. SLIDER LOGIC ===
    const slides = document.querySelectorAll(".slide");
    const dots = document.querySelectorAll(".slider_nav a");

    if (slides.length > 0) {
        let current = 0;
        let interval;

        function showSlide(index) {
            slides.forEach((slide, i) => {
                slide.style.display = i === index ? "block" : "none";
                dots[i]?.classList.toggle("active", i === index);
            });
            current = index;
        }

        function nextSlide() {
            showSlide((current + 1) % slides.length);
        }

        function startAutoSlide() {
            interval = setInterval(nextSlide, 5000);
        }

        dots.forEach((dot, index) => {
            dot.addEventListener("click", e => {
                e.preventDefault();
                showSlide(index);
                clearInterval(interval);
                startAutoSlide();
            });
        });

        showSlide(0);
        startAutoSlide();
    }

    // === 2. HORIZONTAL SCROLL LOGIC ===
    document.querySelectorAll(".scroll-container").forEach(container => {
        const scrollArea = container.querySelector(".novi_relesi");
        const leftBtn = container.querySelector(".scroll-btn.left");
        const rightBtn = container.querySelector(".scroll-btn.right");
        if (!scrollArea || !leftBtn || !rightBtn) return;

        const scrollAmount = 800;

        function updateButtons() {
            leftBtn.style.display = scrollArea.scrollLeft > 10 ? "block" : "none";
            rightBtn.style.display = scrollArea.scrollLeft < (scrollArea.scrollWidth - scrollArea.clientWidth - 10) ? "block" : "none";
        }

        rightBtn.addEventListener("click", () => scrollArea.scrollBy({ left: scrollAmount, behavior: "smooth" }));
        leftBtn.addEventListener("click", () => scrollArea.scrollBy({ left: -scrollAmount, behavior: "smooth" }));
        scrollArea.addEventListener("scroll", updateButtons);
        updateButtons();
    });

    // === 3. FILTERING & SORTING LOGIC ===
    const searchInput = document.getElementById("seriesSearch");
    const ratingFilter = document.getElementById("ratingFilter");
    const genreFilter = document.getElementById("genreFilter");
    const sourceFilter = document.getElementById("sourceFilter");
    const userScoreFilter = document.getElementById("userScoreFilter");
    const sortFilter = document.getElementById("sortFilter");
    const statusFilter = document.getElementById("statusFilter");

    const seriesContainer = document.querySelector(".series-list");
    let seriesRows = Array.from(document.querySelectorAll(".series-row"));

    let selectedGenres = [];

    function normalize(text) {
        return text ? text.toLowerCase().trim().replace(/\s+/g, " ") : "";
    }

    function updateGenreButtonLabel() {
        if (!genreFilter) return;
        const label = genreFilter.querySelector(".select-selected");
        if (!label) return;
        if (selectedGenres.length === 0) label.textContent = "Genres";
        else label.textContent = selectedGenres.length <= 2 ? selectedGenres.join(", ") : `${selectedGenres.length} Genres Selected`;
    }

    function sortSeries(container, sortVal) {
        const items = Array.from(container.querySelectorAll(".series-link"));
        items.sort((a, b) => {
            const aRow = a.querySelector(".series-row");
            const bRow = b.querySelector(".series-row");
            const aScore = parseFloat(aRow.dataset.userScore || 0);
            const bScore = parseFloat(bRow.dataset.userScore || 0);
            const aName = aRow.dataset.name.toLowerCase();
            const bName = bRow.dataset.name.toLowerCase();

            switch (sortVal) {
                case "score-desc": return bScore - aScore;
                case "score-asc": return aScore - bScore;
                case "name-asc": return aName.localeCompare(bName);
                default: return 0;
            }
        });
        items.forEach(item => container.appendChild(item));
    }

    window.applyFilters = function () {
        if (seriesRows.length === 0) return;

        const searchValue = searchInput ? normalize(searchInput.value) : "";
        const searchWords = searchValue.split(" ").filter(word => word !== "");
        const ratingVal = ratingFilter?.dataset.value || "";
        const sourceVal = sourceFilter?.dataset.value || "";
        const userScoreVal = userScoreFilter?.dataset.value || "";
        const sortVal = sortFilter?.dataset.value || "default";
        const statusVal = statusFilter?.dataset.value || "";

        // === FILTER VISIBILITY ===
        seriesRows.forEach(row => {
            const name = normalize(row.dataset.name);
            const rating = normalize(row.dataset.rating);
            const genre = normalize(row.dataset.genre);
            const source = normalize(row.dataset.source);
            const userScore = row.dataset.userScore || "";
            const status = row.dataset.status || "";

            const matchesSearch = searchWords.length === 0 || searchWords.every(word => name.includes(word));
            const matchesRating = ratingVal === "" || rating === ratingVal;
            const matchesGenre = selectedGenres.length === 0 || selectedGenres.every(g => genre.includes(g));
            const matchesSource = sourceVal === "" || source === sourceVal;
            const matchesUserScore = userScoreVal === "" || userScore === userScoreVal;
            const matchesStatus = statusVal === "" || status === statusVal;

            const isVisible = matchesSearch && matchesRating && matchesGenre && matchesSource && matchesUserScore && matchesStatus;
            row.style.display = isVisible ? "flex" : "none";
            if (row.parentElement.classList.contains("series-link")) row.parentElement.style.display = isVisible ? "block" : "none";
        });

        // === SORT SERIES ===
        const categorySections = document.querySelectorAll(".category-section");
        if (categorySections.length) {
            categorySections.forEach(section => sortSeries(section, sortVal));
        } else {
            sortSeries(seriesContainer, sortVal); // fallback for main list
        }
    };

    if (searchInput) searchInput.addEventListener("input", window.applyFilters);

    // === 4. CUSTOM SELECT LOGIC ===
    document.querySelectorAll(".custom-select").forEach(select => {
        const selected = select.querySelector(".select-selected");
        const options = select.querySelector(".select-options");
        if (!selected || !options) return;

        const optionItems = options.querySelectorAll("div");
        selected.addEventListener("click", e => {
            e.stopPropagation();
            document.querySelectorAll(".custom-select").forEach(s => { if (s !== select) s.classList.remove("active"); });
            select.classList.toggle("active");
        });

        optionItems.forEach(option => {
            option.addEventListener("click", () => {
                const val = option.dataset.value;
                selected.textContent = option.textContent;
                select.dataset.value = val;
                const hiddenInput = select.querySelector('input[type="hidden"]');
                if (hiddenInput) hiddenInput.value = val;
                select.classList.remove("active");
                if (typeof window.applyFilters === "function") window.applyFilters();
            });
        });
    });

    document.addEventListener("click", () => {
        document.querySelectorAll(".custom-select").forEach(s => s.classList.remove("active"));
    });

    // === 5. GENRE DROPDOWN PANEL LOGIC ===
    const genreButton = document.getElementById("genreFilter");
    const genreModal = document.getElementById("genreModal");
    const closeGenreModal = document.getElementById("closeGenreModal");
    const applyGenresBtn = document.getElementById("applyGenres");
    const genreCheckboxes = document.querySelectorAll(".genre-grid input");

    if (genreButton) {
        genreButton.addEventListener("click", e => { e.stopPropagation(); genreButton.classList.toggle("active"); });
        genreModal?.addEventListener("click", e => e.stopPropagation());
        closeGenreModal?.addEventListener("click", () => genreButton.classList.remove("active"));
        applyGenresBtn?.addEventListener("click", () => {
            selectedGenres = [];
            genreCheckboxes.forEach(cb => { if (cb.checked) selectedGenres.push(cb.value.toLowerCase()); });
            updateGenreButtonLabel();
            genreButton.classList.remove("active");
            if (typeof window.applyFilters === "function") window.applyFilters();
        });
    }

    // === 6. WHEEL SCROLL ===
    document.querySelectorAll(".wheel-scroll").forEach(container => {
        let scrollAmount = 0;
        let isScrolling = false;

        container.addEventListener("wheel", e => {
            e.preventDefault();
            scrollAmount += e.deltaY * -0.6;
            if (!isScrolling) smoothScroll();
        });

        function smoothScroll() {
            isScrolling = true;
            container.scrollLeft += scrollAmount;
            scrollAmount *= 0.85;
            if (Math.abs(scrollAmount) > 0.5) requestAnimationFrame(smoothScroll);
            else { scrollAmount = 0; isScrolling = false; }
        }
    });

    document.querySelectorAll(".home_podnaslov").forEach(title => {
        title.addEventListener("click", e => e.stopPropagation());
    });

});