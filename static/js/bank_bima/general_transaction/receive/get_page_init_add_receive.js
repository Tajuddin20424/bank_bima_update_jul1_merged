// Bank Bima General Transaction Receive page-init loader.
const bankBimaReceivePageId = new URLSearchParams(window.location.search).get("page_id");

function loadBankBimaReceivePageInit() {
    if (!bankBimaReceivePageId) {
        return;
    }

    window.__PAGE_INIT_LOADING = true;

    $.ajax({
        url: "/bank-bima/get-page-init-add-payment/",
        method: "GET",
        data: { page_id: bankBimaReceivePageId },
        success: function (response) {
            const row = response.get_page_init_data && response.get_page_init_data[0];
            if (!row) {
                window.__PAGE_INIT_LOADING = false;
                return;
            }

            function setIfExists(selector, value) {
                const $select = $(selector);
                if ($select.length && value !== null && value !== undefined && value !== "") {
                    $select.val(String(value));
                }
            }

            loadTransactionMainHeadsCombo(row.tran_main_head_id, function () {
                setIfExists("#transactionmainheads", row.tran_main_head_id);
                loadTransactionMethodsCombo(row.tran_method, function () {
                    setIfExists("#tran_method", row.tran_method);
                    loadTransactionGroupCombo(row.tran_group_id, function () {
                        setIfExists("#tran_group", row.tran_group_id);
                        loadTransactionWithMethodsCombo(row.user_tran_method, function () {
                            setIfExists("#transaction_with_method", row.user_tran_method);
                            loadTransactionWithCombo(row.user_tran_with_id, function () {
                                setIfExists("#transaction_with", row.user_tran_with_id);
                                setIfExists("#tran_type", row.tran_main_head_id);
                                window.__PAGE_INIT_LOADING = false;
                            });
                        });
                    });
                });
            });
        },
        error: function (xhr) {
            window.__PAGE_INIT_LOADING = false;
            console.error("Failed to load Bank Bima receive page init", xhr);
        }
    });
}

$(document).ready(function () {
    loadBankBimaReceivePageInit();
});
