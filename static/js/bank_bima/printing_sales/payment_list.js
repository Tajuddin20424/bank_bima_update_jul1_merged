$(document).ready(function () {

    // =========================
    // VARIABLES
    // =========================
    let paymentList = [];   // ✅ rename
    let currentIndex = 0;
    let offset = 0;
    let query = "";
    let hasMore = true;
    let isLoading = false;
    let hasFiltered = false;
    let currentRequest = null;
    let selectedMainHead = "";
    let selectedWithMethod = "";
    let selectedWith = "";
    let selectedSupplier = "";
    let tranWithNameMap = {};
    let tranUserNameMap = {};

    function getLimit() {
        return parseInt($("#perPage").val(), 10) || 50;
    }

    function getSearchQuery() {
        return ($("#paymentSearch").val() || $("input[name='search']").val() || "").trim();
    }

    function getStatusFilter() {
        return ($("#statusFilter").val() || $("select[name='status']").val() || "").trim();
    }

    function readTopFilters() {
        return {
            mainHead: (document.getElementById("transactionmainheads")?.value || "").trim(),
            withMethod: (document.getElementById("transaction_with_method")?.value || "").trim(),
            withGroup: (document.getElementById("transaction_with")?.value || "").trim(),
            withGroupText: ($("#transaction_with option:selected").text() || "").trim(),
            withUser: (document.getElementById("transaction_with_user")?.value || "").trim(),
            withUserText: ($("#transaction_with_user option:selected").text() || "").trim(),
        };
    }

    function applyFilters() {
        query = getSearchQuery();
        offset = 0;
        currentIndex = 0;
        hasMore = true;
        hasFiltered = true;

        loadPaymentList(query, 0, false);
    }

    function normalizeKey(value) {
        return value === null || value === undefined ? "" : String(value);
    }

    function loadDisplayMaps(callback) {
        const tranWithUrl = window.APP_URLS.TRAN_WITHS_API_URL || "/general/api/tran-withs/";
        const tranUsersUrl = window.APP_URLS.TRAN_USERS_API_URL || "/general/api/tran-users/";

        $.when(
            $.getJSON(tranWithUrl),
            $.getJSON(tranUsersUrl)
        ).done(function (withRes, userRes) {
            tranWithNameMap = {};
            tranUserNameMap = {};

            const withRows = (withRes[0] && withRes[0].results) || [];
            const userRows = (userRes[0] && userRes[0].results) || [];

            withRows.forEach(function (item) {
                tranWithNameMap[normalizeKey(item.id)] = item.tran_with_name || item.name || normalizeKey(item.id);
            });

            userRows.forEach(function (item) {
                const name = item.user_name || normalizeKey(item.user_id || item.id);
                tranUserNameMap[normalizeKey(item.id)] = name;
                tranUserNameMap[normalizeKey(item.user_id)] = name;
            });

            if (callback) callback();
        }).fail(function () {
            if (callback) callback();
        });
    }

    // =========================
    // SET TODAY DATE
    // =========================
    function setTodayDate() {

        if ($("#start_date").val() || $("#end_date").val()) {
            return;
        }

        const today = new Date();
        const localDate =
            today.getFullYear() + "-" +
            String(today.getMonth() + 1).padStart(2, "0") + "-" +
            String(today.getDate()).padStart(2, "0");

        $("#start_date").val(localDate);
        $("#end_date").val(localDate);
    }

    // =========================
    // LOAD DATA
    // =========================
    function loadPaymentList(q = "", newOffset = 0, append = false) {

        if (currentRequest) {
            currentRequest.abort();
        }

        isLoading = true;

        const start_date = $("#start_date").val();
        const end_date = $("#end_date").val();
        const status = getStatusFilter();
        const limit = getLimit();
        const topFilters = readTopFilters();
        selectedMainHead = topFilters.mainHead;
        selectedWithMethod = topFilters.withMethod;
        selectedWith = topFilters.withGroup;
        selectedSupplier = topFilters.withUser;

        currentRequest = $.ajax({
            url: window.APP_URLS.PAYMENT_LIST_URL,
            method: "GET",
            cache: false,
            data: {
                _ts: Date.now(),
                q: q,
                search: q,
                status: status,
                offset: newOffset,
                limit: limit,
                per_page: limit,
                tran_main_head: selectedMainHead,
                transactionmainheads: selectedMainHead,
                tran_with_method: selectedWithMethod,
                transaction_with_method: selectedWithMethod,
                tran_with: selectedWith,
                transaction_with: selectedWith,
                supplier: selectedSupplier,
                transaction_with_user: selectedSupplier,
                start_date: start_date,
                end_date: end_date
            },

            success: function (res) {

                const fetched = res.results || [];

                if (append) {
                    paymentList = paymentList.concat(fetched);
                } else {
                    paymentList = fetched;
                    currentIndex = 0;
                }

                offset = newOffset;

                renderTable();

                $("#total_due").val(res.total_due || 0);

                hasMore = fetched.length === limit;

                isLoading = false;
            },

            error: function () {
                isLoading = false;
            }
        });
    }

    // =========================
    // RENDER
    // =========================
    function renderTable() {

        let html = "";

        function displayDate(value) {
            if (!value) return "-";
            return String(value).split("T")[0].split(" ")[0];
        }

        function displayTime(row) {
            if (row.tran_time) return row.tran_time;
            if (!row.tran_date) return "-";
            let value = String(row.tran_date);
            if (value.includes("T")) {
                return value.split("T")[1].substring(0, 8);
            }
            if (value.includes(" ")) {
                return value.split(" ")[1].substring(0, 8);
            }
            return "-";
        }

        function displayInvoice(row) {
            return row.invoice_ref || row.invoice || row.tran_id || "-";
        }

        function displayTranWith(row) {
            const value = row.tran_type_with;
            const idValue = row.tran_type_with_id;
            return tranWithNameMap[normalizeKey(idValue)] || tranWithNameMap[normalizeKey(value)] || value || "-";
        }

        function displayTranUser(row) {
            const value = row.tran_user;
            const idValue = row.tran_user_id;
            return row.user_name || tranUserNameMap[normalizeKey(idValue)] || tranUserNameMap[normalizeKey(value)] || value || "-";
        }

        paymentList.forEach((p, i) => {
            html += `
                <tr data-index="${i}" class="${i === currentIndex ? 'table-active' : ''}">
                    <td>${i + 1}</td>
                    <td>${p.tran_id}</td>
                    <td>${displayInvoice(p)}</td>
                    <td>${displayDate(p.tran_date)}</td>
                    <td>${displayTranWith(p)}</td>
                    <td>${displayTranUser(p)}</td>
                    <td style="text-align:right;">${p.bill_total}</td>
                    <td style="text-align:right;">${p.discount}</td>
                    <td style="text-align:right;">${p.net_total}</td>
                    <td style="text-align:right;">${p.advance ?? 0}</td>
                    <td style="text-align:right;">${p.due_collection}</td>
                    <td style="text-align:right;">${p.due_discount}</td>
                    <td style="text-align:right;">${p.due}</td>
                    <td class="text-center">
                        <button class="btn btn-sm btn-primary edit-payment-btn"
                            data-id="${p.id}">
                            Edit
                        </button>
                    </td>
                    <td>${displayTime(p)}</td>
                </tr>
            `;
        });

        $("#paymentListTableBody").html(html);  // ✅ changed
    }

    // =========================
    // INIT
    // =========================
    setTodayDate();
    loadDisplayMaps(function () {
        loadPaymentFilterCombos(function () {
            paymentList = [];
            renderTable();
            $("#total_due").val(0);
        });
    });

    function selectFirstIfEmpty(selector) {
        let $select = $(selector);
        if (!$select.val()) {
            $select.prop("selectedIndex", 0);
        }
        return $select.val() || "";
    }

    function selectFirstNonEmpty(selector) {
        let $select = $(selector);
        let currentValue = $select.val() || "";
        if (currentValue) return currentValue;
        let firstValue = "";
        $select.find("option").each(function () {
            if ($(this).val()) {
                firstValue = $(this).val();
                return false;
            }
        });
        if (firstValue) $select.val(firstValue);
        return firstValue;
    }

    function loadPaymentFilterCombos(callback) {
        if (typeof loadTransactionMainHeadsCombo !== "function") {
            if (callback) callback();
            return;
        }

        const initUrl = window.APP_URLS.PAGE_INIT_URL;
        const pageId = window.APP_URLS.PAGE_ID;
        const finish = function () { if (callback) callback(); };
        const loadCombos = function (init) {
            const mainHead = init?.tran_main_head_id || 1;
            const withMethod = init?.user_tran_method || "Payment";
            const withGroup = init?.user_tran_with_id || "";
            loadTransactionMainHeadsCombo(mainHead, function () {
                selectedMainHead = $("#transactionmainheads").val() || "";
                loadTransactionWithMethodsCombo(withMethod, function () {
                    selectedWithMethod = $("#transaction_with_method").val() || "";
                    loadTransactionWithCombo(withGroup, function () {
                        selectedWith = $("#transaction_with").val() || "";
                        loadTransactionWithUserCombo("", function () {
                            selectedSupplier = "";
                            finish();
                        });
                    });
                });
            });
        };
        if (initUrl && pageId) {
            $.getJSON(initUrl, { page_id: pageId })
                .done(function (response) { loadCombos((response.get_page_init_data || [])[0] || {}); })
                .fail(function () { loadCombos({}); });
        } else {
            loadCombos({});
        }
    }

    function reloadTransactionWithUsers(callback) {
        selectedSupplier = "";
        if (typeof loadTransactionWithUserCombo === "function") {
            loadTransactionWithUserCombo("", function () {
                selectedSupplier = selectFirstNonEmpty("#transaction_with_user");
                if (callback) callback();
            });
        } else if (callback) {
            callback();
        }
    }

    function clearPaymentListUntilFilter() {
        hasFiltered = false;
        paymentList = [];
        currentIndex = 0;
        offset = 0;
        hasMore = false;
        renderTable();
        $("#total_due").val(0);
    }

    $("#transactionmainheads, #transaction_with_method, #transaction_with, #transaction_with_user").off("change");

    $("#transactionmainheads").on("change", function () {
        selectedMainHead = this.value;
        selectedWithMethod = "";
        selectedWith = "";
        selectedSupplier = "";
        if (typeof loadTransactionWithMethodsCombo === "function") {
            loadTransactionWithMethodsCombo("Payment", function () {
                selectedWithMethod = $("#transaction_with_method").val() || selectFirstIfEmpty("#transaction_with_method");
                if (typeof loadTransactionWithCombo === "function") {
                    loadTransactionWithCombo("", function () {
                        selectedWith = $("#transaction_with").val() || selectFirstIfEmpty("#transaction_with");
                        reloadTransactionWithUsers(clearPaymentListUntilFilter);
                    });
                } else {
                    clearPaymentListUntilFilter();
                }
            });
        } else {
            clearPaymentListUntilFilter();
        }
    });

    $("#transaction_with_method").on("change", function () {
        selectedWithMethod = this.value;
        selectedWith = "";
        selectedSupplier = "";
        if (typeof loadTransactionWithCombo === "function") {
            loadTransactionWithCombo("", function () {
                selectedWith = $("#transaction_with").val() || selectFirstIfEmpty("#transaction_with");
                reloadTransactionWithUsers(clearPaymentListUntilFilter);
            });
        } else {
            clearPaymentListUntilFilter();
        }
    });

    $("#transaction_with").on("change", function () {
        selectedWith = this.value;
        selectedSupplier = "";
        reloadTransactionWithUsers(clearPaymentListUntilFilter);
    });

    $("#transaction_with_user").on("change", function () {
        selectedSupplier = this.value;
        clearPaymentListUntilFilter();
    });

    // =========================
    // DATE CHANGE AUTO FILTER
    // =========================
    $("#start_date, #end_date").on("change", function () {
        query = getSearchQuery();
        clearPaymentListUntilFilter();
    });

    // =========================
    // SEARCH INPUT
    // =========================
    let typingTimer;

    $("#paymentSearch, input[name='search']").on("input", function () {

        clearTimeout(typingTimer);

        typingTimer = setTimeout(() => {

            clearPaymentListUntilFilter();

        }, 300);
    });

    $("#statusFilter, select[name='status'], #perPage").on("change", function () {
        clearPaymentListUntilFilter();
    });

    $("#paymentFilterForm").on("submit", function (e) {
        e.preventDefault();
        applyFilters();
    });

    $("#paymentFilterBtn").on("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        applyFilters();
    });

    $(document).on("click", ".edit-payment-btn", function () {
        const id = $(this).data("id");
        window.location.href = window.APP_URLS.PAYMENT_EDIT_URL + id + "/";
    });

    // =========================
    // SCROLL PAGINATION
    // =========================
    $(".table-responsive").on("scroll", function () {

        if ($(this).scrollTop() + $(this).innerHeight() >= this.scrollHeight - 10) {

            if (hasFiltered && hasMore && !isLoading) {
                offset += getLimit();
                loadPaymentList(query, offset, true);  // ✅ changed
            }
        }
    });

    // =========================
    // PRINT REPORT
    // =========================
    $("#printReportBtn").on("click", function () {

        let start_date = $("#start_date").val();
        let end_date = $("#end_date").val();
        let q = getSearchQuery();
        let status = getStatusFilter();
        let limit = getLimit();

        let params = new URLSearchParams({
            q: q,
            search: q,
            status: status,
            per_page: limit,
            limit: limit,
            tran_main_head: selectedMainHead,
            transactionmainheads: selectedMainHead,
            tran_with_method: selectedWithMethod,
            transaction_with_method: selectedWithMethod,
            tran_with: selectedWith,
            transaction_with: selectedWith,
            supplier: selectedSupplier,
            transaction_with_user: selectedSupplier,
            start_date: start_date || "",
            end_date: end_date || ""
        });

        let url = `${window.APP_URLS.PAYMENT_REPORT_PDF_URL}?${params.toString()}`;

        window.open(url, "_blank");
    });

});
