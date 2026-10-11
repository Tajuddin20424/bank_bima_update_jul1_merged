let biochemistryRows = [];
let biochemistryTests = [];
let selectedBiochemistryTestId = "";
let selectedBiochemistryTestIds = [];
let biochemistryRowsByTest = {};
let activeResultTestId = "";
let selectedBiochemistryTestNames = {};
let invoiceSearchTimer = null;
let invoiceActiveIndex = -1;
let biochemistryEditMode = false;

function bioCsrfToken() {
    return $("#global_csrf").val() || $("input[name='csrfmiddlewaretoken']").val() || window.csrftoken;
}

function bioEscape(value) {
    return $("<div>").text(value || "").html();
}

function bioResetForm() {
    $("#invoiceSearch").val("");
    $("#invoiceId").val("");
    $("#patientName,#doctorName,#labNo,#reportDate,#patientSex,#patientAgeY,#patientAgeM,#patientAgeD,#patientPhone,#patientAddress").val("");
    $("#patientNameText,#doctorNameText,#patientSexText,#patientPhoneText,#patientAddressText").text("-");
    $("#receiptNo,#patientAge").text("-");
    $("#selectedTestName").text("Select test");
    $("#invoiceTestBody").html('<tr><td colspan="3" class="text-center text-muted">Search transaction</td></tr>');
    $("#resultEntryBody").html('<tr><td colspan="5" class="text-center text-muted">No result rows loaded</td></tr>');
    biochemistryRows = [];
    biochemistryTests = [];
    selectedBiochemistryTestId = "";
    selectedBiochemistryTestIds = [];
    biochemistryRowsByTest = {};
    activeResultTestId = "";
    selectedBiochemistryTestNames = {};
}

function hideInvoiceDropdown() {
    $("#invoiceSearchDropdown").addClass("d-none").empty();
}

function renderInvoiceDropdown(rows) {
    let html = "";
    (rows || []).forEach(function (row) {
        let receipt = row.invoice_ref || row.tran_id || "";
        html += `<div class="bio-invoice-option" data-invoice-id="${bioEscape(row.id)}" data-receipt="${bioEscape(receipt)}">
                    <b>${bioEscape(receipt)}</b>
                    <span class="bio-invoice-meta">${bioEscape(row.patient_name || "-")} | ${bioEscape(row.tran_id || "")}</span>
                </div>`;
    });
    $("#invoiceSearchDropdown").html(html).toggleClass("d-none", !html);
    invoiceActiveIndex = rows && rows.length ? 0 : -1;
    $("#invoiceSearchDropdown .bio-invoice-option").first().addClass("active");
}

function searchInvoiceSuggestions() {
    let term = ($("#invoiceSearch").val() || "").trim();
    if (!term) { hideInvoiceDropdown(); return; }
    $.get("/diagnosis/lab-report/biochemistry/invoice-search/", { q: term }, function (response) {
        renderInvoiceDropdown(response.results || []);
    });
}

function saveActiveResultInputs() {
    if (!biochemistryRowsByTest.template) { return; }
    $("#resultEntryBody tr[data-index]").each(function () {
        let index = Number($(this).data("index"));
        if (biochemistryRowsByTest.template[index]) {
            biochemistryRowsByTest.template[index].result = $(this).find(".bio-result-input").val();
        }
    });
}

function renderResultButtons() {
    let names = selectedBiochemistryTestIds.map(function (testId) { return selectedBiochemistryTestNames[testId] || testId; });
    $("#selectedTestName").html(names.length ? `<span class="badge bg-primary">${bioEscape(names.join(", "))}</span>` : '<span class="badge bg-light text-dark border">Select test</span>');
}

function renderSelectedResultRows() {
    biochemistryRows = biochemistryRowsByTest.template || [];
    let rowHtml = "";
    biochemistryRows.forEach(function (row, index) {
        rowHtml += ` 
            <tr data-index="${index}">
                <td>${bioEscape(row.title)}</td>
                <td>${bioEscape(row.investigation)}</td>
                <td><input type="text" class="form-control form-control-sm bio-result-input" value="${bioEscape(row.result || "")}"></td>
                <td>${bioEscape(row.unit || "")}</td>
                <td>${bioEscape(row.reff_range || "")}</td>
            </tr>`;
    });
    $("#resultEntryBody").html(rowHtml || '<tr><td colspan="5" class="text-center text-muted">Select investigation first</td></tr>');
    renderResultButtons();
}

