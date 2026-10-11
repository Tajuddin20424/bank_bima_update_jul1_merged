
// ============================================================
// HOTEL - GET PAGE INIT ADD PAYMENT
// ============================================================

let urlParams = new URLSearchParams(window.location.search);

let page_id = urlParams.get('page_id');

console.log("HOTEL PAGE ID:", page_id);


// ============================================================
// GET INITIAL DATA
// ============================================================

function getInitData() {

    // Edit mode হলে init data আবার load করবে না
    if (
        (window.EDIT_PAYMENT_DATA && window.EDIT_PAYMENT_DATA.is_edit)
        || !page_id
    ) {
        return;
    }


    $.ajax({

        // Diagnosis -> Hotel
        url: "/hotel/get-page-init-add-payment/",

        method: "GET",

        data: {
            page_id: page_id
        },


        success: function (res) {

            console.log(
                "HOTEL INIT RESPONSE:",
                res
            );


            // -----------------------------------------------
            // CHECK DATA
            // -----------------------------------------------

            if (
                !res.get_page_init_data ||
                res.get_page_init_data.length === 0
            ) {

                console.log(
                    "Hotel page init data not found."
                );

                return;
            }


            let row =
                res.get_page_init_data[0];


            // -----------------------------------------------
            // GET VALUES
            // -----------------------------------------------

            let tran_main_head_id =
                row.tran_main_head_id;


            let user_tran_method =
                row.user_tran_method;


            let user_tran_with_id =
                row.user_tran_with_id;


            let tran_method =
                row.tran_method;


            let tran_group_id =
                row.tran_group_id;


            console.log(
                "tran_main_head_id:",
                tran_main_head_id
            );

            console.log(
                "user_tran_method:",
                user_tran_method
            );

            console.log(
                "user_tran_with_id:",
                user_tran_with_id
            );

            console.log(
                "tran_method:",
                tran_method
            );

            console.log(
                "tran_group_id:",
                tran_group_id
            );


            // =================================================
            // 1. TRANSACTION MAIN HEAD
            // =================================================

            loadTransactionMainHeadsCombo(
                tran_main_head_id,

                function () {

                    console.log(
                        "Hotel Transaction Main Head Loaded"
                    );


                    // =========================================
                    // 2. TRANSACTION METHOD
                    // =========================================

                    loadTransactionMethodsCombo(
                        tran_method,

                        function () {

                            console.log(
                                "Hotel Transaction Method Loaded"
                            );


                            // =================================
                            // 3. TRANSACTION GROUP
                            // =================================

                            loadTransactionGroupCombo(
                                tran_group_id,

                                function () {

                                    console.log(
                                        "Hotel Transaction Group Loaded"
                                    );


                                    // =========================
                                    // 4. LOAD PRODUCTS
                                    // =========================

                                    if (
                                        typeof loadProducts ===
                                        "function"
                                    ) {

                                        loadProducts();

                                    }

                                }
                            );

                        }
                    );


                    // =========================================
                    // 5. TRANSACTION WITH METHOD
                    // =========================================

                    loadTransactionWithMethodsCombo(
                        user_tran_method,

                        function () {

                            console.log(
                                "Hotel Transaction With Method Loaded"
                            );


                            // =================================
                            // 6. TRANSACTION WITH
                            // =================================

                            loadTransactionWithCombo(
                                user_tran_with_id,

                                function () {

                                    console.log(
                                        "Hotel Transaction With Loaded"
                                    );


                                    // =========================
                                    // 7. TRANSACTION WITH USER
                                    // =========================

                                    if (
                                        typeof loadTransactionWithUserCombo ===
                                        "function"
                                    ) {

                                        loadTransactionWithUserCombo();

                                    }

                                }
                            );

                        }
                    );

                }
            );

        },


        error: function (xhr) {

            console.log(
                "Hotel Init Data Load Error:",
                xhr.status,
                xhr.responseText
            );

        }

    });

}


// ============================================================
// DOCUMENT READY
// ============================================================

$(document).ready(function () {

    getInitData();

});