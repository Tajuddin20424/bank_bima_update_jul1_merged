let labParameterPage = 1;
let labParameterLoading = false;
let labParameterHasMore = true;
let labParameterMode = "save";

function labParameterCsrfToken() {
    return $("#global_csrf").val() || $("input[name='csrfmiddlewaretoken']").val() || window.csrftoken;
}

function labParameterEscape(value) {
    return $("<div>").text(value || "").html();
}

function notifyLabParameter(message, type) {
    let toastType = type || "info";
    let toastClass = toastType === "success" ? "bg-success" : (toastType === "error" ? "bg-danger" : (toastType === "warning" ? "bg-warning text-dark" : "bg-primary"));
    let $wrap = $("#labParameterToastWrap");
    if (!$wrap.length) {
        $("body").append('<div id="labParameterToastWrap" style="position:fixed;top:90px;right:24px;z-index:99999;min-width:280px;"></div>');
        $wrap = $("#labParameterToastWrap");
    }
    let $toast = $(`<div class="toast align-items-center text-white ${toastClass} border-0 show shadow mb-2" role="alert"><div class="d-flex"><div class="toast-body fw-semibold">${labParameterEscape(message)}</div><button type="button" class="btn-close btn-close-white me-2 m-auto"></button></div></div>`);
    $wrap.append($toast);
    $toast.find(".btn-close").on("click", function () { $toast.remove(); });
    setTimeout(function () { $toast.fadeOut(250, function () { $(this).remove(); }); }, 3500);
}

function resetLabParameterForm() {
    $("#lab_parameter_id").val("");
    $("#serial").val("0");
    $("#title").val("");
    $("#title_code").val("");
    $("#investigation").val("");
    $("#investigation_code").val("");
    $("#unit").val("");
    $("#reff_range").val("");
    $("#head_id").val("");
    labParameterMode = "save";
    $("#saveLabParameterBtn").text("Save").removeClass("btn-primary").addClass("btn-success");
}

function resetLabParameterList() {
    labParameterPage = 1;
    labParameterHasMore = true;
    $("#labParameterTableBody").html("");
    loadLabParameters();
}

function loadLabParameterHeads(targetSelector, groupId, categoryId, selectedId, allLabel) {
    let $target = $(targetSelector);
    let defaultLabel = allLabel || "-- Optional --";
    $target.html(`<option value="">${defaultLabel}</option>`);
    if (!groupId) { return $.Deferred().resolve().promise(); }
    return $.ajax({
        url: "/diagnosis/lab-report/heads/",
        method: "GET",
        data: { group_id: groupId, category_id: categoryId || "" },
        success: function (response) {
            let options = `<option value="">${defaultLabel}</option>`;
            (response.heads || []).forEach(function (head) {
                options += `<option value="${head.id}">${labParameterEscape(head.name)}</option>`;
            });
            $target.html(options);
            if (selectedId) { $target.val(String(selectedId)); }
        },
        error: function () {
            notifyLabParameter("Failed to load transaction heads", "error");
        }
    });
}

function loadLabParameterCategories(targetSelector, groupId, selectedId, allLabel) {
    let $target = $(targetSelector);
    let defaultLabel = allLabel || "-- Select Category --";
    let emptyLabel = groupId ? defaultLabel : (targetSelector.indexOf("filter") >= 0 ? defaultLabel : "-- Select Group First --");
    $target.html(`<option value="">${emptyLabel}</option>`);
    if (!groupId) { return $.Deferred().resolve().promise(); }
    return $.ajax({
        url: "/diagnosis/lab-report/categories/",
        method: "GET",
        data: { group_id: groupId },
        success: function (response) {
            let options = `<option value="">${defaultLabel}</option>`;
            (response.categories || []).forEach(function (category) {
                options += `<option value="${category.id}">${labParameterEscape(category.name)}</option>`;
            });
            $target.html(options);
            if (selectedId) { $target.val(String(selectedId)); }
        },
        error: function () {
            notifyLabParameter("Failed to load lab categories", "error");
        }
    });
}

