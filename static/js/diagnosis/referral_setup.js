$(document).ready(function () {
    function csrfToken() {
        return $("#global_csrf").val() || $("input[name='csrfmiddlewaretoken']").val();
    }

    function selectedDoctorId() {
        return $("#referralDoctor").val();
    }

    function selectedGroupId() {
        return $("#referralGroup").val();
    }

    const referralTestsUrl = $("#referralTestsUrl").val() || "/diagnosis/referral/tests/";
    const referralSavedGroupsUrl = $("#referralSavedGroupsUrl").val() || "/diagnosis/referral/saved-groups/";
    const referralSaveUrl = $("#referralSaveUrl").val() || "/diagnosis/referral/save/";
    const referralCopyUrl = $("#referralCopyUrl").val() || "/diagnosis/referral/copy/";
    const referralSuccessMessage = $("#referralSuccessMessage").val() || "Referral setup updated successfully";
    const referralCopySuccessMessage = $("#referralCopySuccessMessage").val() || "Referral setup copied successfully";
    const referralProviderLabel = $("#referralProviderLabel").val() || "Doctor";
    const referralProviderMetaLabel = $("#referralProviderMetaLabel").val() || "Specialization";
    const referralProviderExtraLabel = $("#referralProviderExtraLabel").val() || "Chamber";

    function notify(message, type) {
        let toastType = type || "info";
        let toastClass = toastType === "success" ? "bg-success" : (toastType === "error" ? "bg-danger" : (toastType === "warning" ? "bg-warning text-dark" : "bg-primary"));
        let $toastWrap = $("#referralToastWrap");
        if (!$toastWrap.length) {
            $("body").append('<div id="referralToastWrap" style="position:fixed;top:90px;right:24px;z-index:99999;min-width:280px;"></div>');
            $toastWrap = $("#referralToastWrap");
        }
        let $toast = $(`<div class="toast align-items-center text-white ${toastClass} border-0 show shadow mb-2" role="alert"><div class="d-flex"><div class="toast-body fw-semibold">${message}</div><button type="button" class="btn-close btn-close-white me-2 m-auto"></button></div></div>`);
        $toastWrap.append($toast);
        $toast.find(".btn-close").on("click", function () { $toast.remove(); });
        setTimeout(function () { $toast.fadeOut(250, function () { $(this).remove(); }); }, 4500);
    }

    let savedToastMessage = sessionStorage.getItem("referralSetupToast");
    if (savedToastMessage) {
        sessionStorage.removeItem("referralSetupToast");
        notify(savedToastMessage, "success");
    }

    let pendingConfirmAction = null;
    let referralGroupsLoaded = false;

    function openConfirmModal(title, message, action) {
        pendingConfirmAction = action;
        $("#referralConfirmTitle").text(title);
        $("#referralConfirmMessage").text(message);
        $("#referralConfirmModal").modal("show");
    }

    $("#referralConfirmYesBtn").on("click", function () {
        $("#referralConfirmModal").modal("hide");
        if (typeof pendingConfirmAction === "function") { pendingConfirmAction(); }
        pendingConfirmAction = null;
    });

    $(".referral-doctor-select").select2({ width: "100%" });

    function loadGroups() {
        $.get("/diagnosis/referral/groups/", function (res) {
            let options = '<option value="">-- Select Group --</option>';
            (res.groups || []).forEach(function (group) {
                options += `<option value="${group.id}">${group.name}</option>`;
            });
            $("#referralGroup").html(options);
            referralGroupsLoaded = true;
            $("#referralGroup").trigger("referral:groups-loaded");
        }).fail(function () {
            notify("Failed to load diagnosis groups", "error");
        });
    }

    function renderEmpty(message) {
        $("#referralTestBody").html(`<tr><td colspan="5" class="text-center text-muted py-4">${message}</td></tr>`);
    }

    function clearReferralForm() {
        $("#referralDoctor").val("").trigger("change.select2");
        $("#copySourceDoctor").val("").trigger("change.select2");
        $("#referralGroup").val("");
        $("#globalRateType").val("tk");
        $("#globalRate").val("");
        $("#selectAllTests").prop("checked", false);
        $("#selectedDoctorName").text(`No ${referralProviderLabel} selected`);
        $("#selectedDoctorMeta").text("-");
        renderEmpty("Select doctor and group");
    }

    function refreshReferralPage(message) {
        clearReferralForm();
        sessionStorage.setItem("referralSetupToast", message);
        window.location.href = window.location.pathname;
    }

    function loadTests() {
        let docId = selectedDoctorId();
        let groupId = selectedGroupId();
        if (!docId || !groupId) { renderEmpty("Select doctor and group"); return; }

        $.get(referralTestsUrl, { doc_id: docId, group_id: groupId }, function (res) {
            let tests = res.tests || [];
            if (!tests.length) { renderEmpty("No test found under this group"); return; }
            let rows = "";
            tests.forEach(function (test) {
                let checked = Number(test.selected || 0) === 1 ? "checked" : "";
                let refType = test.ref_type || "tk";
                rows += ` 
                    <tr data-head-id="${test.id}"> 
                        <td class="text-center"><input type="checkbox" class="form-check-input test-check" ${checked}></td>
                        <td>${test.name || "-"}</td>
                        <td class="text-end">${Number(test.mrp || 0).toFixed(2)}</td>
                        <td>
                            <select class="form-select form-select-sm row-ref-type">
                                <option value="tk" ${refType === "tk" ? "selected" : ""}>Tk</option>
                                <option value="percent" ${refType === "percent" ? "selected" : ""}>%</option>
                            </select>
                        </td>
                        <td><input type="number" step="0.01" min="0" class="form-control form-control-sm row-ref-rate" value="${Number(test.ref_rate || 0)}"></td>
                    </tr>`;
            });
            $("#referralTestBody").html(rows);
            $("#selectAllTests").prop("checked", tests.every(function (test) { return Number(test.selected || 0) === 1; }));
            let firstSaved = tests.find(function (test) { return Number(test.selected || 0) === 1; });
            if (firstSaved) {
                $("#globalRateType").val(firstSaved.ref_type || "tk");
                $("#globalRate").val(Number(firstSaved.ref_rate || 0));
            }
        }).fail(function (xhr) {
            let res = xhr.responseJSON || {};
            notify(res.message || "Failed to load tests", "error");
        });
    }

    function loadSavedSetupForDoctor(docId) {
        if (!docId) { $("#referralGroup").val(""); renderEmpty(`Select ${referralProviderLabel} and group`); return; }
        $.get(referralSavedGroupsUrl, { doc_id: docId }, function (res) {
            let groups = res.groups || [];
            if (!groups.length) { $("#referralGroup").val(""); renderEmpty(`No saved referral setup found for this ${referralProviderLabel}`); return; }
            $("#referralGroup").val(groups[0].group_id);
            loadTests();
        }).fail(function (xhr) {
            let res = xhr.responseJSON || {};
            notify(res.message || "Failed to load saved referral setup", "error");
        });
    }

    $("#referralDoctor").on("change", function () {
        let option = $(this).find("option:selected");
        let name = option.data("name") || `No ${referralProviderLabel} selected`;
        let specialization = option.data("specialization") || "-";
        let chamber = option.data("chamber") || "-";
        $("#selectedDoctorName").text(name);
        $("#selectedDoctorMeta").text(`${referralProviderMetaLabel}: ${specialization} | ${referralProviderExtraLabel}: ${chamber}`);
        if (referralGroupsLoaded) { loadSavedSetupForDoctor(selectedDoctorId()); return; }
        $("#referralGroup").one("referral:groups-loaded", function () { loadSavedSetupForDoctor(selectedDoctorId()); });
    });

    $("#referralGroup").on("change", loadTests);

    $("#selectAllTests").on("change", function () {
        $(".test-check").prop("checked", $(this).is(":checked"));
    });

    $("#applyRateBtn").on("click", function () {
        let rateType = $("#globalRateType").val();
        let rate = $("#globalRate").val() || 0;
        $(".test-check:checked").each(function () {
            let row = $(this).closest("tr");
            row.find(".row-ref-type").val(rateType);
            row.find(".row-ref-rate").val(rate);
        });
    });

    function submitReferralSetup(docId, groupId, rows) {
        $.ajax({
            url: referralSaveUrl,
            method: "POST",
            headers: { "X-CSRFToken": csrfToken() },
            contentType: "application/json",
            data: JSON.stringify({ doc_id: docId, group_id: groupId, rows: rows }),
            success: function () { refreshReferralPage(referralSuccessMessage); },
            error: function (xhr) {
                let res = xhr.responseJSON || {};
                notify(res.message || "Failed to save referral setup", "error");
            }
        });
    }

    function submitReferralCopy(sourceDocId, targetDocId) {
        $.ajax({
            url: referralCopyUrl,
            method: "POST",
            headers: { "X-CSRFToken": csrfToken() },
            contentType: "application/json",
            data: JSON.stringify({ source_doc_id: sourceDocId, target_doc_id: targetDocId }),
            success: function () { refreshReferralPage(referralCopySuccessMessage); },
            error: function (xhr) {
                let res = xhr.responseJSON || {};
                notify(res.message || "Failed to copy referral setup", "error");
            }
        });
    }

    $("#saveReferralBtn").on("click", function () {
        let docId = selectedDoctorId();
        let groupId = selectedGroupId();
        if (!docId) { notify(`Please select ${referralProviderLabel}`, "warning"); return; }
        if (!groupId) { notify("Please select group", "warning"); return; }

        let rows = [];
        $("#referralTestBody tr[data-head-id]").each(function () {
            let row = $(this);
            rows.push({
                tran_head_id: row.data("head-id"),
                ref_type: row.find(".row-ref-type").val(),
                ref_rate: row.find(".row-ref-rate").val() || 0,
                selected: row.find(".test-check").is(":checked")
            });
        });

        openConfirmModal("Confirm Referral Update", `Are you sure you want to update this ${referralProviderLabel} referral setup?`, function () {
            submitReferralSetup(docId, groupId, rows);
        });
    });

    $("#copyReferralBtn").on("click", function () {
        let sourceDocId = $("#copySourceDoctor").val();
        let targetDocId = selectedDoctorId();
        if (!targetDocId) { notify(`Please select target ${referralProviderLabel} first`, "warning"); return; }
        if (!sourceDocId) { notify(`Please select source ${referralProviderLabel}`, "warning"); return; }
        if (sourceDocId === targetDocId) { notify(`Source and target ${referralProviderLabel} cannot be same`, "warning"); return; }

        openConfirmModal("Confirm Referral Copy", `Are you sure you want to copy referral setup to selected ${referralProviderLabel}?`, function () {
            submitReferralCopy(sourceDocId, targetDocId);
        });
    });

    loadGroups();
});
