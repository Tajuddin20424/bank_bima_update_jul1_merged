(function () {
    const search = document.getElementById("patient_search");
    if (!search) return;
    const results = document.getElementById("patient_search_results");
    let timer;
    let patients = [];
    let activeIndex = -1;

    search.addEventListener("input", function () {
        clearTimeout(timer);
        const query = search.value.trim();
        if (!query) {
            results.innerHTML = "";
            patients = [];
            activeIndex = -1;
            return;
        }
        activeIndex = -1;
        timer = setTimeout(() => loadPatients(query), 250);
    });

    search.addEventListener("keydown", function (event) {
        if (event.key === "ArrowDown" || event.key === "ArrowUp") {
            if (!patients.length) return;
            event.preventDefault();
            activeIndex = event.key === "ArrowDown"
                ? Math.min(activeIndex + 1, patients.length - 1)
                : Math.max(activeIndex - 1, 0);
            highlightPatient();
            return;
        }
        if (event.key !== "Enter") return;
        event.preventDefault();

        if (activeIndex >= 0 && patients[activeIndex]) {
            selectPatient(patients[activeIndex]);
            return;
        }

        const query = search.value.trim();
        if (!query) return;

        loadPatients(query);
    });

    function loadPatients(query) {
        const url = search.dataset.searchUrl + "?q=" + encodeURIComponent(query);
        fetch(url)
            .then(response => {
                if (!response.ok) throw new Error("HTTP " + response.status);
                return response.json();
            })
            .then(data => {
                patients = data.patients || [];
                activeIndex = -1;
                renderResults(patients);
            })
            .catch(error => alert("Patient search failed (" + error.message + ")"));
    }

    function renderResults(patients) {
        if (!patients.length) {
            results.innerHTML = '<div class="list-group-item text-muted">Patient does not exist in the database.</div>';
            return;
        }
        results.innerHTML = `
            <div class="table-responsive border rounded bg-white">
                <table class="table table-sm table-hover align-middle mb-0">
                    <thead class="table-light">
                        <tr>
                            <th>Patient ID</th>
                            <th>Name</th>
                            <th>Phone</th>
                            <th>Address</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${patients.map((patient, index) => `
                            <tr class="select-patient" data-index="${index}" style="cursor:pointer">
                                <td>${escapeHtml(patient.patient_id || "-")}</td>
                                <td>${escapeHtml(patient.name || "-")}</td>
                                <td>${escapeHtml(patient.phone || "-")}</td>
                                <td>${escapeHtml(patient.address || "-")}</td>
                            </tr>
                        `).join("")}
                    </tbody>
                </table>
            </div>`;
        results.querySelectorAll(".select-patient").forEach(button => {
            button.addEventListener("click", () => {
                selectPatient(patients[Number(button.dataset.index)]);
            });
        });
    }

    function highlightPatient() {
        results.querySelectorAll(".select-patient").forEach((row, index) => {
            row.classList.toggle("table-primary", index === activeIndex);
        });
        const activeRow = results.querySelectorAll(".select-patient")[activeIndex];
        if (activeRow) activeRow.scrollIntoView({ block: "nearest" });
    }

    function selectPatient(patient) {
        fillPatient(patient);
        results.innerHTML = "";
        search.value = "";
        patients = [];
        activeIndex = -1;
    }

    function fillPatient(patient) {
        $("#patient_id").val(patient.patient_id || "");
        $("#pat_title").val(patient.title || "Mr.");
        $("#pat_name").val(patient.name || "");
        $("#pat_age_y").val(patient.age_y || 0);
        $("#pat_age_m").val(patient.age_m || 0);
        $("#pat_age_d").val(patient.age_d || 0);
        $("#pat_gender").val(patient.gender || "Male");
        $("#pat_phone").val(patient.phone || "");
        $("#pat_address").val(patient.address || "");
        $("#doc_lookup").focus();
    }

    function escapeHtml(value) {
        return String(value).replace(/[&<>'"]/g, char => ({
            "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
        }[char]));
    }
})();