function loadLabParameters() {
    if (labParameterLoading || !labParameterHasMore) { return; }
    labParameterLoading = true;
    $.ajax({
        url: "/diagnosis/lab-report/parameters/load/",
        method: "GET",
        data: {
            page: labParameterPage,
            limit: 20,
            group_id: $("#filter_group_id").val(),
            category_id: $("#filter_category_id").val(),
            head_id: $("#filter_head_id").val(),
            search: $("#search_lab_parameter").val()
        },
        success: function (response) {
            let rows = response.lab_parameters || [];
            if (!rows.length && labParameterPage === 1) {
                $("#labParameterTableBody").html('<tr><td colspan="12" class="text-center text-muted py-4">No lab parameter found</td></tr>');
                labParameterHasMore = false;
                labParameterLoading = false;
                return;
            }
            if (!rows.length) {
                labParameterHasMore = false;
                labParameterLoading = false;
                return;
            }
            let html = "";
            rows.forEach(function (row, index) {
                html += ` 
                    <tr>
                        <td>${((labParameterPage - 1) * 20) + index + 1}</td>
                        <td>${labParameterEscape(row.group_name)}</td>
                        <td>${labParameterEscape(row.category_name)}</td>
                        <td>${labParameterEscape(row.tran_head_name || "-")}</td>
                        <td>${labParameterEscape(row.serial)}</td>
                        <td>${labParameterEscape(row.title)}</td>
                        <td>${labParameterEscape(row.title_code || "-")}</td>
                        <td>${labParameterEscape(row.investigation)}</td>
                        <td>${labParameterEscape(row.investigation_code || "-")}</td>
                        <td>${labParameterEscape(row.unit || "-")}</td>
                        <td>${labParameterEscape(row.reff_range || "-")}</td>
                        <td>
                            <button type="button" class="btn btn-sm btn-warning labParameterEditBtn"
                                data-id="${row.id}"
                                data-group_id="${row.group_id}"
                                data-category_id="${row.category_id}"
                                data-head_id="${row.head_id || ""}"
                                data-serial="${labParameterEscape(row.serial)}"
                                data-title="${labParameterEscape(row.title)}"
                                data-title_code="${labParameterEscape(row.title_code || "")}"
                                data-investigation="${labParameterEscape(row.investigation)}"
                                data-investigation_code="${labParameterEscape(row.investigation_code || "")}"
                                data-unit="${labParameterEscape(row.unit || "")}"
                                data-reff_range="${labParameterEscape(row.reff_range || "")}">Edit</button>
                            <button type="button" class="btn btn-sm btn-danger labParameterDeleteBtn" data-id="${row.id}">Delete</button>
                        </td>
                    </tr>
                `;
            });
            if (labParameterPage === 1) { $("#labParameterTableBody").html(html); } else { $("#labParameterTableBody").append(html); }
            labParameterPage++;
            labParameterLoading = false;
        },
        error: function (xhr) {
            labParameterLoading = false;
            let response = xhr.responseJSON || {};
            notifyLabParameter(response.message || "Failed to load lab parameters", "error");
        }
    });
}

$(document).ready(function () {
    loadLabParameters();

    $("#group_id").on("change", function () {
        loadLabParameterCategories("#category_id", $("#group_id").val(), null, "-- Select Category --");
        loadLabParameterHeads("#head_id", $("#group_id").val(), "", null, "-- Optional --");
    });

    $("#category_id").on("change", function () {
        loadLabParameterHeads("#head_id", $("#group_id").val(), $("#category_id").val(), null, "-- Optional --");
    });

    $("#filter_group_id").on("change", function () {
        loadLabParameterCategories("#filter_category_id", $("#filter_group_id").val(), null, "All Category").always(function () {
            loadLabParameterHeads("#filter_head_id", $("#filter_group_id").val(), $("#filter_category_id").val(), null, "All Head");
            resetLabParameterList();
        });
    });

    $("#filter_category_id").on("change", function () {
        loadLabParameterHeads("#filter_head_id", $("#filter_group_id").val(), $("#filter_category_id").val(), null, "All Head");
        resetLabParameterList();
    });

    $("#filter_head_id").on("change", resetLabParameterList);

    $("#search_lab_parameter").on("input", function () {
        resetLabParameterList();
    });

    $("#resetLabParameterBtn").on("click", function () {
        resetLabParameterForm();
    });

    $("#labParameterForm").on("submit", function (event) {
        event.preventDefault();
        let url = labParameterMode === "update" ? "/diagnosis/lab-report/parameters/update/" : "/diagnosis/lab-report/parameters/save/";
        $.ajax({
            url: url,
            method: "POST",
            headers: { "X-CSRFToken": labParameterCsrfToken() },
            data: $(this).serialize(),
            success: function (response) {
                notifyLabParameter(response.message || "Saved successfully", "success");
                resetLabParameterForm();
                resetLabParameterList();
            },
            error: function (xhr) {
                let response = xhr.responseJSON || {};
                notifyLabParameter(response.message || "Failed to save lab parameter", "error");
            }
        });
    });

    $(document).on("click", ".labParameterEditBtn", function () {
        let data = $(this).data();
        $("#lab_parameter_id").val(data.id);
        $("#group_id").val(data.group_id);
        $("#serial").val(data.serial);
        $("#title").val(data.title);
        $("#title_code").val(data.title_code);
        $("#investigation").val(data.investigation);
        $("#investigation_code").val(data.investigation_code);
        $("#unit").val(data.unit);
        $("#reff_range").val(data.reff_range);
        loadLabParameterCategories("#category_id", data.group_id, data.category_id, "-- Select Category --").always(function () {
            loadLabParameterHeads("#head_id", data.group_id, data.category_id, data.head_id, "-- Optional --");
        });
        labParameterMode = "update";
        $("#saveLabParameterBtn").text("Update").removeClass("btn-success").addClass("btn-primary");
        window.scrollTo({ top: 0, behavior: "smooth" });
    });

    $(document).on("click", ".labParameterDeleteBtn", function () {
        if (!confirm("Are you sure you want to delete this lab parameter?")) { return; }
        $.ajax({
            url: "/diagnosis/lab-report/parameters/delete/",
            method: "POST",
            headers: { "X-CSRFToken": labParameterCsrfToken() },
            data: { id: $(this).data("id") },
            success: function (response) {
                notifyLabParameter(response.message || "Deleted successfully", "success");
                resetLabParameterList();
            },
            error: function (xhr) {
                let response = xhr.responseJSON || {};
                notifyLabParameter(response.message || "Failed to delete lab parameter", "error");
            }
        });
    });

    $(window).on("scroll", function () {
        if ($(window).scrollTop() + $(window).height() >= $(document).height() - 150) {
            loadLabParameters();
        }
    });
});
