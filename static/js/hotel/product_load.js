let currentRequest = null;
let offset = 0;
let query = "";
let isLoading = false;
let limit = 50;

let lastSavedTransactionId = null;


// ============================================================
// TODAY DATE
// ============================================================

function setTodayDate() {

    const today = new Date();

    const localDate =
        today.getFullYear() + "-" +
        String(today.getMonth() + 1).padStart(2, "0") + "-" +
        String(today.getDate()).padStart(2, "0");


    if (document.getElementById("tranDate")) {
        document.getElementById("tranDate").value = localDate;
    }


    if (document.getElementById("expiryDate")) {
        document.getElementById("expiryDate").value = localDate;
    }
}


// ============================================================
// PRODUCT TOTAL
// ============================================================

function updateProductTotal() {

    let quantity =
        parseFloat($("#quantity").val()) || 0;

    let mrp =
        parseFloat($("#mrp").val()) || 0;

    let total =
        quantity * mrp;

    $("#total").val(
        total.toFixed(2)
    );
}


// ============================================================
// DOCUMENT READY
// ============================================================

$(document).ready(function () {

    console.log("HOTEL PRODUCT LOAD JS LOADED");


    // ========================================================
    // DEFAULT PRODUCT VALUES
    // ========================================================

    $("#quantity")
        .val(1)
        .prop("readonly", true);

    $("#cp")
        .val(0)
        .prop("readonly", true);

    $("#mrp")
        .val(0)
        .prop("readonly", true);


    setTodayDate();


    // ========================================================
    // OPEN PRODUCT SEARCH
    // ========================================================

    function openProductSearch() {

        if (!$("#productSearch").data("select2")) {
            return;
        }

        $("#productSearch").select2("open");


        setTimeout(function () {

            let searchField =
                document.querySelector(
                    ".select2-container--open .select2-search__field"
                );

            if (searchField) {

                searchField.focus();
                searchField.select();
            }

        }, 150);
    }


    // ========================================================
    // OPEN SELECT2 SEARCH
    // ========================================================

    function openSelect2Search(selector) {

        if (!$(selector).length) {
            return;
        }

        if (!$(selector).data("select2")) {
            return;
        }


        $(selector).select2("open");


        setTimeout(function () {

            let searchField =
                document.querySelector(
                    ".select2-container--open .select2-search__field"
                );


            if (searchField) {

                searchField.focus();
                searchField.select();
            }

        }, 100);
    }


    // ========================================================
    // FOCUS PRODUCT AFTER DUPLICATE
    // ========================================================

    function focusProductNameAfterDuplicateAlert() {

        const $productSearch =
            $("#productSearch");


        $("#addProductBtn").blur();

        $("#productid").val("");

        $productSearch
            .val(null)
            .trigger("change");


        setTimeout(function () {

            if (!$productSearch.data("select2")) {
                return;
            }


            $productSearch.select2("open");


            setTimeout(function () {

                const searchField =
                    document.querySelector(
                        ".select2-container--open .select2-search__field"
                    );


                if (searchField) {

                    searchField.focus();
                    searchField.select();
                }

            }, 150);

        }, 100);
    }


    // ========================================================
    // FOCUS PRODUCT BOX ONLY
    // ========================================================

    function focusProductBoxOnly() {

        let productBox =
            $("#productSearch")
                .next(".select2-container")
                .find(".select2-selection");


        if (productBox.length) {

            productBox.focus();
        }
    }


    // ========================================================
    // FAST FOCUS
    // ========================================================

    function focusFast(selector) {

        const applyFocus = function () {

            const el =
                document.querySelector(selector);


            if (!el) {
                return;
            }


            el.focus({
                preventScroll: true
            });


            if (
                typeof el.select === "function"
            ) {
                el.select();
            }
        };


        applyFocus();

        requestAnimationFrame(
            applyFocus
        );

        setTimeout(
            applyFocus,
            0
        );
    }


    // ========================================================
    // GUEST + PRODUCT READY CHECK
    // ========================================================

    function isReadyToFocusAddButton() {

        let guestSelected =
            $("#guest_lookup").val() ||
            $("#guest_id").val();


        let productSelected =
            $("#productSearch").val() ||
            $("#productid").val();


        return Boolean(
            guestSelected &&
            productSelected
        );
    }


    function focusAddButtonIfReady() {

        if (!isReadyToFocusAddButton()) {
            return false;
        }


        $("#addProductBtn").focus();

        return true;
    }


    // ========================================================
    // PAGE LOAD FOCUS
    // ========================================================

    setTimeout(function () {

        if (
            $("#guest_lookup").length &&
            $("#guest_lookup").data("select2")
        ) {

            $("#guest_lookup")
                .select2("open");
        }

    }, 300);


    // ========================================================
    // KEYBOARD FLOW
    //
    // Guest -> SR -> Product
    // ========================================================

    $("#guest_lookup")
        .off("select2:select.hotelKeyboardFlow")
        .on(
            "select2:select.hotelKeyboardFlow",
            function () {

                let selectedOption =
                    $(this).find(
                        "option:selected"
                    );


                // Guest ID
                $("#guest_id").val(
                    $(this).val() || ""
                );


                // Guest Name
                let guestName =
                    selectedOption.data("name") ||
                    selectedOption.data("guest-name") ||
                    selectedOption.text() ||
                    "";


                $("#guest_name").val(
                    guestName.trim()
                );


                // Guest Phone
                let guestPhone =
                    selectedOption.data("phone") ||
                    selectedOption.data("mobile") ||
                    "";


                $("#guest_phone").val(
                    guestPhone
                );


                // Guest Address
                let guestAddress =
                    selectedOption.data("address") ||
                    "";


                $("#guest_address").val(
                    guestAddress
                );


                setTimeout(function () {

                    openSelect2Search(
                        "#sr_lookup"
                    );

                }, 100);
            }
        );


    // ========================================================
    // SR -> PRODUCT
    // ========================================================

    $("#sr_lookup")
        .off("select2:select.hotelKeyboardFlow")
        .on(
            "select2:select.hotelKeyboardFlow",
            function () {

                let selectedOption =
                    $(this).find(
                        "option:selected"
                    );


                $("#sr_id").val(
                    $(this).val() || ""
                );


                $("#sr_name_display").val(
                    (
                        selectedOption.text() ||
                        ""
                    ).trim()
                );


                setTimeout(function () {

                    openProductSearch();

                }, 100);
            }
        );


    // ========================================================
    // TRANSACTION MAIN HEAD CHANGE
    // ========================================================

    $("#transactionmainheads")
        .off("change.productFilter")
        .on(
            "change.productFilter",
            function () {

                $("#productSearch")
                    .val(null)
                    .trigger("change");


                $("#productid").val("");
            }
        );


    // ========================================================
    // TRANSACTION GROUP CHANGE
    // ========================================================

    $("#tran_group")
        .off("change.productFilter")
        .on(
            "change.productFilter",
            function () {

                $("#productSearch")
                    .val(null)
                    .trigger("change");


                $("#productid").val("");
            }
        );


    // ========================================================
    // QTY -> ADD BUTTON
    // ========================================================

    $("#quantity")
        .off("keydown.hotelQty")
        .on(
            "keydown.hotelQty",
            function (e) {

                if (e.key === "Enter") {

                    e.preventDefault();


                    setTimeout(function () {

                        $("#addProductBtn")
                            .focus();

                    }, 0);
                }
            }
        );


    // ========================================================
    // ADD BUTTON ENTER
    // ========================================================

    $("#addProductBtn")
        .off("keydown.hotelAdd")
        .on(
            "keydown.hotelAdd",
            function (e) {

                if (e.key === "Enter") {

                    e.preventDefault();

                    $(this).click();
                }
            }
        );


    // ========================================================
    // ADD PRODUCT
    // ========================================================

    $("#addProductBtn")
        .off("click.hotelAddProduct")
        .on(
            "click.hotelAddProduct",
            function () {


                let productId =
                    (
                        $("#productid").val() ||
                        ""
                    )
                        .toString()
                        .trim();


                let name =
                    (
                        $("#productSearch option:selected")
                            .text() ||
                        ""
                    )
                        .toString()
                        .trim();


                if (
                    !name ||
                    name ===
                    "-- Start Typing Product ID / Name --"
                ) {

                    name = "";
                }


                let qty =
                    Number(
                        (
                            $("#quantity").val() ||
                            "1"
                        )
                            .toString()
                            .trim()
                    );


                let cp =
                    Number(
                        (
                            $("#cp").val() ||
                            "0"
                        )
                            .toString()
                            .trim()
                    );


                let mrp =
                    Number(
                        (
                            $("#mrp").val() ||
                            "0"
                        )
                            .toString()
                            .trim()
                    );


                let expiry =
                    (
                        $("#expiryDate").val() ||
                        ""
                    )
                        .toString()
                        .trim();


                let total =
                    qty * mrp;


                // ============================================
                // HOTEL GUEST VALIDATION
                // ============================================

                let guestId =
                    (
                        $("#guest_id").val() ||
                        $("#guest_lookup").val() ||
                        ""
                    )
                        .toString()
                        .trim();


                if (!guestId) {

                    alert(
                        "⚠️ Please select a guest first!"
                    );


                    setTimeout(function () {

                        openSelect2Search(
                            "#guest_lookup"
                        );

                    }, 100);


                    return;
                }


                // ============================================
                // PRODUCT VALIDATION
                // ============================================

                if (!name) {

                    alert(
                        "⚠️ Please enter product name!"
                    );

                    openProductSearch();

                    return;
                }


                if (!productId) {

                    alert(
                        "⚠️ Please select a product from the list!"
                    );

                    openProductSearch();

                    return;
                }


                // ============================================
                // DUPLICATE PRODUCT CHECK
                // ============================================

                let duplicate =
                    false;


                $("#selectedPaymentListPayment tr")
                    .each(function () {

                        if (
                            $(this).data("product-id") ==
                            productId
                        ) {

                            duplicate = true;

                            return false;
                        }
                    });


                if (duplicate) {

                    showDuplicateProductModal();

                    return;
                }


                // ============================================
                // ADD PRODUCT
                // ============================================

                addToSelectedList(
                    productId,
                    name,
                    qty,
                    cp,
                    mrp,
                    expiry,
                    total
                );


                clearInputs();

                updateInvoiceSummary();


                setTimeout(function () {

                    showAddMoreProductModal();

                }, 100);
            }
        );


    // ========================================================
    // ADD MORE PRODUCT MODAL
    // ========================================================

    function showAddMoreProductModal() {

        const modalElement =
            document.getElementById(
                "addMoreProductModal"
            );


        if (!modalElement) {

            openProductSearch();

            return;
        }


        if (
            typeof bootstrap ===
            "undefined" ||
            !bootstrap.Modal
        ) {

            openProductSearch();

            return;
        }


        let addMoreModal =
            bootstrap.Modal.getInstance(
                modalElement
            );


        if (!addMoreModal) {

            addMoreModal =
                new bootstrap.Modal(
                    modalElement,
                    {
                        backdrop: "static",
                        keyboard: false
                    }
                );
        }


        addMoreModal.show();


        $(modalElement)
            .off(
                "shown.bs.modal.addMoreProduct"
            )
            .on(
                "shown.bs.modal.addMoreProduct",
                function () {

                    $("#addMoreYesBtn")
                        .focus();
                }
            );
    }


    // ========================================================
    // DUPLICATE PRODUCT MODAL
    // ========================================================

    function showDuplicateProductModal() {

        const modalElement =
            document.getElementById(
                "duplicateProductModal"
            );


        if (!modalElement) {

            alert(
                "This product is already added!"
            );

            focusProductNameAfterDuplicateAlert();

            return;
        }


        if (
            typeof bootstrap ===
            "undefined" ||
            !bootstrap.Modal
        ) {

            alert(
                "This product is already added!"
            );

            focusProductNameAfterDuplicateAlert();

            return;
        }


        let duplicateModal =
            bootstrap.Modal.getInstance(
                modalElement
            );


        if (!duplicateModal) {

            duplicateModal =
                new bootstrap.Modal(
                    modalElement,
                    {
                        backdrop: "static",
                        keyboard: false,
                        focus: true
                    }
                );
        }


        $(modalElement)
            .off(
                "shown.bs.modal.duplicateProduct"
            )
            .one(
                "shown.bs.modal.duplicateProduct",
                function () {

                    $("#duplicateProductOkBtn")
                        .focus();
                }
            );


        duplicateModal.show();
    }


    // ========================================================
    // DUPLICATE MODAL OK
    // ========================================================

    $("#duplicateProductOkBtn")
        .off("click.duplicateProduct")
        .on(
            "click.duplicateProduct",
            function () {

                const modalElement =
                    document.getElementById(
                        "duplicateProductModal"
                    );


                const duplicateModal =
                    modalElement
                        ? bootstrap.Modal
                            .getInstance(
                                modalElement
                            )
                        : null;


                if (!modalElement) {

                    focusProductNameAfterDuplicateAlert();

                    return;
                }


                $(modalElement)
                    .off(
                        "hidden.bs.modal.duplicateProduct"
                    )
                    .one(
                        "hidden.bs.modal.duplicateProduct",
                        function () {

                            $("#addProductBtn")
                                .blur();

                            $("#productid")
                                .val("");

                            $("#productSearch")
                                .val(null)
                                .trigger("change");


                            setTimeout(function () {

                                openProductSearch();

                            }, 150);
                        }
                    );


                if (duplicateModal) {

                    duplicateModal.hide();
                }
            }
        );


    // ========================================================
    // ADD MORE YES
    // ========================================================

    $("#addMoreYesBtn")
        .off("click.addMoreProduct")
        .on(
            "click.addMoreProduct",
            function () {

                const modalElement =
                    document.getElementById(
                        "addMoreProductModal"
                    );


                if (!modalElement) {

                    openProductSearch();

                    return;
                }


                const addMoreModal =
                    bootstrap.Modal
                        .getInstance(
                            modalElement
                        );


                $(modalElement)
                    .off(
                        "hidden.bs.modal.addMoreYes"
                    )
                    .one(
                        "hidden.bs.modal.addMoreYes",
                        function () {

                            if (
                                document.activeElement
                            ) {

                                document
                                    .activeElement
                                    .blur();
                            }


                            setTimeout(function () {

                                openProductSearch();

                            }, 250);
                        }
                    );


                if (addMoreModal) {

                    addMoreModal.hide();
                }
            }
        );


    // ========================================================
    // ADD MORE NO
    // ========================================================

    $("#addMoreNoBtn")
        .off("click.addMoreProduct")
        .on(
            "click.addMoreProduct",
            function () {

                const modalElement =
                    document.getElementById(
                        "addMoreProductModal"
                    );


                if (!modalElement) {

                    $("#advanced")
                        .focus()
                        .select();

                    return;
                }


                const addMoreModal =
                    bootstrap.Modal
                        .getInstance(
                            modalElement
                        );


                $(modalElement)
                    .off(
                        "hidden.bs.modal.addMoreNo"
                    )
                    .one(
                        "hidden.bs.modal.addMoreNo",
                        function () {

                            $("#advanced")
                                .focus()
                                .select();
                        }
                    );


                if (addMoreModal) {

                    addMoreModal.hide();
                }
            }
        );


    // ========================================================
    // ADD MORE MODAL ARROW NAVIGATION
    // ========================================================

    $("#addMoreYesBtn, #addMoreNoBtn")
        .off(
            "keydown.addMoreNavigation"
        )
        .on(
            "keydown.addMoreNavigation",
            function (e) {

                if (
                    e.key !== "ArrowRight" &&
                    e.key !== "ArrowLeft"
                ) {

                    return;
                }


                e.preventDefault();


                const currentId =
                    $(this).attr("id");


                if (
                    currentId ===
                    "addMoreYesBtn"
                ) {

                    $("#addMoreNoBtn")
                        .focus();

                } else {

                    $("#addMoreYesBtn")
                        .focus();
                }
            }
        );


    // ========================================================
    // ADVANCE VALIDATION
    // ========================================================

    function validateAdvanceAmountOnEnter() {

        const advance =
            parseFloat(
                $("#advanced").val()
            ) || 0;


        const netAmount =
            parseFloat(
                $("#netAmount").val()
            ) || 0;


        if (
            advance > netAmount
        ) {

            alert(
                "⚠️ Advance amount cannot exceed balance/net amount!"
            );


            $("#advanced")
                .focus()
                .select();


            return false;
        }


        return true;
    }


    // ========================================================
    // ADVANCE -> SAVE
    // ========================================================

    $("#advanced")
        .off("keydown.advanceToSave")
        .on(
            "keydown.advanceToSave",
            function (e) {

                if (
                    e.key !== "Enter"
                ) {

                    return;
                }


                e.preventDefault();


                if (
                    !validateAdvanceAmountOnEnter()
                ) {

                    return;
                }


                $("#saveAllBtn")
                    .focus();
            }
        );


    // ========================================================
    // SAVE CONFIRM MODAL
    // ========================================================

    function showSaveTransactionConfirmModal() {

        const modalElement =
            document.getElementById(
                "saveTransactionConfirmModal"
            );


        if (!modalElement) {

            // Modal না থাকলে সরাসরি save
            saveTransaction();

            return;
        }


        if (
            typeof bootstrap ===
            "undefined" ||
            !bootstrap.Modal
        ) {

            saveTransaction();

            return;
        }


        let confirmModal =
            bootstrap.Modal
                .getInstance(
                    modalElement
                );


        if (!confirmModal) {

            confirmModal =
                new bootstrap.Modal(
                    modalElement,
                    {
                        backdrop: "static",
                        keyboard: false,
                        focus: true
                    }
                );
        }


        $(modalElement)
            .off(
                "shown.bs.modal.saveConfirm"
            )
            .one(
                "shown.bs.modal.saveConfirm",
                function () {

                    $("#saveConfirmYesBtn")
                        .focus();
                }
            );


        confirmModal.show();
    }


    // ========================================================
    // SAVE BUTTON
    // ========================================================

    $("#saveAllBtn")
        .off("click.saveConfirm")
        .on(
            "click.saveConfirm",
            function (e) {

                e.preventDefault();

                showSaveTransactionConfirmModal();
            }
        );


    // ========================================================
    // ACTUAL SAVE TRANSACTION
    // ========================================================

    function saveTransaction() {

        let paymentList = [];


        // ====================================================
        // SELECTED PRODUCTS
        // ====================================================

        $("#selectedPaymentListPayment tr")
            .each(function () {

                let row =
                    $(this);


                let expiryDate =
                    (
                        row
                            .find(
                                "td:eq(6)"
                            )
                            .text() ||
                        ""
                    ).trim();


                if (!expiryDate) {

                    expiryDate = null;
                }


                paymentList.push([

                    row.data(
                        "product-id"
                    ),

                    parseFloat(
                        row
                            .find(
                                "td:eq(3)"
                            )
                            .text()
                    ) || 0,

                    parseFloat(
                        row
                            .find(
                                "td:eq(4)"
                            )
                            .text()
                    ) || 0,

                    parseFloat(
                        row
                            .find(
                                "td:eq(5)"
                            )
                            .text()
                    ) || 0,

                    expiryDate,

                    parseFloat(
                        row
                            .find(
                                "td:eq(7)"
                            )
                            .text()
                    ) || 0
                ]);
            });


        if (!paymentList.length) {

            alert(
                "No products selected!"
            );

            return;
        }


        // ====================================================
        // GUEST VALIDATION
        // ====================================================

        let guestId =
            (
                $("#guest_id").val() ||
                $("#guest_lookup").val() ||
                ""
            )
                .toString()
                .trim();


        if (!guestId) {

            alert(
                "⚠️ Please select a guest first!"
            );


            openSelect2Search(
                "#guest_lookup"
            );


            return;
        }


        // ====================================================
        // PAYMENT VALIDATION
        // ====================================================

        let payment =
            parseFloat(
                $("#advanced").val()
            ) || 0;


        let netAmount =
            parseFloat(
                $("#netAmount").val()
            ) || 0;


        if (
            payment > netAmount
        ) {

            alert(
                "⚠️ Invalid Receive/Advance Amount! " +
                "It cannot exceed Net Amount."
            );


            $("#advanced")
                .focus()
                .select();


            return;
        }


        // ====================================================
        // TRANSACTION WITH
        // ====================================================

        let selectedUserText =
            $(
                "#transaction_with_user option:selected"
            ).text();


        let selectedUserId =
            $(
                "#transaction_with_user"
            ).val();


        let tranTypeWith =
            $("#transaction_with").val() ||
            $("#self_transaction_with").val();


        if (!tranTypeWith) {

            alert(
                "⚠️ Please select Transaction With or Self Transaction!"
            );

            return;
        }


        // ====================================================
        // GUEST DATA
        // ====================================================

        let guestName =
            (
                $("#guest_name").val() ||
                $("#guest_lookup option:selected")
                    .text() ||
                ""
            )
                .toString()
                .trim();


        let guestPhone =
            (
                $("#guest_phone").val() ||
                ""
            )
                .toString()
                .trim();


        let guestAddress =
            (
                $("#guest_address").val() ||
                ""
            )
                .toString()
                .trim();


        // ====================================================
        // HOTEL TRANSACTION TYPE
        //
        // Hardcoded Diagnosis 10 REMOVED.
        // Selected Hotel Main Head ID যাবে।
        // ====================================================

        let hotelTranType =
            parseInt(
                $("#transactionmainheads")
                    .val()
            ) || null;


        if (!hotelTranType) {

            alert(
                "⚠️ Please select Hotel Transaction Main Head!"
            );

            return;
        }


        // ====================================================
        // PAYLOAD
        // ====================================================

        let payload = {

            edit_id:
                window.EDIT_PAYMENT_DATA?.is_edit
                    ? window.EDIT_PAYMENT_DATA
                        .transaction?.id
                    : null,


            store:
                parseInt(
                    $(".store-select").val()
                ) || null,


            location:
                parseInt(
                    $(".location-select").val()
                ) || null,


            // Transaction With User
            supplier:
                selectedUserId,


            user_name:
                selectedUserText,


            tran_type_with:
                parseInt(
                    $("#transaction_with")
                        .val()
                ) || null,


            // HOTEL
            tran_type:
                hotelTranType,


            tran_method:
                "receive",


            invoice:
                $("#paymentinvoice").val() ||
                "",


            bill_amount:
                parseFloat(
                    $("#invoiceAmount")
                        .val()
                ) || 0,


            discount:
                parseFloat(
                    $("#discount")
                        .val()
                ) || 0,


            net_amount:
                parseFloat(
                    $("#netAmount")
                        .val()
                ) || 0,


            receive:
                0,


            payment:
                parseFloat(
                    $("#advanced")
                        .val()
                ) || 0,


            due:
                parseFloat(
                    $("#balance")
                        .val()
                ) || 0,


            tran_date:
                $("#tranDate")
                    .val(),


            products:
                paymentList,


            // ================================================
            // HOTEL GUEST
            // ================================================

            guest_id:
                guestId,


            guest_name:
                guestName,


            guest_phone:
                guestPhone,


            guest_address:
                guestAddress,


            // ================================================
            // SR SAME
            // ================================================

            referred_sr_id:
                (
                    $("#sr_id").val() ||
                    $("#sr_lookup").val() ||
                    ""
                )
                    .toString()
                    .trim() || null
        };


        console.log(
            "HOTEL SAVE PAYLOAD:",
            payload
        );


        // ====================================================
        // DISABLE SAVE
        // ====================================================

        $("#saveAllBtn")
            .prop(
                "disabled",
                true
            );


        $("#saveConfirmYesBtn")
            .prop(
                "disabled",
                true
            );


        // ====================================================
        // SAVE AJAX
        // ====================================================

        $.ajax({

            url:
                "/hotel/payment/save-payment/",

            type:
                "POST",


            headers: {

                "X-CSRFToken":
                    csrftoken
            },


            contentType:
                "application/json",


            data:
                JSON.stringify(
                    payload
                ),


            success:
                function (response) {

                    console.log(
                        "HOTEL SAVE RESPONSE:",
                        response
                    );


                    $("#saveAllBtn")
                        .prop(
                            "disabled",
                            false
                        );


                    $("#saveConfirmYesBtn")
                        .prop(
                            "disabled",
                            false
                        );


                    if (
                        !response.success
                    ) {

                        alert(
                            response.message ||
                            response.error ||
                            "Save failed!"
                        );

                        return;
                    }

                

                    // ========================================
                    // PREVIEW
                    // ========================================

                    showTransactionPreview(
                        response,
                        payload,
                        paymentList
                    );


                    // ========================================
                    // CLEAR PRODUCT LIST
                    // ========================================

                    $("#selectedPaymentListPayment")
                        .empty();


                    $("#invoiceAmount")
                        .val("0");


                    $("#discount")
                        .val("0");


                    $("#netAmount")
                        .val("0");


                    $("#advanced")
                        .val("0");


                    $("#balance")
                        .val("0");


                    $("#productid")
                        .val("");


                    $("#productSearch")
                        .val(null)
                        .trigger("change");


                    $("#quantity")
                        .val("1");


                    $("#cp")
                        .val("0");


                    $("#mrp")
                        .val("0");


                    $("#total")
                        .val("");
                },


            error:
                function (xhr) {

                    $("#saveAllBtn")
                        .prop(
                            "disabled",
                            false
                        );


                    $("#saveConfirmYesBtn")
                        .prop(
                            "disabled",
                            false
                        );


                    console.error(
                        "HOTEL SAVE ERROR:",
                        xhr.status,
                        xhr.responseText
                    );


                    let errorMessage =
                        "Save failed! Please try again.";


                    if (
                        xhr.responseJSON
                    ) {

                        errorMessage =
                            xhr.responseJSON
                                .message ||

                            xhr.responseJSON
                                .error ||

                            errorMessage;

                    } else if (
                        xhr.responseText
                    ) {

                        try {

                            const response =
                                JSON.parse(
                                    xhr.responseText
                                );


                            errorMessage =
                                response.message ||
                                response.error ||
                                errorMessage;

                        } catch (error) {

                            console.error(
                                "Invalid error response:",
                                error
                            );
                        }
                    }


                    alert(
                        errorMessage
                    );


                    // ========================================
                    // GUEST VALIDATION ERROR
                    // ========================================

                    if (
                        errorMessage
                            .toLowerCase()
                            .includes(
                                "guest"
                            )
                    ) {

                        $("#guest_id")
                            .val("");


                        $("#guest_lookup")
                            .val(null)
                            .trigger(
                                "change"
                            );


                        setTimeout(
                            function () {

                                openSelect2Search(
                                    "#guest_lookup"
                                );

                            },
                            150
                        );


                        return;
                    }


                    $("#saveAllBtn")
                        .focus();
                }
        });
    }


    // ========================================================
    // SAVE CONFIRM YES
    // ========================================================

    $("#saveConfirmYesBtn")
        .off(
            "click.saveTransaction"
        )
        .on(
            "click.saveTransaction",
            function () {

                const modalElement =
                    document.getElementById(
                        "saveTransactionConfirmModal"
                    );


                if (!modalElement) {

                    saveTransaction();

                    return;
                }


                const confirmModal =
                    bootstrap.Modal
                        .getInstance(
                            modalElement
                        );


                $(modalElement)
                    .off(
                        "hidden.bs.modal.saveYes"
                    )
                    .one(
                        "hidden.bs.modal.saveYes",
                        function () {

                            saveTransaction();
                        }
                    );


                if (confirmModal) {

                    confirmModal.hide();

                } else {

                    saveTransaction();
                }
            }
        );


    // ========================================================
    // SAVE CONFIRM NO
    // ========================================================

    $("#saveConfirmNoBtn")
        .off(
            "click.saveTransaction"
        )
        .on(
            "click.saveTransaction",
            function () {

                const modalElement =
                    document.getElementById(
                        "saveTransactionConfirmModal"
                    );


                if (!modalElement) {

                    $("#saveAllBtn")
                        .focus();

                    return;
                }


                const confirmModal =
                    bootstrap.Modal
                        .getInstance(
                            modalElement
                        );


                $(modalElement)
                    .off(
                        "hidden.bs.modal.saveNo"
                    )
                    .one(
                        "hidden.bs.modal.saveNo",
                        function () {

                            $("#saveAllBtn")
                                .focus();
                        }
                    );


                if (confirmModal) {

                    confirmModal.hide();
                }
            }
        );


    // ========================================================
    // SAVE MODAL ARROW
    // ========================================================

    $("#saveConfirmYesBtn, #saveConfirmNoBtn")
        .off(
            "keydown.saveConfirmNavigation"
        )
        .on(
            "keydown.saveConfirmNavigation",
            function (e) {

                if (
                    e.key !== "ArrowRight" &&
                    e.key !== "ArrowLeft"
                ) {

                    return;
                }


                e.preventDefault();


                if (
                    $(this).attr("id") ===
                    "saveConfirmYesBtn"
                ) {

                    $("#saveConfirmNoBtn")
                        .focus();

                } else {

                    $("#saveConfirmYesBtn")
                        .focus();
                }
            }
        );


    // ========================================================
    // PRICE × QTY
    // ========================================================

    $("#quantity, #mrp")
        .off("input.hotelTotal")
        .on(
            "input.hotelTotal",
            function () {

                updateProductTotal();
            }
        );


    // ========================================================
    // ADD PRODUCT TO TABLE
    // ========================================================

    function addToSelectedList(
        productId,
        pname,
        qty,
        cp,
        mrp,
        expiry,
        total
    ) {

        let row = `

            <tr data-product-id="${productId}">

                <td>
                    ${
                        $("#selectedPaymentListPayment tr")
                            .length + 1
                    }
                </td>

                <td style="display:none;">
                    ${productId}
                </td>

                <td>
                    ${pname}
                </td>

                <td>
                    ${qty}
                </td>

                <td>
                    ${cp}
                </td>

                <td style="display:none;">
                    ${mrp}
                </td>

                <td style="display:none;">
                    ${expiry || ""}
                </td>

                <td>
                    ${Number(total).toFixed(2)}
                </td>

                <td>

                    <button
                        type="button"
                        class="btn btn-sm btn-primary edit-item">

                        Edit

                    </button>

                    <button
                        type="button"
                        class="btn btn-sm btn-danger remove-item">

                        Remove

                    </button>

                </td>

            </tr>
        `;


        $("#selectedPaymentListPayment")
            .append(row);


        updateSerial();

        updateInvoiceSummary();
    }


    // ========================================================
    // APPEND EDIT PRODUCT
    // ========================================================

    function appendEditProductRow(
        item
    ) {

        let productId =
            item.product_id || "";


        let name =
            item.product_name ||
            productId;


        let qty =
            parseFloat(
                item.quantity
            ) || 0;


        let cp =
            parseFloat(
                item.cp
            ) || 0;


        let mrp =
            parseFloat(
                item.mrp
            ) || 0;


        let expiry =
            item.expiry_date ||
            "";


        let total =
            parseFloat(
                item.total
            ) || 0;


        let row = `

            <tr data-product-id="${productId}">

                <td>
                    ${
                        $("#selectedPaymentListPayment tr")
                            .length + 1
                    }
                </td>

                <td style="display:none;">
                    ${productId}
                </td>

                <td>
                    ${name}
                </td>

                <td>
                    ${qty}
                </td>

                <td>
                    ${cp}
                </td>

                <td style="display:none;">
                    ${mrp}
                </td>

                <td style="display:none;">
                    ${expiry}
                </td>

                <td>
                    ${total.toFixed(2)}
                </td>

                <td>

                    <button
                        type="button"
                        class="btn btn-sm btn-primary edit-item">

                        Edit

                    </button>

                    <button
                        type="button"
                        class="btn btn-sm btn-danger remove-item">

                        Remove

                    </button>

                </td>

            </tr>
        `;


        $("#selectedPaymentListPayment")
            .append(row);
    }


    // ========================================================
    // EDIT PRODUCT
    // ========================================================

    $(document)
        .off(
            "click.hotelEditItem",
            ".edit-item"
        )
        .on(
            "click.hotelEditItem",
            ".edit-item",
            function () {

                let row =
                    $(this)
                        .closest("tr");


                let productId =
                    row
                        .find("td:eq(1)")
                        .text()
                        .trim();


                let name =
                    row
                        .find("td:eq(2)")
                        .text()
                        .trim();


                let qty =
                    row
                        .find("td:eq(3)")
                        .text()
                        .trim();


                let cp =
                    row
                        .find("td:eq(4)")
                        .text()
                        .trim();


                let mrp =
                    row
                        .find("td:eq(5)")
                        .text()
                        .trim();


                let expiry =
                    row
                        .find("td:eq(6)")
                        .text()
                        .trim();


                // Remove old row
                row.remove();


                updateSerial();
                updateInvoiceSummary();


                $("#productid")
                    .val(productId);


                let productOption =
                    new Option(
                        name,
                        productId,
                        true,
                        true
                    );


                $("#productSearch")
                    .append(
                        productOption
                    )
                    .trigger(
                        "change"
                    );


                $("#quantity")
                    .val(qty);


                $("#cp")
                    .val(cp);


                $("#mrp")
                    .val(mrp);


                $("#expiryDate")
                    .val(expiry);


                $("#total")
                    .val(
                        (
                            (
                                parseFloat(qty) ||
                                0
                            ) *
                            (
                                parseFloat(mrp) ||
                                0
                            )
                        ).toFixed(2)
                    );


                $("#addProductBtn")
                    .focus();
            }
        );


    // ========================================================
    // CLEAR PRODUCT INPUT
    // ========================================================

    function clearInputs() {

        $("#productid")
            .val("");


        $("#productSearch")
            .val(null)
            .trigger(
                "change"
            );


        $("#cp")
            .val("0");


        $("#mrp")
            .val("0");


        $("#quantity")
            .val("1");


        $("#total")
            .val("");


        if (
            $("#expiryDate").length
        ) {

            $("#expiryDate")
                .val("");
        }
    }


    // ========================================================
    // UPDATE SERIAL
    // ========================================================

    function updateSerial() {

        $("#selectedPaymentListPayment tr")
            .each(
                function (
                    index
                ) {

                    $(this)
                        .find(
                            "td:eq(0)"
                        )
                        .text(
                            index + 1
                        );
                }
            );
    }


    // ========================================================
    // REMOVE PRODUCT
    // ========================================================

    $(document)
        .off(
            "click.hotelRemoveItem",
            ".remove-item"
        )
        .on(
            "click.hotelRemoveItem",
            ".remove-item",
            function () {

                let productName =
                    $(this)
                        .closest("tr")
                        .find(
                            "td:eq(2)"
                        )
                        .text();


                if (
                    confirm(
                        "Are you sure to remove:\n\n" +
                        productName +
                        " ?"
                    )
                ) {

                    $(this)
                        .closest("tr")
                        .remove();
                }


                updateSerial();

                updateInvoiceSummary();

                focusProductBoxOnly();
            }
        );


    // ========================================================
    // INVOICE SUMMARY
    // ========================================================

    function updateInvoiceSummary() {

        let invoiceAmount =
            0;


        $("#selectedPaymentListPayment tr")
            .each(function () {

                let rowTotal =
                    parseFloat(
                        $(this)
                            .find(
                                "td:eq(7)"
                            )
                            .text()
                    ) || 0;


                invoiceAmount +=
                    rowTotal;
            });


        let discountAmount =
            parseFloat(
                $("#discount")
                    .val()
            ) || 0;


        let advance =
            parseFloat(
                $("#advanced")
                    .val()
            ) || 0;


        let netAmount =
            invoiceAmount -
            discountAmount;


        if (
            netAmount < 0
        ) {

            netAmount = 0;
        }


        let balance;


        // ====================================================
        // EDIT MODE
        // ====================================================

        if (
            window.EDIT_PAYMENT_DATA &&
            window.EDIT_PAYMENT_DATA
                .is_edit &&
            window.EDIT_PAYMENT_DATA
                .transaction
        ) {

            let t =
                window
                    .EDIT_PAYMENT_DATA
                    .transaction;


            let dueCol =
                parseFloat(
                    t.due_col
                ) || 0;


            let dueDisc =
                parseFloat(
                    t.due_disc
                ) || 0;


            balance =
                netAmount -
                advance -
                dueCol -
                dueDisc;

        } else {

            // ================================================
            // ADD MODE
            // ================================================

            balance =
                netAmount -
                advance;
        }


        if (
            balance < 0
        ) {

            balance = 0;
        }


        $("#invoiceAmount")
            .val(
                invoiceAmount
                    .toFixed(2)
            );


        $("#netAmount")
            .val(
                netAmount
                    .toFixed(2)
            );


        $("#balance")
            .val(
                balance
                    .toFixed(2)
            );
    }


    // ========================================================
    // DISCOUNT / ADVANCE
    // ========================================================

    $("#discount, #advanced")
        .off(
            "input.hotelInvoice"
        )
        .on(
            "input.hotelInvoice",
            function () {

                updateInvoiceSummary();
            }
        );


    // ========================================================
    // SET SELECT2 OPTION
    // ========================================================

    function setSelect2Option(
        selector,
        value,
        text
    ) {

        if (!value) {
            return;
        }


        let label =
            text || value;


        let option =
            new Option(
                label,
                value,
                true,
                true
            );


        $(selector)
            .append(
                option
            )
            .trigger(
                "change"
            );
    }


    // ========================================================
    // EDIT HOTEL PAYMENT
    // ========================================================

    function initEditPaymentForm() {

        let editData = window.EDIT_PAYMENT_DATA || {};

        if (!editData.is_edit || !editData.transaction) {
            return;
        }

        let t = editData.transaction;
        let details = editData.details || [];

        // Title
        $(".card-header h5").first().text("Edit Hotel Payment");
        $("#saveAllBtn").text("Update");

        // Date + Invoice
        $("#tranDate").val(t.tran_date || "");
        $("#paymentinvoice").val(t.invoice_ref || t.tran_id || "");
        $("#payment_method").val(t.tran_method || "cash");

        // Location + Store
        $(".location-select").val(t.loc_id || "").trigger("change");
        $(".store-select").val(t.store_id || "");

        // Guest
        let guestId = t.tran_user || t.guest_id || "";

        $("#guest_id").val(guestId);
        $("#guest_user_id").val(guestId);
        $("#guest_id_display").val(guestId);
        $("#guest_name").val(t.guest_name || "");
        $("#guest_phone").val(t.guest_phone || "");
        $("#guest_address").val(t.guest_address || "");

        if ($("#guest_lookup").length && guestId) {
            setSelect2Option("#guest_lookup", guestId, t.guest_name || guestId);
        }

        // SR
        $("#sr_id").val(t.sr_id || "");
        $("#sr_name_display").val(t.sr_name || "");

        if ($("#sr_lookup").length && t.sr_id) {
            setSelect2Option("#sr_lookup", t.sr_id, t.sr_name || t.sr_id);
        }

        // Old Products
        $("#selectedPaymentListPayment").empty();

        details.forEach(function (item) {
            appendEditProductRow(item);
        });

        updateSerial();

        // Amount
        $("#discount").val(parseFloat(t.discount || 0).toFixed(2));
        $("#advanced").val(parseFloat(t.payment || 0).toFixed(2));

        // Account Main Heads -> Transaction Method -> Transaction Group
        if (typeof loadTransactionMainHeadsCombo === "function") {

            loadTransactionMainHeadsCombo(t.tran_type || null, function () {

                if (typeof loadTransactionMethodsCombo === "function") {

                    loadTransactionMethodsCombo(
                        t.tran_group_method || t.tran_method || null,
                        function () {

                            if (typeof loadTransactionGroupCombo === "function") {
                                loadTransactionGroupCombo(t.tran_group_id || null, function () {
                                    if (typeof loadProducts === "function") {
                                        loadProducts();
                                    }
                                });
                            }
                        }
                    );
                }

                // Transaction With
                if (typeof loadTransactionWithMethodsCombo === "function") {
                    loadTransactionWithMethodsCombo(t.tran_with_method || null, function () {
                        if (typeof loadTransactionWithCombo === "function") {
                            loadTransactionWithCombo(t.tran_type_with || null, function () {
                                if (typeof loadTransactionWithUserCombo === "function") {
                                    loadTransactionWithUserCombo(t.tran_user || null);
                                }
                            });
                        }
                    });
                }
            });
        }

        // Recalculate after old products are loaded
        updateInvoiceSummary();

        console.log("HOTEL EDIT FORM LOADED", t);
    }


    // ========================================================
    // EDIT INITIALIZE
    // ========================================================

    setTimeout(
        initEditPaymentForm,
        500
    );


    // ========================================================
    // OPTIONAL SR
    //
    // SR dropdown open অবস্থায় Enter দিলে,
    // value না থাকলে Product-এ যাবে।
    // ========================================================

    $(document)
        .off(
            "keydown.hotelOptionalSr",
            ".select2-search__field"
        )
        .on(
            "keydown.hotelOptionalSr",
            ".select2-search__field",
            function (e) {

                if (
                    e.key !== "Enter"
                ) {

                    return;
                }


                const $srLookup =
                    $("#sr_lookup");


                if (
                    !$srLookup.length ||
                    !$srLookup.data(
                        "select2"
                    )
                ) {

                    return;
                }


                const srSelect2 =
                    $srLookup.data(
                        "select2"
                    );


                if (
                    !srSelect2.isOpen()
                ) {

                    return;
                }


                if (
                    $srLookup.val()
                ) {

                    return;
                }


                e.preventDefault();

                e.stopPropagation();

                e.stopImmediatePropagation();


                $srLookup
                    .select2(
                        "close"
                    );


                setTimeout(
                    function () {

                        openProductSearch();

                    },
                    100
                );
            }
        );


    // ========================================================
    // INITIAL SUMMARY
    // ========================================================

    updateInvoiceSummary();

});


