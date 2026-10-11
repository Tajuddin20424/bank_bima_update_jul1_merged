$(function () {
    let rows = [];
    let request = null;

    function today() {
        const d = new Date();
        return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
    }

    function money(value) {
        return (parseFloat(value) || 0).toFixed(2);
    }

    function loadHeads() {
        $.getJSON(window.APP_URLS.TRAN_MAIN_HEAD_URL, function (res) {
            const $select = $("#transactionmainheads").empty().append('<option value="">All Main Heads</option>');
            (res.transaction_main_heads_combo || []).forEach(function (item) {
                $select.append(`<option value="${item.id}">${item.name}</option>`);
            });
        });
    }

    function loadMethods(callback) {
        const mainHead = $("#transactionmainheads").val() || "";
        $.getJSON(window.APP_URLS.TRAN_WITH_METHOD_URL, { tran_main_head_id: mainHead }, function (res) {
            const $select = $("#transaction_with_method").empty().append('<option value="">All Methods</option>');
            (res.transaction_with_method_combo || []).forEach(function (item) {
                $select.append(`<option value="${item.method}">${item.method}</option>`);
            });
            if (callback) callback();
        });
    }

    function loadGroups(callback) {
        $.getJSON(window.APP_URLS.TRAN_WITH_URL, {
            tran_main_head_id: $("#transactionmainheads").val() || "",
            tran_with_method: $("#transaction_with_method").val() || ""
        }, function (res) {
            const $select = $("#transaction_with").empty().append('<option value="">All Groups</option>');
            (res.transaction_with_combo || []).forEach(function (item) {
                $select.append(`<option value="${item.id}">${item.name}</option>`);
            });
            if (callback) callback();
        });
    }

    function loadUsers() {
        $.getJSON(window.APP_URLS.TRAN_USERS_URL, {
            tran_main_head_id: $("#transactionmainheads").val() || "",
            tran_with_id: $("#transaction_with").val() || ""
        }, function (res) {
            const $select = $("#transaction_with_user").empty().append('<option value="">All Users</option>');
            (res.transaction_with_user_combo || []).forEach(function (item) {
                $select.append(`<option value="${item.id}">${item.user_name}</option>`);
            });
        });
    }

    function render() {
        const search = $("#supplierSearch").val().toLowerCase().trim();
        const visible = rows.filter(item => !search || JSON.stringify(item).toLowerCase().includes(search));
        const html = visible.length ? visible.map(function (item, index) {
            return `<tr>
                <td>${index + 1}</td><td>${item.tran_id || ""}</td><td>${item.invoice_ref || "-"}</td>
                <td>${item.tran_date || ""}</td><td>${item.supplier_name || "-"}</td><td>${item.user_name || item.tran_user || "-"}</td>
                <td class="text-end">${money(item.bill_total)}</td><td class="text-end">${money(item.discount)}</td>
                <td class="text-end">${money(item.net_total)}</td><td class="text-end">${money(item.advance)}</td>
                <td class="text-end">${money(item.due_collection)}</td><td class="text-end">${money(item.due_discount)}</td>
                <td class="text-end">${money(item.due)}</td>
                <td><button class="btn btn-sm btn-primary payment-btn" data-id="${item.id}">Payment</button></td>
            </tr>`;
        }).join("") : '<tr><td colspan="14" class="text-center py-3">No payment data found</td></tr>';
        $("#paymentListTableBody").html(html);
    }

    function loadTable() {
        if (request) request.abort();
        const params = {
            transactionmainheads: $("#transactionmainheads").val() || "",
            transaction_with_method: $("#transaction_with_method").val() || "",
            transaction_with: $("#transaction_with").val() || "",
            transaction_with_user: $("#transaction_with_user").val() || "",
            status: $("#status").val() || "",
            start_date: $("#start_date").val() || "",
            end_date: $("#end_date").val() || "",
            limit: $("#perPage").val() || 50,
            offset: 0
        };
        request = $.getJSON(window.APP_URLS.PARTY_PAYMENT_LIST_URL, params, function (res) {
            rows = res.results || [];
            render();
            $("#total_due").val(money(res.total_due));
        });
    }

    $("#start_date, #end_date").val(today());
    loadHeads();
    loadMethods(function () { loadGroups(loadUsers); });
    loadTable();

    $("#transactionmainheads").on("change", function () { loadMethods(function () { loadGroups(loadUsers); }); loadTable(); });
    $("#transaction_with_method").on("change", function () { loadGroups(loadUsers); loadTable(); });
    $("#transaction_with").on("change", function () { loadUsers(); loadTable(); });
    $("#transaction_with_user, #status").on("change", loadTable);
    $("#supplierSearch").on("input", render);
    $("#partyPaymentFilter").on("submit", function (event) { event.preventDefault(); loadTable(); });

    $(document).on("click", ".payment-btn", function () {
        window.location.href = window.APP_URLS.PARTY_PAYMENT_FORM_BASE_URL + $(this).data("id") + "/";
    });

    $("#fifo_pay_btn").on("click", function () {
        const amount = parseFloat($("#fifo_payment").val()) || 0;
        if (amount <= 0 || !rows.length) { alert("Enter payment amount"); return; }
        $.post(window.APP_URLS.PARTY_PAYMENT_FIFO_URL, {
            payment: amount,
            ids: JSON.stringify(rows.map(item => item.id))
        }, function (res) {
            if (!res.success) { alert(res.error || "Payment failed"); return; }
            alert("Payment Successful!");
            loadTable();
        });
    });
});
