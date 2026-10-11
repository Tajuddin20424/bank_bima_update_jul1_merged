let mode = "save";

// ============================================================
// LOAD BED CATEGORY
// ============================================================

function loadCategoryDropdown() {

    $.ajax({

        url: '/bed_category/get/',

        method: 'GET',


        success: function(response) {

            let categories =
                response.bed_categories || [];


            let html =
                '<option value="">Select Category</option>';


            $.each(categories, function(index, category) {

                if (String(category.status) === '1') {

                    html += `

                        <option value="${category.id}">

                            ${category.name}

                        </option>

                    `;

                }

            });


            $('#category_id').html(html);

        },


        error: function(xhr) {

            console.log(
                xhr.responseText
            );


            alert(
                'Failed to load bed categories.'
            );

        }

    });

}


// ============================================================
// CATEGORY WISE BED OCCUPANCY
// ============================================================

function loadCategorySummary(response) {


    let categories =
        response.category_summary || [];


    let tbody = '';


    // ========================================================
    // NORMAL CATEGORY
    // ========================================================

    $.each(categories, function(index, category) {


        tbody += `

            <tr>

                <td class="fw-bold">

                    ${category.category_name || ''}

                </td>


                <td
                    class="
                        text-center
                        text-success
                        fw-bold
                    "
                >

                    ${category.total_vacant || 0}

                </td>


                <td
                    class="
                        text-center
                        text-danger
                        fw-bold
                    "
                >

                    ${category.total_occupied || 0}

                </td>


                <td
                    class="
                        text-center
                        text-primary
                        fw-bold
                    "
                >

                    ${category.total_bed || 0}

                </td>

            </tr>

        `;

    });


    // ========================================================
    // NO CATEGORY
    // ========================================================

    if (categories.length === 0) {

        tbody += `

            <tr>

                <td
                    colspan="4"
                    class="text-center text-muted"
                >

                    No active category found.

                </td>

            </tr>

        `;

    }


    // ========================================================
    // NORMAL TOTAL
    // ========================================================

    tbody += `

        <tr class="table-light">

            <td class="fw-bold">

                Total

            </td>


            <td
                class="
                    text-center
                    text-success
                    fw-bold
                "
            >

                ${response.total_vacant || 0}

            </td>


            <td
                class="
                    text-center
                    text-danger
                    fw-bold
                "
            >

                ${response.total_occupied || 0}

            </td>


            <td
                class="
                    text-center
                    text-primary
                    fw-bold
                "
            >

                ${response.normal_total_bed || 0}

            </td>

        </tr>

    `;


    // ========================================================
    // SPACE
    // ========================================================

    tbody += `

        <tr>

            <td
                colspan="4"
                style="
                    height: 12px;
                    background: #f8f9fa;
                "
            >
            </td>

        </tr>

    `;


    // ========================================================
    // TEMP
    // TEMP VACANT + OCCUPIED + TOTAL
    // ========================================================

    tbody += `

        <tr class="table-warning">

            <td class="fw-bold">

                TEMP

            </td>


            <td
                class="
                    text-center
                    text-success
                    fw-bold
                "
            >

                ${response.temp_vacant || 0}

            </td>


            <td
                class="
                    text-center
                    text-danger
                    fw-bold
                "
            >

                ${response.temp_occupied || 0}

            </td>


            <td
                class="
                    text-center
                    fw-bold
                "
            >

                ${response.temp_total || 0}

            </td>

        </tr>

    `;


    // ========================================================
    // ALL BEDS
    // ========================================================

    tbody += `

        <tr class="table-dark">

            <td class="fw-bold">

                All Beds

            </td>


            <td
                class="
                    text-center
                    fw-bold
                "
            >

                ${response.all_vacant || 0}

            </td>


            <td
                class="
                    text-center
                    fw-bold
                "
            >

                ${response.all_occupied || 0}

            </td>


            <td
                class="
                    text-center
                    fw-bold
                "
            >

                ${response.total_bed || 0}

            </td>

        </tr>

    `;


    // ========================================================
    // SHOW SUMMARY
    // ========================================================

    $('#categorySummaryBody').html(
        tbody
    );

}


// ============================================================
// RENDER BED INFO LIST
// All List / Vacant Only / Occupied List work inside this table.
// Category Wise Bed Occupancy summary is not changed by this filter.
// ============================================================