function renderInvoiceData(response, renderRows) {
    let invoice = response.invoice || {};
    $("#invoiceId").val(invoice.id || "");
    $("#patientName").val(invoice.patient_name || "");
    $("#doctorName").val(invoice.doctor_name || "");
    $("#patientPhone").val(invoice.phone || "");
    $("#patientAddress").val(invoice.address || "");
    $("#patientNameText").text(invoice.patient_name || "-");
    $("#doctorNameText").text(invoice.doctor_name || "-");
    $("#patientPhoneText").text(invoice.phone || "-");
    $("#patientAddressText").text(invoice.address || "-");
    $("#labNo").val(invoice.id || "");
    $("#reportDate").val((invoice.tran_date || "").slice(0, 10));
    $("#receiptNo").text(invoice.invoice_ref || invoice.tran_id || "-");
    $("#patientAge").text(`${invoice.age_y || 0}Y ${invoice.age_m || 0}M ${invoice.age_d || 0}D`);
    $("#patientAgeY").val(invoice.age_y || 0);
    $("#patientAgeM").val(invoice.age_m || 0);
    $("#patientAgeD").val(invoice.age_d || 0);
    $("#patientSex").val(invoice.gender || "");
    $("#patientSexText").text(invoice.gender || "-");

    let testHtml = "";
    biochemistryTests = response.tests || [];
    if (response.selected_test_ids && response.selected_test_ids.length) {
        selectedBiochemistryTestIds = response.selected_test_ids.map(String);
        (response.selected_test_names || []).forEach(function (name, index) { selectedBiochemistryTestNames[selectedBiochemistryTestIds[index]] = name; });
        if (!selectedBiochemistryTestId && selectedBiochemistryTestIds.length) { selectedBiochemistryTestId = selectedBiochemistryTestIds[0]; }
    }
    biochemistryTests.forEach(function (test) {
        selectedBiochemistryTestNames[String(test.id)] = selectedBiochemistryTestNames[String(test.id)] || test.name;
        let checked = selectedBiochemistryTestIds.includes(String(test.id)) ? "checked" : "";
        let activeClass = checked ? " active" : "";
        testHtml += `<tr class="bio-test-row${activeClass}" data-test-id="${bioEscape(test.id)}" data-test-name="${bioEscape(test.name)}"><td>${bioEscape(test.id)}</td><td>${bioEscape(test.name)}</td><td class="text-center"><input type="checkbox" class="bio-test-select" ${checked}></td></tr>`;
    });
    let emptyMessage = response.already_added ? "Already added. Please edit from report list." : "No matching Biochemistry test found";
    $("#invoiceTestBody").html(testHtml || `<tr><td colspan="3" class="text-center text-muted">${emptyMessage}</td></tr>`);
    let selectedTest = biochemistryTests.find(function (test) { return String(test.id) === String(selectedBiochemistryTestId); });
    renderResultButtons();

    if (renderRows && selectedBiochemistryTestId) {
        let selectedTestName = selectedTest ? selectedTest.name : "";
        biochemistryRowsByTest.template = (response.rows || []).map(function (row) {
            row.head_id = "";
            row.selected_test_name = selectedTestName;
            return row;
        });
    }
    renderSelectedResultRows();
}

function loadInvoiceBySearch(invoiceId, testId, editMode) {
    let data = invoiceId ? { invoice_id: invoiceId } : { invoice: $("#invoiceSearch").val() };
    if (testId) { data.test_id = testId; }
    if (editMode || biochemistryEditMode) { data.edit = "1"; }
    $.get("/diagnosis/lab-report/biochemistry/load-invoice/", data, function (response) {
        renderInvoiceData(response, !!testId || biochemistryEditMode);
    }).fail(function (xhr) {
        let response = xhr.responseJSON || {};
        alert(response.message || "Failed to load transaction");
    });
}