// ============================================================
// CSRF TOKEN
// ============================================================

function getCookie(name) {

    let cookieValue =
        null;


    if (
        document.cookie &&
        document.cookie !== ""
    ) {

        const cookies =
            document.cookie
                .split(";");


        for (
            let i = 0;
            i < cookies.length;
            i++
        ) {

            const cookie =
                cookies[i]
                    .trim();


            if (
                cookie.substring(
                    0,
                    name.length + 1
                ) ===
                (
                    name + "="
                )
            ) {

                cookieValue =
                    decodeURIComponent(
                        cookie.substring(
                            name.length + 1
                        )
                    );


                break;
            }
        }
    }


    return cookieValue;
}


const csrftoken =
    getCookie(
        "csrftoken"
    );


function setPreviewTextOrBarcode(barcodeSel, textSel, value, barcodeSvg) {
    const $barcode = $(barcodeSel);
    const $text = $(textSel);

    if (barcodeSvg) {
        $barcode.html(barcodeSvg).show();
        $text.hide();
    } else {
        $barcode.hide();
        $text.text(value || "-").show();
    }
}

function setPaymentStatus(balance) {
    const due = parseFloat(balance) || 0;

    $("#previewPaymentStatusBox")
        .text(due > 0 ? "DUE" : "PAID")
        .toggleClass("text-danger", due > 0)
        .toggleClass("text-success", due <= 0);
}