function renderBedInfoTable(data) {

    let filteredData = data || [];

    if (currentBedFilter === 'vacant') {
        filteredData = filteredData.filter(function(bed) {
            return String(bed.occupancy || '').toLowerCase() === 'vacant';
        });
    }

    else if (currentBedFilter === 'occupied') {
        filteredData = filteredData.filter(function(bed) {
            return String(bed.occupancy || '').toLowerCase() === 'occupied';
        });
    }

    let tbody = '';

    if (filteredData.length === 0) {
        tbody = `
            <tr>
                <td colspan="7" class="text-center text-muted">
                    No Bed Info Found
                </td>
            </tr>
        `;

        $('#tableBody').html(tbody);
        return;
    }

    $.each(filteredData, function(index, bed) {

        let occupancyBadge = '';

        if (bed.occupancy === 'occupied') {
            occupancyBadge = '<span class="badge bg-danger">Occupied</span>';
        }
        else if (bed.occupancy === 'not_available') {
            occupancyBadge = '<span class="badge bg-secondary">Not Available</span>';
        }
        else {
            occupancyBadge = '<span class="badge bg-success">Vacant</span>';
        }

        let statusBadge = '';

        if (String(bed.status) === '1') {
            statusBadge = '<span class="badge bg-success">Active</span>';
        }
        else {
            statusBadge = '<span class="badge bg-danger">Inactive</span>';
        }

        tbody += `
            <tr>
                <td>${index + 1}</td>
                <td>${bed.id}</td>
                <td>${bed.category_name || ''}</td>
                <td>${bed.bed_no || ''}</td>
                <td>${occupancyBadge}</td>
                <td>${statusBadge}</td>
                <td>
                    <button
                        type="button"
                        class="btn btn-sm btn-warning editBtn"
                        data-id="${bed.id}"
                    >
                        Edit
                    </button>

                    <button
                        type="button"
                        class="btn btn-sm btn-danger deleteBtn"
                        data-id="${bed.id}"
                    >
                        Delete
                    </button>
                </td>
            </tr>
        `;
    });

    $('#tableBody').html(tbody);
}


// ============================================================
// LOAD BED INFO
// ============================================================

function loadBedInfo(category_id = '') {

    $.ajax({

        url: '/bed_info/get/',
        method: 'GET',

        data: {
            category_id: category_id
        },

        success: function(response) {

            // Keep the existing category-wise summary flow unchanged.
            loadCategorySummary(response);

            // Save the current API result so radio filters do not call
            // another endpoint and do not change CRUD/backend flow.
            currentBedData = response.bed_info || [];

            renderBedInfoTable(currentBedData);
        },

        error: function(xhr) {

            console.log(xhr.responseText);
            alert('Error: ' + xhr.status);
        }

    });
}


// ============================================================
// BED INFO LIST FILTER
// ============================================================

$(document).on(
    'change',
    '.bedListFilter',
    function() {

        currentBedFilter = $(this).val() || 'all';
        renderBedInfoTable(currentBedData);
    }
);


// ============================================================
// DOCUMENT READY
// ============================================================