function collectResultRows() {
    saveActiveResultInputs();
    let allRows = biochemistryRowsByTest.template || [];
    return allRows.map(function (row) {
        return {
            group_id: row.group_id, category_id: row.category_id, head_id: row.head_id || "", serial: row.serial || 0,
            title: row.title || "", title_code: row.title_code || "", investigation: row.investigation || "", investigation_code: row.investigation_code || "",
            unit: row.unit || "", reff_range: row.reff_range || "", result: row.result || "", selected_test_name: row.selected_test_name || ""
        };
    });
}

function openPreview(url) {
    $("#previewFrame").html('<div class="p-4 text-center text-muted">Loading preview...</div>');
    $("#biochemistryPreviewModal").modal("show");
    $.get(url, function (response) {
        $("#previewFrame").html(response.html || '<div class="p-4 text-center text-muted">No preview data found</div>');
        $("#downloadPreviewBtn").attr("href", response.download_url || url.replace("/preview/", "/pdf/") + "?download=1");
    }).fail(function (xhr) {
        let response = xhr.responseJSON || {};
        $("#previewFrame").html(`<div class="p-4 text-center text-danger">${bioEscape(response.message || "Preview failed")}</div>`);
    });
}

function bioLoadCategoryFilter() {
    let groupId = $("#resultFilterGroup").val();
    let $category = $("#resultFilterCategory");
    if (!$category.length) { return; }
    $category.html('<option value="">All Category</option>');
    if (!groupId) { return; }
    $.get("/diagnosis/lab-report/categories/", { group_id: groupId }, function (response) {
        let options = '<option value="">All Category</option>';
        (response.categories || []).forEach(function (category) {
            options += `<option value="${category.id}">${bioEscape(category.name)}</option>`;
        });
        $category.html(options);
    });
}

function loadResultList() {
    if (!$("#resultListBody").length) { return; }
    $.get("/diagnosis/lab-report/biochemistry/list/", {
        search: $("#resultListSearch").val(),
        group_id: $("#resultFilterGroup").val(),
        category_id: $("#resultFilterCategory").val()
    }, function (response) {
        let rows = response.results || [];
        let html = "";
        rows.forEach(function (row, index) {
            html += ` 
                <tr>
                    <td>${index + 1}</td>
                    <td>${bioEscape(row.tran_id)}</td>
                    <td>${bioEscape(row.invoice_ref || "-")}</td>
                    <td>${bioEscape(row.patient_name || "-")}</td>
                    <td>${bioEscape(row.total_rows)}</td>
                    <td>${bioEscape(row.updated_at || "-")}</td>
                    <td>
                        <button type="button" class="btn btn-sm btn-warning bio-edit-btn" data-invoice-id="${row.invoice_id}">Edit</button>
                        <button type="button" class="btn btn-sm btn-primary bio-preview-btn" data-invoice-id="${row.invoice_id}">Preview</button>
                    </td>
                </tr>`;
        });
        $("#resultListBody").html(html || '<tr><td colspan="7" class="text-center text-muted">No Biochemistry report found</td></tr>');
    });
}

function bioQueryParam(name) {
    return new URLSearchParams(window.location.search).get(name);
}

