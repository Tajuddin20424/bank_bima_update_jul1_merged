$(document).ready(function () {

    console.log("Hotel Payment List JS Loaded");


    // =========================================================
    // 1. LOAD GUEST FILTER
    // =========================================================

    function loadGuestFilter() {

        $.ajax({
            url: window.APP_URLS.HOTEL_GUEST_FILTER_URL,
            type: "GET",
            dataType: "json",

            success: function (response) {

                let $guest = $('#guest_filter');

                $guest.empty();

                $guest.append(
                    '<option value="">All Guest</option>'
                );


                let rows =
                    response.results ||
                    response.guests ||
                    response.hotel_guests ||
                    [];


                $.each(rows, function (index, guest) {

                    let id =
                        guest.id ||
                        guest.user_db_id ||
                        '';

                    let name =
                        guest.guest_name ||
                        guest.user_name ||
                        guest.name ||
                        '';


                    $guest.append(
                        `<option value="${id}">
                            ${name}
                        </option>`
                    );

                });

            },

            error: function (xhr) {

                console.log(
                    "Guest Filter Load Error:",
                    xhr.responseText
                );

            }

        });

    }



    // =========================================================
    // 2. LOAD SR FILTER
    // =========================================================

    function loadSrFilter() {

        $.ajax({

            url: window.APP_URLS.HOTEL_SR_FILTER_URL,
            type: "GET",
            dataType: "json",

            success: function (response) {

                let $sr = $('#sr_filter');

                $sr.empty();

                $sr.append(
                    '<option value="">All SR</option>'
                );


                let rows =
                    response.results ||
                    response.sr ||
                    response.srs ||
                    [];


                $.each(rows, function (index, item) {

                    let id =
                        item.id ||
                        item.sr_id ||
                        '';

                    let name =
                        item.name ||
                        item.sr_name ||
                        '';


                    $sr.append(
                        `<option value="${id}">
                            ${name}
                        </option>`
                    );

                });

            },

            error: function (xhr) {

                console.log(
                    "SR Filter Load Error:",
                    xhr.responseText
                );

            }

        });

    }



    // =========================================================
    // 3. LOAD TRANSACTION BY FILTER
    // =========================================================

    function loadTranByFilter() {

        $.ajax({

            url: window.APP_URLS.HOTEL_TRAN_BY_FILTER_URL,
            type: "GET",
            dataType: "json",

            success: function (response) {

                let $select =
                    $('#tran_by_filter');

                $select.empty();

                $select.append(
                    '<option value="">All Transaction By</option>'
                );


                let rows =
                    response.results ||
                    response.transaction_by ||
                    response.tran_by ||
                    [];


                $.each(rows, function (index, item) {

                    let value =
                        item.id ||
                        item.tran_by ||
                        item.value ||
                        '';

                    let name =
                        item.name ||
                        item.tran_by_name ||
                        item.tran_by ||
                        item.text ||
                        value;


                    $select.append(
                        `<option value="${value}">
                            ${name}
                        </option>`
                    );

                });

            },

            error: function (xhr) {

                console.log(
                    "Transaction By Filter Load Error:",
                    xhr.responseText
                );

            }

        });

    }



    // =========================================================
    // 4. LOAD HOTEL PAYMENT LIST
    // =========================================================

    function loadHotelPaymentList() {

        let search =
            $('#supplierSearch').val() || '';

        let status =
            $('#status').val() || '';

        let startDate =
            $('#start_date').val() || '';

        let endDate =
            $('#end_date').val() || '';

        let perPage =
            $('#perPage').val() || 50;

        let guestId =
            $('#guest_filter').val() || '';

        let srId =
            $('#sr_filter').val() || '';

        let tranBy =
            $('#tran_by_filter').val() || '';


        $.ajax({

            url: window.APP_URLS.PAYMENT_LIST_URL,

            type: "GET",

            dataType: "json",

            data: {

                search: search,

                status: status,

                start_date: startDate,

                end_date: endDate,

                per_page: perPage,

                guest_id: guestId,

                sr_id: srId,

                tran_by: tranBy
            },


            beforeSend: function () {

                $('#paymentListTableBody').html(`

                    <tr>

                        <td
                            colspan="16"
                            class="text-center">

                            Loading...

                        </td>

                    </tr>

                `);

            },


            success: function (response) {

                console.log(
                    "Hotel Payment List Response:",
                    response
                );


                let rows =
                    response.results ||
                    response.payments ||
                    response.payment_list ||
                    response.data ||
                    [];


                let html = '';

                let totalDue = 0;


                if (!rows.length) {

                    html = `

                        <tr>

                            <td
                                colspan="16"
                                class="text-center text-muted">

                                No Data Found

                            </td>

                        </tr>

                    `;


                    $('#paymentListTableBody')
                        .html(html);

                    $('#total_due')
                        .val('0.00');

                    return;
                }



                $.each(
                    rows,
                    function (index, row) {


                        let tranId =
                            row.tran_id ||
                            row.transaction_id ||
                            '';


                        let invoiceRef =
                            row.invoice_ref ||
                            row.invoice_no ||
                            row.invoice ||
                            '';


                        let tranDate =
                            row.tran_date ||
                            row.date ||
                            '';


                        let supplier =
                            row.supplier_name ||
                            row.supplier ||
                            '';


                        let guest =
                            row.guest_name ||
                            row.user_name ||
                            row.guest ||
                            '';


                        let sr =
                            row.sr_name ||
                            row.sr ||
                            '';


                        let tranBy =
                            row.tran_by_name ||
                            row.tran_by ||
                            '';


                        let bill =
                            parseFloat(
                                row.bill ||
                                row.bill_amount ||
                                row.invoice_amount ||
                                0
                            );


                        let discount =
                            parseFloat(
                                row.discount || 0
                            );


                        let net =
                            parseFloat(
                                row.net ||
                                row.net_amount ||
                                0
                            );


                        let advance =
                            parseFloat(
                                row.advance ||
                                row.advanced ||
                                0
                            );


                        let dueCol =
                            parseFloat(
                                row.due_col ||
                                row.due_collection ||
                                0
                            );


                        let dueDisc =
                            parseFloat(
                                row.due_disc ||
                                row.due_discount ||
                                0
                            );


                        let due =
                            parseFloat(
                                row.due ||
                                row.balance ||
                                0
                            );


                        totalDue += due;



                        let dbId =
                            row.id || '';


                        html += `

                            <tr>

                                <td>
                                    ${index + 1}
                                </td>


                                <td>
                                    ${tranId}
                                </td>


                                <td>
                                    ${invoiceRef}
                                </td>


                                <td>
                                    ${tranDate}
                                </td>


                                <td>
                                    ${supplier}
                                </td>


                                <td>
                                    ${guest}
                                </td>


                                <td>
                                    ${sr}
                                </td>


                                <td>
                                    ${tranBy}
                                </td>


                                <td class="text-end">
                                    ${bill.toFixed(2)}
                                </td>


                                <td class="text-end">
                                    ${discount.toFixed(2)}
                                </td>


                                <td class="text-end">
                                    ${net.toFixed(2)}
                                </td>


                                <td class="text-end">
                                    ${advance.toFixed(2)}
                                </td>


                                <td class="text-end">
                                    ${dueCol.toFixed(2)}
                                </td>


                                <td class="text-end">
                                    ${dueDisc.toFixed(2)}
                                </td>


                                <td class="text-end">
                                    ${due.toFixed(2)}
                                </td>


                                <td class="text-center">

                                    <a
                                        href="/hotel/payment/edit/${dbId}/"
                                        class="btn btn-warning btn-sm">

                                        Edit

                                    </a>

                                </td>

                            </tr>

                        `;

                    }
                );


                $('#paymentListTableBody')
                    .html(html);


                /*
                Backend total_due দিলে সেটা নেব।
                না দিলে visible rows থেকে calculate হবে।
                */

                let backendTotalDue =
                    response.total_due;


                if (
                    backendTotalDue !== undefined &&
                    backendTotalDue !== null
                ) {

                    $('#total_due').val(
                        parseFloat(
                            backendTotalDue || 0
                        ).toFixed(2)
                    );

                } else {

                    $('#total_due').val(
                        totalDue.toFixed(2)
                    );

                }

            },


            error: function (xhr) {

                console.log(
                    "Hotel Payment List Error:",
                    xhr.responseText
                );


                $('#paymentListTableBody').html(`

                    <tr>

                        <td
                            colspan="16"
                            class="text-center text-danger">

                            Failed to load hotel payment list

                        </td>

                    </tr>

                `);

            }

        });

    }



    // =========================================================
    // 5. FILTER BUTTON
    // =========================================================

    $('#hotelFilterForm').on(
        'submit',
        function (e) {

            e.preventDefault();

            loadHotelPaymentList();

        }
    );



    // =========================================================
    // 6. FILTER COMBO CHANGE
    // =========================================================

    $(document).on(
        'change',
        '#guest_filter, #sr_filter, #tran_by_filter',
        function () {

            loadHotelPaymentList();

        }
    );



    // =========================================================
    // 7. PER PAGE CHANGE
    // =========================================================

    $(document).on(
        'change',
        '#perPage',
        function () {

            loadHotelPaymentList();

        }
    );



    // =========================================================
    // 8. ENTER SEARCH
    // =========================================================

    $('#supplierSearch').on(
        'keypress',
        function (e) {

            if (e.which === 13) {

                e.preventDefault();

                loadHotelPaymentList();

            }

        }
    );



    // =========================================================
    // 9. FIFO PAYMENT
    // =========================================================

    $('#fifo_pay_btn').on(
        'click',
        function () {


            let payment =
                parseFloat(
                    $('#fifo_payment').val()
                ) || 0;


            if (payment <= 0) {

                alert(
                    'Please enter payment amount'
                );

                return;
            }


            let guestId =
                $('#guest_filter').val() || '';


            if (!guestId) {

                alert(
                    'Please select Guest first'
                );

                return;
            }


            $.ajax({

                url:
                    window.APP_URLS.FIFO_PAYMENT_URL,

                type:
                    "POST",

                data: {

                    guest_id:
                        guestId,

                    payment:
                        payment,

                    csrfmiddlewaretoken:
                        getCookie('csrftoken')
                },


                success: function (response) {


                    if (
                        response.success ||
                        response.status === 'success'
                    ) {

                        alert(
                            response.message ||
                            'Payment completed successfully'
                        );


                        $('#fifo_payment')
                            .val('');


                        loadHotelPaymentList();

                    } else {

                        alert(
                            response.message ||
                            'Payment failed'
                        );

                    }

                },


                error: function (xhr) {

                    console.log(
                        "FIFO Payment Error:",
                        xhr.responseText
                    );


                    alert(
                        'Payment failed'
                    );

                }

            });

        }
    );



    // =========================================================
    // 10. CSRF
    // =========================================================

    function getCookie(name) {

        let cookieValue = null;


        if (
            document.cookie &&
            document.cookie !== ''
        ) {

            let cookies =
                document.cookie.split(';');


            for (
                let i = 0;
                i < cookies.length;
                i++
            ) {

                let cookie =
                    cookies[i].trim();


                if (
                    cookie.substring(
                        0,
                        name.length + 1
                    ) ===
                    (
                        name + '='
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



    // =========================================================
    // 11. PAGE INITIAL LOAD
    // =========================================================

    loadGuestFilter();

    loadSrFilter();

    loadTranByFilter();

    loadHotelPaymentList();

});