$(document).ready(function() {


    // ========================================================
    // LOAD CATEGORY
    // ========================================================

    loadCategoryDropdown();


    // ========================================================
    // LOAD BED INFO
    // ========================================================

    loadBedInfo();


    // ========================================================
    // CATEGORY CHANGE
    // ========================================================

    $('#category_id').on(
        'change',
        function() {


            let category_id =
                $(this).val();


            loadBedInfo(
                category_id
            );

        }
    );


    // ========================================================
    // OCCUPANCY CHANGE
    // ========================================================

    $('#occupancy').on(
        'change',
        function() {


            let occupancy =
                $(this).val();


            if (
                occupancy === 'not_available'
            ) {

                alert(
                    'Not Available'
                );

            }

        }
    );


    // ========================================================
    // SAVE / UPDATE
    // ========================================================

    $('#saveBtn').on(
        'click',
        function(e) {


            e.preventDefault();


            // =================================================
            // GET VALUES
            // =================================================

            let id =
                $('#id').val();


            let category_id =
                $('#category_id').val();


            let bed_no =
                $('#bed_no').val();


            let occupancy =
                $('#occupancy').val();


            let status =
                $('#status').val();


            // =================================================
            // VALIDATION
            // =================================================

            if (
                !category_id ||
                !bed_no
            ) {

                alert(
                    'Category and Bed No are required'
                );

                return;

            }


            // =================================================
            // SAVE
            // =================================================

            if (mode === 'save') {


                $.ajax({

                    url:
                        '/bed_info/save/',

                    type:
                        'POST',


                    headers: {

                        'X-CSRFToken':
                            csrftoken

                    },


                    data: {

                        category_id:
                            category_id,

                        bed_no:
                            bed_no,

                        occupancy:
                            occupancy,

                        status:
                            status

                    },


                    success: function(response) {


                        alert(
                            response.message
                        );


                        if (
                            response.status === 'success'
                        ) {


                            let selectedCategory =
                                category_id;


                            // =================================
                            // CLEAR FORM
                            // =================================

                            $('#form')[0].reset();


                            $('#id').val('');


                            $('#occupancy').val(
                                'vacant'
                            );


                            mode =
                                "save";


                            $('#saveBtn').text(
                                'Save'
                            );


                            // =================================
                            // KEEP CATEGORY SELECTED
                            // =================================

                            $('#category_id').val(
                                selectedCategory
                            );


                            // =================================
                            // RELOAD
                            // =================================

                            loadBedInfo(
                                selectedCategory
                            );

                        }

                    },


                    error: function(xhr) {

                        console.log(
                            xhr.responseText
                        );


                        alert(
                            'Error: ' +
                            xhr.status
                        );

                    }

                });

            }


            // =================================================
            // UPDATE
            // =================================================

            else if (
                mode === 'update'
            ) {


                $.ajax({

                    url:
                        '/bed_info/update/',

                    type:
                        'POST',


                    headers: {

                        'X-CSRFToken':
                            csrftoken

                    },


                    data: {

                        id:
                            id,

                        category_id:
                            category_id,

                        bed_no:
                            bed_no,

                        occupancy:
                            occupancy,

                        status:
                            status

                    },


                    success: function(response) {


                        alert(
                            response.message
                        );


                        if (
                            response.status === 'success'
                        ) {


                            let selectedCategory =
                                category_id;


                            // =================================
                            // CLEAR FORM
                            // =================================

                            $('#form')[0].reset();


                            $('#id').val('');


                            $('#occupancy').val(
                                'vacant'
                            );


                            mode =
                                "save";


                            $('#saveBtn').text(
                                'Save'
                            );


                            // =================================
                            // KEEP CATEGORY SELECTED
                            // =================================

                            $('#category_id').val(
                                selectedCategory
                            );


                            // =================================
                            // RELOAD
                            // =================================

                            loadBedInfo(
                                selectedCategory
                            );

                        }

                    },


                    error: function(xhr) {

                        console.log(
                            xhr.responseText
                        );


                        alert(
                            'Error: ' +
                            xhr.status
                        );

                    }

                });

            }

        }
    );


    // ========================================================
    // CLEAR
    // ========================================================

    $('#clearBtn').on(
        'click',
        function(e) {


            e.preventDefault();


            $('#form')[0].reset();


            $('#id').val('');


            $('#occupancy').val(
                'vacant'
            );


            mode =
                "save";


            $('#saveBtn').text(
                'Save'
            );


            loadBedInfo();

        }
    );

});


// ============================================================
// EDIT BED INFO
// ============================================================

$(document).on(
    'click',
    '.editBtn',
    function(e) {


        e.preventDefault();


        let id =
            $(this).data('id');


        $.ajax({

            url:
                '/bed_info/get/',

            method:
                'GET',


            success: function(response) {


                let data =
                    response.bed_info || [];


                let bed =
                    data.find(
                        function(item) {

                            return (
                                String(item.id) ===
                                String(id)
                            );

                        }
                    );


                if (!bed) {

                    alert(
                        'Bed Info not found'
                    );

                    return;

                }


                // =============================================
                // SET FORM DATA
                // =============================================

                $('#id').val(
                    bed.id
                );


                $('#category_id').val(
                    bed.category_id
                );


                $('#bed_no').val(
                    bed.bed_no
                );


                $('#occupancy').val(
                    bed.occupancy || 'vacant'
                );


                $('#status').val(
                    String(bed.status)
                );


                // =============================================
                // UPDATE MODE
                // =============================================

                mode =
                    "update";


                $('#saveBtn').text(
                    'Update'
                );


                // =============================================
                // LOAD SELECTED CATEGORY
                // =============================================

                loadBedInfo(
                    bed.category_id
                );

            },


            error: function(xhr) {

                console.log(
                    xhr.responseText
                );


                alert(
                    'Error: ' +
                    xhr.status
                );

            }

        });

    }
);


// ============================================================
// DELETE BED INFO
// ============================================================

$(document).on(
    'click',
    '.deleteBtn',
    function(e) {


        e.preventDefault();


        let id =
            $(this).data('id');


        let category_id =
            $('#category_id').val();


        if (
            confirm(
                'Confirm delete?'
            )
        ) {


            $.ajax({

                url:
                    '/bed_info/remove/',

                type:
                    'POST',


                headers: {

                    'X-CSRFToken':
                        csrftoken

                },


                data: {

                    id:
                        id

                },


                success: function(response) {


                    alert(
                        response.message
                    );


                    if (
                        response.status === 'success'
                    ) {


                        $('#form')[0].reset();


                        $('#id').val('');


                        $('#occupancy').val(
                            'vacant'
                        );


                        mode =
                            "save";


                        $('#saveBtn').text(
                            'Save'
                        );


                        loadBedInfo(
                            category_id
                        );

                    }

                },


                error: function(xhr) {

                    console.log(
                        xhr.responseText
                    );


                    alert(
                        'Error: ' +
                        xhr.status
                    );

                }

            });
        }

    }
);