// ============================================================
// HOTEL TRANSACTION PREVIEW
// ============================================================

function showTransactionPreview(
    response,
    payload,
    paymentList
) {

    lastSavedTransactionId =
        response.tran_id ||
        null;


    // ========================================================
    // HELPERS
    // ========================================================

    function selectedText(
        selector
    ) {

        const $element =
            $(selector);


        if (
            !$element.length
        ) {

            return "-";
        }


        const text =
            $element
                .find(
                    "option:selected"
                )
                .text();


        if (
            !text ||
            !text.trim()
        ) {

            return "-";
        }


        return text.trim();
    }


    function safeText(
        value
    ) {

        if (
            value === null ||
            value === undefined ||
            value === ""
        ) {

            return "-";
        }


        return value;
    }


    function money(
        value
    ) {

        const amount =
            parseFloat(
                value
            ) || 0;


        return amount
            .toFixed(2);
    }


    function setInvoiceBarcode(
        $target,
        invoiceValue,
        barcodeSvg
    ) {

        if (!barcodeSvg) {

            $target.text(
                safeText(
                    invoiceValue
                )
            );

            return;
        }


        $target.html(
            barcodeSvg
        );
    }

    // ========================================================
    // INVOICE NO HIDE
    // ========================================================

    $("#previewInvoiceNoBarcode").hide();
    $("#previewInvoiceNoText").hide();


  

    // ========================================================
    // TRANSACTION INFORMATION
    // ========================================================

    $("#previewTranId")
        .text(
            safeText(
                response.tran_id
            )
        );


    $("#previewTranIdText")
        .text(
            "Transaction ID: " +
            safeText(
                response.tran_id
            )
        );


    $("#previewTranDate")
        .text(
            safeText(
                payload.tran_date
            )
        );


    $("#previewMainHead")
        .text(
            selectedText(
                "#transactionmainheads"
            )
        );


    $("#previewTransactionMethod")
        .text(
            selectedText(
                "#transaction_method"
            )
        );


    $("#previewTransactionGroup")
        .text(
            selectedText(
                "#tran_group"
            )
        );


    $("#previewTransactionWithMethod")
        .text(
            selectedText(
                "#transaction_with_method"
            )
        );


    $("#previewTransactionWith")
        .text(
            selectedText(
                "#transaction_with"
            )
        );


    $("#previewTransactionUser")
        .text(
            selectedText(
                "#transaction_with_user"
            )
        );


    $("#previewPaymentMethod")
        .text(
            selectedText(
                "#payment_method"
            )
        );


    // ========================================================
    // INVOICE
    // ========================================================

    setPreviewTextOrBarcode(

        "#previewInvoiceNoBarcode",

        "#previewInvoiceNoText",

        response.invoice_ref ||
        payload.invoice ||
        response.tran_id,

        response.invoice_barcode_svg ||
        payload.invoice_barcode_svg
    );


    $("#previewLocation")
        .text(
            selectedText(
                ".location-select"
            )
        );


    // ========================================================
    // HOTEL GUEST PREVIEW
    // ========================================================

    $("#previewGuestId")
        .text(
            safeText(
                response.guest_id ||
                payload.guest_id
            )
        );


    if (
        $("#previewGuestIdBarcode")
            .length
    ) {

        setPreviewTextOrBarcode(

            "#previewGuestIdBarcode",

            "#previewGuestId",

            response.guest_id ||
            payload.guest_id,

            response.guest_barcode_svg ||
            payload.guest_barcode_svg
        );
    }


    $("#previewGuestName")
        .text(
            safeText(
                payload.guest_name
            )
        );


    $("#previewGuestPhone")
        .text(
            safeText(
                payload.guest_phone
            )
        );


    $("#previewGuestAddress")
        .text(
            safeText(
                payload.guest_address
            )
        );


    // ========================================================
    // SR PREVIEW
    // ========================================================

    $("#previewSrId")
        .text(
            safeText(
                response.sr_id ||
                payload.referred_sr_id
            )
        );


    let srName =
        (
            $("#sr_name_display")
                .val() ||
            ""
        ).trim();


    let srId =
        response.sr_id ||
        payload.referred_sr_id ||
        "";


    if (!srName) {

        const selectedSrValue =
            $("#sr_lookup")
                .val();


        const selectedSrText =
            (
                $("#sr_lookup option:selected")
                    .text() ||
                ""
            ).trim();


        if (
            selectedSrValue &&
            selectedSrText &&
            !selectedSrText.includes(
                "Start Typing"
            ) &&
            selectedSrText !== "-"
        ) {

            srName =
                selectedSrText;
        }
    }


    $("#previewSrName")
        .text(
            srName || "-"
        );


    $("#previewSrId")
        .text(
            srId || "-"
        );


    // ========================================================
    // PRODUCT PREVIEW
    // ========================================================

    let rowsHtml =
        "";


    $("#selectedPaymentListPayment tr")
        .each(
            function (
                index
            ) {

                const $row =
                    $(this);


                const productId =
                    $row.data(
                        "product-id"
                    ) || "-";


                const productName =
                    (
                        $row
                            .find(
                                "td:eq(2)"
                            )
                            .text() ||
                        "-"
                    ).trim();


                const qty =
                    parseFloat(
                        $row
                            .find(
                                "td:eq(3)"
                            )
                            .text()
                    ) || 0;


                const mrp =
                    parseFloat(
                        $row
                            .find(
                                "td:eq(5)"
                            )
                            .text()
                    ) || 0;


                const total =
                    parseFloat(
                        $row
                            .find(
                                "td:eq(7)"
                            )
                            .text()
                    ) || 0;


                rowsHtml += `

                    <tr>

                        <td>
                            ${index + 1}
                        </td>

                        <td>
                            ${productId}
                        </td>

                        <td>
                            ${productName}
                        </td>

                        <td class="text-center">
                            ${qty}
                        </td>

                        <td class="text-end">
                            ${mrp.toFixed(2)}
                        </td>

                        <td class="text-end fw-semibold">
                            ${total.toFixed(2)}
                        </td>

                    </tr>
                `;
            }
        );


    if (!rowsHtml) {

        // success-এর পরে selected table clear হয়ে গেলে
        // paymentList payload থেকে preview বানাব

        if (
            Array.isArray(
                paymentList
            ) &&
            paymentList.length
        ) {

            paymentList.forEach(
                function (
                    item,
                    index
                ) {

                    let productId =
                        item[0] ||
                        "-";


                    let qty =
                        parseFloat(
                            item[1]
                        ) || 0;


                    let mrp =
                        parseFloat(
                            item[3]
                        ) || 0;


                    let total =
                        parseFloat(
                            item[5]
                        ) || 0;


                    rowsHtml += `

                        <tr>

                            <td>
                                ${index + 1}
                            </td>

                            <td>
                                ${productId}
                            </td>

                            <td>
                                ${productId}
                            </td>

                            <td class="text-center">
                                ${qty}
                            </td>

                            <td class="text-end">
                                ${mrp.toFixed(2)}
                            </td>

                            <td class="text-end fw-semibold">
                                ${total.toFixed(2)}
                            </td>

                        </tr>
                    `;
                }
            );
        }
    }


    if (!rowsHtml) {

        rowsHtml = `

            <tr>

                <td
                    colspan="6"
                    class="text-center text-muted py-3">

                    No transaction details found

                </td>

            </tr>
        `;
    }


    $("#previewTransactionRows")
        .html(
            rowsHtml
        );


    // ========================================================
    // BOTTOM GUEST NAME
    // ========================================================

    $("#previewBottomGuestName")
        .text(
            safeText(
                payload.guest_name
            )
        );


    // ========================================================
    // PAYMENT SUMMARY
    // ========================================================

    $("#previewInvoiceAmount")
        .text(
            money(
                payload.bill_amount
            )
        );


    $("#previewDiscount")
        .text(
            money(
                payload.discount
            )
        );


    $("#previewNetAmount")
        .text(
            money(
                payload.net_amount
            )
        );


    $("#previewAdvance")
        .text(
            money(
                payload.payment
            )
        );


    $("#previewDueCollection")
        .text(
            money(
                response.due_col ??
                payload.due_col
            )
        );


    $("#previewDueDiscount")
        .text(
            money(
                response.due_disc ??
                payload.due_disc
            )
        );


    $("#previewBalance")
        .text(
            money(
                payload.due
            )
        );


    setPaymentStatus(
        $("#previewBalance")
            .text()
    );


    // ========================================================
    // SHOW PREVIEW MODAL
    // ========================================================

    const modalElement =
        document.getElementById(
            "transactionPreviewModal"
        );


    if (!modalElement) {

        console.error(
            "transactionPreviewModal not found"
        );

        return;
    }


    if (
        typeof bootstrap ===
        "undefined" ||
        !bootstrap.Modal
    ) {

        console.error(
            "Bootstrap Modal JS is not loaded"
        );

        return;
    }


    let previewModal =
        bootstrap.Modal
            .getInstance(
                modalElement
            );


    if (!previewModal) {

        previewModal =
            new bootstrap.Modal(
                modalElement
            );
    }


        previewModal.show();
        alert("✅ Save successful!");

    // ========================================================
    // PRINT
    // ========================================================

    $("#openPrintableInvoiceBtn")
        .off(
            "click.hotelPrint"
        )
        .on(
            "click.hotelPrint",
            function () {

                let previewHtml =
                    $(
                        "#transactionPreviewModal"
                    ).prop(
                        "outerHTML"
                    );


                let styles =
                    "";


                $(
                    "link[rel='stylesheet']"
                ).each(
                    function () {

                        styles +=
                            `<link rel="stylesheet" href="${$(this).attr("href")}">`;
                    }
                );


                $("style")
                    .each(
                        function () {

                            styles +=
                                `<style>${$(this).html()}</style>`;
                        }
                    );


                let printWindow =
                    window.open(
                        "",
                        "_blank"
                    );


                if (!printWindow) {

                    alert(
                        "Please allow popup for printing."
                    );

                    return;
                }


                printWindow.document.write(`

                    <!DOCTYPE html>

                    <html>

                    <head>

                        <title>
                            Hotel Invoice
                        </title>

                        ${styles}

                        <style>

                            body {
                                background: #fff;
                                margin: 20px;
                            }

                            @page {
                                size: A4;
                                margin: 10mm;
                            }

                            @media print {

                                body {
                                    margin: 0;
                                }

                                .modal-backdrop,
                                .btn,
                                button {
                                    display: none !important;
                                }

                                #transactionPreviewModal {
                                    display: block !important;
                                    visibility: visible !important;
                                    position: static !important;
                                    width: 100% !important;
                                    box-shadow: none !important;
                                    border: none !important;
                                }

                            }

                        </style>

                    </head>

                    <body>

                        ${previewHtml}

                    </body>

                    </html>
                `);


                printWindow
                    .document
                    .close();


                printWindow
                    .focus();


                setTimeout(
                    function () {

                        printWindow.print();

                    },
                    500
                );
            }
        );
}