$(document).ready(function () {
    loadResultList();
    let queryInvoiceId = bioQueryParam("invoice_id");
    biochemistryEditMode = bioQueryParam("edit") === "1";
    if (queryInvoiceId && $("#invoiceId").length) { loadInvoiceBySearch(queryInvoiceId, "", biochemistryEditMode); }

    $("#loadInvoiceBtn").on("click", function () { selectedBiochemistryTestId = ""; loadInvoiceBySearch(); });
    $("#invoiceSearch").on("keydown", function (event) {
        let $options = $("#invoiceSearchDropdown .bio-invoice-option");
        if ((!$options.length || $("#invoiceSearchDropdown").hasClass("d-none")) && event.key === "Enter") { event.preventDefault(); selectedBiochemistryTestId = ""; loadInvoiceBySearch(); return; }
        if (!$options.length || $("#invoiceSearchDropdown").hasClass("d-none")) { return; }
        if (event.key === "ArrowDown") {
            event.preventDefault();
            invoiceActiveIndex = Math.min(invoiceActiveIndex + 1, $options.length - 1);
        } else if (event.key === "ArrowUp") {
            event.preventDefault();
            invoiceActiveIndex = Math.max(invoiceActiveIndex - 1, 0);
        } else if (event.key === "Enter") {
            event.preventDefault();
            $options.eq(Math.max(invoiceActiveIndex, 0)).trigger("click");
            return;
        } else { return; }
        $options.removeClass("active").eq(invoiceActiveIndex).addClass("active");
    });
    $("#invoiceSearch").on("input", function () {
        clearTimeout(invoiceSearchTimer);
        invoiceSearchTimer = setTimeout(searchInvoiceSuggestions, 180);
    });
    $(document).on("click", ".bio-invoice-option", function () {
        $("#invoiceSearch").val($(this).data("receipt"));
        selectedBiochemistryTestId = "";
        hideInvoiceDropdown();
        loadInvoiceBySearch($(this).data("invoice-id"));
    });
    $(document).on("click", function (event) {
        if (!$(event.target).closest("#invoiceSearch,#invoiceSearchDropdown").length) { hideInvoiceDropdown(); }
    });
    $("#resetBiochemistryBtn").on("click", bioResetForm);
    $("#resultListSearch").on("input", loadResultList);
    $("#resultListFilterBtn,#resultFilterCategory").on("click change", loadResultList);
    $("#resultFilterGroup").on("change", function () { bioLoadCategoryFilter(); loadResultList(); });

    $("#saveBiochemistryBtn").on("click", function () {
        let invoiceId = $("#invoiceId").val();
        if (!invoiceId) { alert("Please search transaction first"); return; }
        if (!selectedBiochemistryTestIds.length) { alert("Please select investigation first"); return; }
        let rows = collectResultRows().filter(function (row) { return String(row.result || "").trim(); });
        if (!rows.length) { alert("No result rows found"); return; }
        $.ajax({
            url: "/diagnosis/lab-report/biochemistry/save/",
            method: "POST",
            headers: { "X-CSRFToken": bioCsrfToken() },
            contentType: "application/json",
            data: JSON.stringify({ invoice_id: invoiceId, selected_test_ids: selectedBiochemistryTestIds, selected_test_names: selectedBiochemistryTestIds.map(function (id) { return selectedBiochemistryTestNames[id] || id; }), rows: rows }),
            success: function (response) {
                loadResultList();
                openPreview(response.preview_url);
            },
            error: function (xhr) {
                let response = xhr.responseJSON || {};
                alert(response.message || "Failed to save result");
            }
        });
    });

    $(document).on("click", ".bio-test-row", function (event) {
        saveActiveResultInputs();
        selectedBiochemistryTestId = $(this).data("test-id");
        let testId = String(selectedBiochemistryTestId);
        let $checkbox = $(this).find(".bio-test-select");
        if (!$(event.target).is(".bio-test-select")) { $checkbox.prop("checked", !$checkbox.prop("checked")); }
        if ($checkbox.prop("checked")) {
            if (!selectedBiochemistryTestIds.includes(testId)) { selectedBiochemistryTestIds.push(testId); }
            selectedBiochemistryTestNames[testId] = $(this).data("test-name") || selectedBiochemistryTestNames[testId] || testId;
            if (!biochemistryRowsByTest.template) { loadInvoiceBySearch($("#invoiceId").val(), selectedBiochemistryTestId, biochemistryEditMode); } else { renderSelectedResultRows(); }
        } else {
            selectedBiochemistryTestIds = selectedBiochemistryTestIds.filter(function (id) { return id !== testId; });
            renderSelectedResultRows();
        }
    });

    $(document).on("click", ".bio-edit-btn", function () {
        window.location.href = `/diagnosis/lab-report/biochemistry/add/?invoice_id=${$(this).data("invoice-id")}&edit=1`;
    });

    $(document).on("click", ".bio-preview-btn", function () {
        openPreview(`/diagnosis/lab-report/biochemistry/preview/${$(this).data("invoice-id")}/`);
    });
});
