$(function () {
    let rows = [];
    let request = null;

    function today() {
        const date = new Date();
        return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
    }

    function money(value) {
        return (parseFloat(value) || 0).toFixed(2);
    }

    function render() {
        const html = rows.length ? rows.map(function (item, index) {
            return `<tr>
                <td>${index + 1}</td>
                <td>${item.tran_id || ""}</td>
                <td>${item.invoice_ref || "-"}</td>
                <td>${item.tran_date || ""}</td>
                <td>${item.supplier_name || "-"}</td>
                <td>${item.user_name || "-"}</td>
                <td class="text-end">${money(item.bill_total)}</td>
                <td class="text-end">${money(item.discount)}</td>
                <td class="text-end">${money(item.net_total)}</td>
                <td class="text-end">${money(item.receive)}</td>
                <td class="text-end">${money(item.payment)}</td>
                <td class="text-end">${money(item.due)}</td>
                <td><button class="btn btn-sm btn-primary payment-btn" data-id="${item.id}">Payment</button></td>
            </tr>`;
        }).join("") : '<tr><td colspan="13" class="text-center py-3">No payment data found</td></tr>';
        $("#pharmacyPartyPaymentBody").html(html);
    }

    function loadTable() {
        if (request) request.abort();
        request = $.getJSON(window.APP_URLS.PARTY_PAYMENT_LIST_URL, {
            q: $("#pharmacyPartySearch").val() || "",
            start_date: $("#pharmacy_start_date").val() || "",
            end_date: $("#pharmacy_end_date").val() || "",
            limit: $("#pharmacyPerPage").val() || 50,
            offset: 0
        }, function (response) {
            rows = response.results || [];
            render();
            $("#pharmacy_total_due").val(money(response.total_due));
        }).fail(function () {
            rows = [];
            render();
            $("#pharmacy_total_due").val("0.00");
        });
    }

    $("#pharmacy_start_date, #pharmacy_end_date").val(today());
    loadTable();

    $("#pharmacyPartyPaymentFilter").on("submit", function (event) {
        event.preventDefault();
        loadTable();
    });

    $("#pharmacyPartySearch").on("keydown", function (event) {
        if (event.key === "Enter") {
            event.preventDefault();
            loadTable();
        }
    });

    $(document).on("click", ".payment-btn", function () {
        window.location.href = window.APP_URLS.PARTY_PAYMENT_FORM_BASE_URL + $(this).data("id") + "/";
    });

    $("#pharmacy_fifo_pay_btn").on("click", function () {
        const amount = parseFloat($("#pharmacy_fifo_payment").val()) || 0;
        if (amount <= 0 || !rows.length) {
            alert("Enter payment amount");
            return;
        }
        $.post(window.APP_URLS.PARTY_PAYMENT_FIFO_URL, {
            payment: amount,
            ids: JSON.stringify(rows.map(item => item.id))
        }, function (response) {
            if (!response.success) {
                alert(response.error || "Payment failed");
                return;
            }
            alert("Payment Successful!");
            $("#pharmacy_fifo_payment").val("");
            loadTable();
        }).fail(function (xhr) {
            alert((xhr.responseJSON && xhr.responseJSON.error) || "Payment failed");
        });
    });
});
