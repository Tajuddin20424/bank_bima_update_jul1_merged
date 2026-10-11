$(document).ready(function () {
    function money(value) {
        return Number(value || 0).toFixed(2);
    }

    function today() {
        return new Date().toISOString().slice(0, 10);
    }

    function renderEmpty(message) {
        $("#refReportBody").html(`<tr><td colspan="10" class="text-center text-muted py-4">${message}</td></tr>`);
        $("#totalTestTk, #totalDiscount, #totalReferral").text("0.00");
    }

    function loadProviders() {
        let reportType = $("#refReportType").val();
        $.get("/diagnosis/referral/report/providers/", { report_type: reportType }, function (res) {
            let label = reportType === "sr" ? "SR" : "Doctor";
            let options = `<option value="">-- Select ${label} --</option>`;
            (res.providers || []).forEach(function (provider) {
                options += `<option value="${provider.code}">${provider.code} - ${provider.name}</option>`;
            });
            $("#refProvider").html(options);
            renderEmpty("Filter report");
        }).fail(function () {
            renderEmpty("Failed to load provider list");
        });
    }

    function loadReport() {
        let params = {
            report_type: $("#refReportType").val(),
            provider_id: $("#refProvider").val(),
            start_date: $("#refStartDate").val(),
            end_date: $("#refEndDate").val()
        };
        if (!params.provider_id || !params.start_date || !params.end_date) {
            renderEmpty("Select provider and date range");
            return;
        }
        $.get("/diagnosis/referral/report/data/", params, function (res) {
            let rows = res.rows || [];
            if (!rows.length) { renderEmpty("No referral transaction found"); return; }
            let html = "";
            rows.forEach(function (row, index) {
                html += `<tr>
                    <td>${index + 1}</td>
                    <td>${row.tran_id || "-"}</td>
                    <td>${row.tran_date || "-"}</td>
                    <td>${row.group_name || "-"}</td>
                    <td>${row.tran_head_name || "-"}</td>
                    <td class="text-end">${money(row.test_tk)}</td>
                    <td class="text-end">${money(row.discount)}</td>
                    <td>${row.ref_type || "-"}</td>
                    <td class="text-end">${money(row.ref_rate)}</td>
                    <td class="text-end">${money(row.referral_amount)}</td>
                </tr>`;
            });
            $("#refReportBody").html(html);
            $("#totalTestTk").text(money(res.total_test_tk));
            $("#totalDiscount").text(money(res.total_discount));
            $("#totalReferral").text(money(res.total_referral));
        }).fail(function (xhr) {
            let res = xhr.responseJSON || {};
            renderEmpty(res.message || "Failed to load referral report");
        });
    }

    function downloadReportPdf() {
        let params = {
            report_type: $("#refReportType").val(),
            provider_id: $("#refProvider").val(),
            start_date: $("#refStartDate").val(),
            end_date: $("#refEndDate").val()
        };
        if (!params.provider_id || !params.start_date || !params.end_date) {
            renderEmpty("Select provider and date range before downloading PDF");
            return;
        }
        let query = $.param(params);
        window.location.href = `/diagnosis/referral/report/pdf/?${query}`;
    }

    $("#refStartDate").val(today());
    $("#refEndDate").val(today());
    $("#refReportType").on("change", loadProviders);
    $("#refFilterBtn").on("click", loadReport);
    $("#refPdfBtn").on("click", downloadReportPdf);
    loadProviders();
});
