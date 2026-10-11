$(document).ready(function () {

    console.log("🚀 SR & Product Select2 Engine Active.");


    /* =====================================================
       COMMON SELECT2 SEARCH FOCUS
    ===================================================== */

    function focusOpenedSelect2Search() {

        setTimeout(function () {

            let searchField = document.querySelector(
                ".select2-container--open .select2-search__field"
            );

            if (searchField) {
                searchField.focus();
                searchField.select();
            }

        }, 100);
    }



    /* =====================================================
       SR AGENT SEARCH AUTO-COMPLETE
    ===================================================== */

    $(".select2-sr").select2({

        ajax: {

            url: window.APP_URLS.SR_AUTOCOMPLETE_URL,

            dataType: "json",

            delay: 250,

            data: function (params) {

                return {
                    q: params.term || ""
                };
            },

            processResults: function (data) {

                let results = data.results || [];

                /*
                    SR না থাকলে এই option দেখাবে
                */

                results.unshift({
                    id: "__blank_sr__",
                    text: "-- No SR --",
                    is_blank_sr: true
                });

                return {
                    results: results
                };
            },

            cache: true
        },

        placeholder: "-- Start Typing SR ID / Name --",

        minimumInputLength: 0,

        allowClear: true,

        width: "100%",

        dropdownParent: $("#sr_lookup").closest(".card"),

        dropdownCssClass: "diagnosis-reference-dropdown"
    });



    /* =====================================================
       SR SELECT
    ===================================================== */

    $("#sr_lookup")
        .off("select2:select")
        .on("select2:select", function (e) {

            let data = e.params.data;


            /*
                NO SR selected
            */

            if (
                data.is_blank_sr ||
                data.id === "__blank_sr__"
            ) {

                $("#sr_lookup")
                    .val(null)
                    .trigger("change");

                $("#sr_id").val("");

                $("#sr_name_display").val("");

                $("#sr_lookup").select2("close");


                /*
                    Product Search open
                */

                setTimeout(function () {

                    $("#productSearch").select2("open");

                    focusOpenedSelect2Search();

                }, 100);

                return;
            }


            /*
                Selected SR information
            */

            $("#sr_id").val(data.id);

            $("#sr_name_display").val(
                data.name_display ||
                data.text ||
                ""
            );


            $("#sr_lookup").select2("close");


            /*
                Move to Product Search
            */

            setTimeout(function () {

                $("#productSearch").select2("open");

                focusOpenedSelect2Search();

            }, 300);

        });



    /* =====================================================
       SR CLEAR
    ===================================================== */

    $("#sr_lookup")
        .off("select2:clear")
        .on("select2:clear", function () {

            $("#sr_id").val("");

            $("#sr_name_display").val("");

        });



    /* =====================================================
       SR CLICK / FOCUS -> OPEN LIST
    ===================================================== */

    $("#sr_lookup")
        .off("focus.srOpenList click.srOpenList")
        .on(
            "focus.srOpenList click.srOpenList",
            function () {

                const $field = $(this);

                if (
                    $field.data("select2") &&
                    !$field.data("select2").isOpen()
                ) {

                    $field.select2("open");
                }
            }
        );



    /* =====================================================
       PRODUCT RESULT DESIGN
    ===================================================== */

    function formatProductResult(product) {

        if (product.loading) {
            return product.text;
        }


        let productName =
            product.name ||
            product.text ||
            "-";


        let categoryName =
            product.category_name ||
            "";


        let quantity =
            product.quantity ??
            product.qty ??
            product.stock_quantity ??
            0;


        let mrp =
            parseFloat(product.mrp) || 0;


        return $(`
            <div class="product-search-row">

                <div class="product-search-name">
                    ${productName}
                </div>

                <div class="product-search-generic">
                    ${categoryName}
                </div>

                <div class="product-search-qty">
                    ${quantity}
                </div>

                <div class="product-search-mrp">
                    ${mrp.toFixed(2)}
                </div>

            </div>
        `);
    }



    /* =====================================================
       SELECTED PRODUCT DISPLAY
    ===================================================== */

    function formatSelectedProduct(product) {

        if (!product.id) {
            return product.text;
        }

        return (
            product.name ||
            product.text ||
            ""
        );
    }



    /* =====================================================
       PRODUCT SEARCH AUTO-COMPLETE
    ===================================================== */

    $(".select2-product").select2({

        ajax: {

            url: window.APP_URLS.PRODUCT_SEARCH_URL,

            dataType: "json",

            delay: 250,


            data: function (params) {

                return {

                    q: params.term || "",

                    tran_main_head_id:
                        $("#transactionmainheads").val(),

                    tran_group_id:
                        $("#tran_group").val()
                };
            },


            processResults: function (data) {

                return {

                    results: $.map(
                        data.results || [],

                        function (item) {

                            return {

                                id: item.id,

                                text:
                                    item.name ||
                                    item.text ||
                                    "",

                                name:
                                    item.name ||
                                    item.text ||
                                    "",

                                generic_name:
                                    item.generic_name ||
                                    item.generic ||
                                    item.genericName ||
                                    "",

                                quantity:
                                    item.quantity ??
                                    item.qty ??
                                    item.stock_quantity ??
                                    0,

                                cp:
                                    item.cp || 0,

                                mrp:
                                    item.mrp || 0,

                                category_name:
                                    item.category_name || "",

                                manufacturer:
                                    item.manufacturer || "",

                                form:
                                    item.form || ""
                            };
                        }
                    )
                };
            },

            cache: true
        },


        placeholder:
            "-- Start Typing Product ID / Name --",

        minimumInputLength: 0,

        allowClear: true,

        width: "100%",

        dropdownParent:
            $("#productSearch").closest(".card-body"),

        dropdownCssClass:
            "diagnosis-product-dropdown",

        templateResult:
            formatProductResult,

        templateSelection:
            formatSelectedProduct,

        escapeMarkup: function (markup) {
            return markup;
        },


        language: {

            searching: function () {
                return "Searching products...";
            },

            noResults: function () {
                return "No product found";
            }
        }

    });



    /* =====================================================
       PRODUCT SELECT
    ===================================================== */

    $("#productSearch")
        .off("select2:select")
        .on("select2:select", function (e) {

            let data = e.params.data;


            let qty =
                parseFloat(
                    $("#quantity").val()
                ) || 1;


            let cp =
                parseFloat(data.cp) || 0;


            let mrp =
                parseFloat(data.mrp) || 0;


            let total =
                qty * mrp;


            /*
                Set product information
            */

            $("#productid").val(
                data.id
            );

            $("#cp").val(
                cp
            );

            $("#mrp").val(
                mrp
            );

            $("#quantity").val(
                qty
            );

            $("#total").val(
                total.toFixed(2)
            );


            $("#productSearch")
                .select2("close");


            /*
                Focus Add Product Button
            */

            setTimeout(function () {

                let addButton =
                    document.getElementById(
                        "addProductBtn"
                    );

                if (addButton) {

                    addButton.scrollIntoView({
                        behavior: "smooth",
                        block: "center"
                    });

                    addButton.focus();
                }

            }, 300);

        });



    /* =====================================================
       PRODUCT CLEAR
    ===================================================== */

    $("#productSearch")
        .off("select2:clear")
        .on("select2:clear", function () {

            $("#productid").val("");

            $("#cp").val("0");

            $("#mrp").val("0");

            $("#total").val("");

        });



    /* =====================================================
       PRODUCT CLICK / FOCUS -> OPEN LIST
    ===================================================== */

    $("#productSearch")
        .off(
            "focus.productOpenList click.productOpenList"
        )
        .on(
            "focus.productOpenList click.productOpenList",
            function () {

                const $field = $(this);

                if (
                    $field.data("select2") &&
                    !$field.data("select2").isOpen()
                ) {

                    $field.select2("open");
                }
            }
        );



    /* =====================================================
       PRODUCT DROPDOWN HEADER
    ===================================================== */

    function addProductDropdownHeader() {

        const productSelect2 =
            $("#productSearch").data("select2");


        if (
            !productSelect2 ||
            !productSelect2.$dropdown
        ) {
            return;
        }


        const $productDropdown =
            productSelect2.$dropdown;


        const $results =
            $productDropdown.find(
                ".select2-results"
            );


        if (!$results.length) {
            return;
        }


        /*
            Header already থাকলে
            আবার add হবে না
        */

        if (
            $results
                .find(".product-search-header")
                .length
        ) {
            return;
        }


        const header = `

            <div class="product-search-header">

                <div>
                    Product Name
                </div>

                <div>
                    Category
                </div>

                <div>
                    Qty
                </div>

                <div>
                    MRP
                </div>

            </div>
        `;


        $results.prepend(header);
    }



    /* =====================================================
       PRODUCT DROPDOWN WIDTH
    ===================================================== */

    function resizeProductDropdown() {

        const productSelect2 =
            $("#productSearch").data("select2");


        const productPanel =
            $("#productSearch")
                .closest(
                    ".diagnosis-product-entry-panel"
                );


        const productWidth =
            productPanel
                .find(".card")
                .outerWidth();


        if (
            !productSelect2 ||
            !productSelect2.$dropdown ||
            !productWidth
        ) {
            return;
        }


        productSelect2
            .$dropdown
            .parent()
            .css({

                left: "0px",

                width:
                    productWidth + "px",

                minWidth: "0",

                maxWidth:
                    productWidth + "px"
            });


        productSelect2
            .$dropdown
            .css({

                width:
                    productWidth + "px",

                minWidth: "0",

                maxWidth:
                    productWidth + "px"
            });
    }



    /* =====================================================
       SR DROPDOWN WIDTH
    ===================================================== */

    function resizeSRDropdown() {

        const referenceSelect2 =
            $("#sr_lookup").data("select2");


        const referenceCard =
            $("#sr_lookup").closest(".card");


        const referenceWidth =
            referenceCard.outerWidth();


        if (
            !referenceSelect2 ||
            !referenceSelect2.$dropdown ||
            !referenceWidth
        ) {
            return;
        }


        referenceSelect2
            .$dropdown
            .closest(".select2-container")
            .css({

                left: "0px",

                width:
                    referenceWidth + "px",

                minWidth: "0",

                maxWidth:
                    referenceWidth + "px"
            });


        referenceSelect2
            .$dropdown
            .parent()
            .css({

                left: "0px",

                width:
                    referenceWidth + "px",

                minWidth: "0",

                maxWidth:
                    referenceWidth + "px"
            });


        referenceSelect2
            .$dropdown
            .css({

                width:
                    referenceWidth + "px",

                minWidth: "0",

                maxWidth:
                    referenceWidth + "px"
            });
    }



    /* =====================================================
       PRODUCT DROPDOWN OPEN
    ===================================================== */

    $(document)
        .off("select2:open.productHeader")
        .on(
            "select2:open.productHeader",
            function (e) {

                if (
                    $(e.target).attr("id") !==
                    "productSearch"
                ) {
                    return;
                }


                setTimeout(function () {

                    resizeProductDropdown();

                    addProductDropdownHeader();

                }, 50);

            }
        );



    /* =====================================================
       SR DROPDOWN OPEN
    ===================================================== */

    $(document)
        .off("select2:open.srDropdownWidth")
        .on(
            "select2:open.srDropdownWidth",
            function (e) {

                if (
                    $(e.target).attr("id") !==
                    "sr_lookup"
                ) {
                    return;
                }


                setTimeout(function () {

                    resizeSRDropdown();

                }, 50);

            }
        );



    /* =====================================================
       SELECT2 OPEN -> SEARCH INPUT FOCUS
    ===================================================== */

    $(document)
        .off("select2:open.srProductSelect2")
        .on(
            "select2:open.srProductSelect2",
            function () {

                focusOpenedSelect2Search();

            }
        );

});