let mode = "save";

// ============================================================
// LOAD CHECK IN DETAILS
// ============================================================

function loadCheckInDetails() {

    // ========================================================
    // FILTER VALUES
    // ========================================================

    let search = $('#search').val() || '';

    let status = $('#filter_status').val() || '';

    let start_date = $('#start_date').val() || '';

    let end_date = $('#end_date').val() || '';

    let limit = $('#limit').val() || '50';


    // ========================================================
    // DEBUG
    // ========================================================

    console.log(
        'FILTER >>>',
        {
            search: search,
            status: status,
            start_date: start_date,
            end_date: end_date,
            limit: limit
        }
    );


    // ========================================================
    // AJAX
    // ========================================================

    $.ajax({

        url: '/check_in_details/load-check-in/',

        method: 'GET',

        data: {

            search: search,

            status: status,

            start_date: start_date,

            end_date: end_date,

            limit: limit

        },


        success: function(response) {

            console.log(
                'CHECK IN RESPONSE >>>',
                response
            );


            let data =
                response.check_in_details || [];


            let tbody = '';


            // =================================================
            // NO DATA
            // =================================================

            if (data.length === 0) {

                tbody = `

                    <tr>

                        <td
                            colspan="10"
                            class="text-center text-muted"
                        >
                            No Check In Details Found
                        </td>

                    </tr>

                `;


                $('#checkInTableBody').html(
                    tbody
                );


                return;

            }


            // =================================================
            // DATA LOOP
            // =================================================

            $.each(
                data,
                function(index, item) {


                    // ===========================================
                    // STATUS
                    // ===========================================

                    let statusBadge = '';


                    if (
                        String(item.status) === '1'
                    ) {

                        statusBadge =
                            '<span class="badge bg-success">Active</span>';

                    }

                    else {

                        statusBadge =
                            '<span class="badge bg-danger">Inactive</span>';

                    }


                    // ===========================================
                    // TABLE ROW
                    // ===========================================

                    tbody += `

                        <tr>

                            <td>
                                ${index + 1}
                            </td>

                            <td>
                                ${item.id || ''}
                            </td>

                            <td>
                                ${item.guest_name || ''}
                            </td>

                            <td>
                                ${item.bed_category || ''}
                            </td>

                            <td>
                                ${item.bed_no || ''}
                            </td>

                            <td>
                                ${item.check_in || ''}
                            </td>

                            <td>
                                ${item.check_out || ''}
                            </td>

                            <td>
                                ${statusBadge}
                            </td>

                            <td>

                                <button
                                    type="button"
                                    class="btn btn-sm btn-warning editBtn"
                                    data-id="${item.id}"
                                >
                                    Edit
                                </button>

                                <button
                                    type="button"
                                    class="btn btn-sm btn-danger deleteBtn"
                                    data-id="${item.id}"
                                >
                                    Delete
                                </button>

                            </td>

                        </tr>

                    `;

                }
            );


            // =================================================
            // SHOW DATA
            // =================================================

            $('#checkInTableBody').html(
                tbody
            );

        },


        error: function(xhr) {

            console.log(
                xhr.responseText
            );

            alert(
                'Error: ' + xhr.status
            );

        }

    });

}



// ============================================================
// FILTER BUTTON
// ============================================================

$(document).on(
    'click',
    '#filterBtn',
    function(e) {

        loadCheckInDetails();

    }
);


// ============================================================
// SEARCH ENTER
// ============================================================

$(document).on(
    'keyup',
    '#search',
    function(e) {

        if (e.key === 'Enter') {

            loadCheckInDetails();

        }

    }
);


// ============================================================
// STATUS CHANGE
// ============================================================

$(document).on(
    'change',
    '#filter_status',
    function() {

        loadCheckInDetails();

    }
);


// ============================================================
// LIMIT CHANGE
// ============================================================

$(document).on(
    'change',
    '#limit',
    function() {

        loadCheckInDetails();

    }
);


// ============================================================
// START DATE CHANGE
// ============================================================

$(document).on(
    'change',
    '#start_date',
    function() {

        let start_date =
            $('#start_date').val();

        let end_date =
            $('#end_date').val();


        if (
            start_date &&
            end_date &&
            start_date > end_date
        ) {

            alert(
                'Start Date cannot be greater than End Date'
            );

            $('#start_date').val('');

            return;

        }

    }
);


// ============================================================
// END DATE CHANGE
// ============================================================

$(document).on(
    'change',
    '#end_date',
    function() {

        let start_date =
            $('#start_date').val();

        let end_date =
            $('#end_date').val();


        if (
            start_date &&
            end_date &&
            end_date < start_date
        ) {

            alert(
                'End Date cannot be less than Start Date'
            );

            $('#end_date').val('');

            return;

        }

    }
);


// ============================================================
// CHECK IN DETAILS TABLE LOCAL SEARCH
// ============================================================

$(document).on(
    'keyup',
    '#checkInSearch',
    function() {

        let value = String(
            $(this).val() || ''
        ).toLowerCase();


        $('#checkInTableBody tr').each(
            function() {

                let rowText = String(
                    $(this).text() || ''
                ).toLowerCase();


                $(this).toggle(
                    rowText.indexOf(value) !== -1
                );

            }
        );

    }
);


// ============================================================
// PAGE INITIAL LOAD
// ============================================================

$(document).ready(
    function() {

        console.log(
            'CHECK IN DETAILS JS LOADED'
        );


        // Hotel Guest dropdown
        loadGuestDropdown();


        // Check In Details table
        loadCheckInDetails();

    }
);