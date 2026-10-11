let mode = "save";   // GLOBAL


function loadBedCategories() {

    $.ajax({

        url: '/bed_category/get/',
        method: 'GET',

        success: function(response) {

            let categories = response.bed_categories || [];
            let tbody = '';


            $.each(categories, function(index, c) {


                // =================================================
                // STATUS
                // =================================================

                let statusBadge = c.status == 1
                    ? '<span class="badge bg-success">Active</span>'
                    : '<span class="badge bg-danger">Inactive</span>';


                // =================================================
                // TABLE ROW
                // =================================================

                tbody += `

                    <tr
                        class="bed-category-row"

                        data-id="${c.id}"

                        data-name="${c.name || ''}"

                        data-status="${c.status}"
                    >

                        <td>
                            ${index + 1}
                        </td>


                        <td>
                            ${c.id}
                        </td>


                        <td>
                            ${c.name || ''}
                        </td>


                        <td>
                            ${statusBadge}
                        </td>


                        <td>

                            <button
                                type="button"
                                class="btn btn-sm btn-warning editBtn"
                                data-id="${c.id}"
                            >
                                Edit
                            </button>


                            <button
                                type="button"
                                class="btn btn-sm btn-danger deleteBtn"

                                data-id="${c.id}"

                                data-name="${c.name || ''}"
                            >
                                Delete
                            </button>

                        </td>

                    </tr>

                `;

            });


            // =================================================
            // NO DATA
            // =================================================

            if (categories.length === 0) {

                tbody = `

                    <tr>

                        <td
                            colspan="5"
                            class="text-center"
                        >
                            No Bed Category Found
                        </td>

                    </tr>

                `;

            }


            $('#tableBody').html(tbody);

        },


        // =====================================================
        // ERROR
        // =====================================================

        error: function(xhr) {

            console.log(xhr.responseText);

            alert(
                'Failed to load bed category list.'
            );

        }

    });

}



// ============================================================
// DOCUMENT READY
// ============================================================

$(document).ready(function() {


    // ========================================================
    // LOAD BED CATEGORIES
    // ========================================================

    loadBedCategories();



    // ========================================================
    // SAVE / UPDATE BUTTON
    // ========================================================

    $('#saveBtn').click(function(e) {

        e.preventDefault();


        // ----------------------------------------------------
        // GET VALUES
        // ----------------------------------------------------

        let id = $('#id').val();

        let name = $('#name').val();

        let status = $('#status').val();


        // ----------------------------------------------------
        // VALIDATION
        // ----------------------------------------------------

        if (!name) {

            alert(
                "Please enter bed category name."
            );

            return;

        }


        // ====================================================
        // SAVE
        // ====================================================

        if (mode === 'save') {

            $.ajax({

                url: '/bed_category/save/',

                method: 'POST',

                headers: {

                    "X-CSRFToken": csrftoken

                },

                data: {

                    'name': name,

                    'status': status

                },


                success: function(response) {

                    console.log(
                        "Save Response:",
                        response
                    );


                    if (
                        response.status === 'success'
                    ) {

                        alert(
                            response.message ||
                            "Bed category saved successfully."
                        );


                        // Reload table
                        loadBedCategories();


                        // Clear form
                        clearBedCategoryForm();

                    }

                    else {

                        alert(
                            response.message ||
                            "Save failed."
                        );

                    }

                },


                error: function(xhr) {

                    console.log(
                        xhr.responseText
                    );


                    alert(
                        "Server error while saving bed category."
                    );

                }

            });

        }


        // ====================================================
        // UPDATE
        // ====================================================

        else if (mode === 'update') {


            if (!id) {

                alert(
                    "Bed Category ID not found."
                );

                return;

            }


            $.ajax({

                url: '/bed_category/update/',

                method: 'POST',

                headers: {

                    "X-CSRFToken": csrftoken

                },

                data: {

                    'id': id,

                    'name': name,

                    'status': status

                },


                success: function(response) {

                    console.log(
                        "Update Response:",
                        response
                    );


                    if (
                        response.status === 'success'
                    ) {

                        alert(
                            response.message ||
                            "Bed category updated successfully."
                        );


                        // Reload table
                        loadBedCategories();


                        // Clear form
                        clearBedCategoryForm();

                    }

                    else {

                        alert(
                            response.message ||
                            "Update failed."
                        );

                    }

                },


                error: function(xhr) {

                    console.log(
                        xhr.responseText
                    );


                    alert(
                        "Server error while updating bed category."
                    );

                }

            });

        }

    });



    // ========================================================
    // CLEAR BUTTON
    // ========================================================

    $('#clearBtn').click(function(e) {

        e.preventDefault();

        clearBedCategoryForm();

    });

});



// ============================================================
// EDIT BED CATEGORY
// ============================================================

$(document).on('click', '.editBtn', function(e) {

    e.preventDefault();


    // ========================================================
    // CURRENT ROW
    // ========================================================

    let row = $(this).closest(
        '.bed-category-row'
    );


    // ========================================================
    // GET DATA
    // ========================================================

    let id =
        row.data('id');


    let name =
        row.data('name');


    let status =
        row.data('status');


    console.log(
        "Editing Bed Category ID:",
        id
    );


    console.log(
        "Name:",
        name
    );


    console.log(
        "Status:",
        status
    );


    // ========================================================
    // UPDATE MODE
    // ========================================================

    mode = "update";


    // ========================================================
    // SET FORM VALUES
    // ========================================================

    $('#id').val(
        id
    );


    $('#name').val(
        name
    );


    $('#status').val(
        String(status)
    );


    // ========================================================
    // BUTTON TEXT
    // ========================================================

    $('#saveBtn').text(
        'Update'
    );


    // ========================================================
    // SCROLL TO FORM
    // ========================================================

    if ($('#form').length) {

        $('html, body').animate({

            scrollTop:
                $('#form').offset().top - 100

        }, 300);

    }

});



// ============================================================
// DELETE BED CATEGORY
// ============================================================

$(document).on('click', '.deleteBtn', function(e) {

    e.preventDefault();


    let id =
        $(this).data('id');


    let name =
        $(this).data('name');


    console.log(
        "Deleting Bed Category ID:",
        id
    );


    console.log(
        "Deleting Bed Category Name:",
        name
    );


    if (
        confirm(
            "Confirm to remove this bed category?"
        )
    ) {

        $.ajax({

            url: '/bed_category/remove/',

            method: 'POST',

            headers: {

                "X-CSRFToken": csrftoken

            },

            data: {

                'id': id

            },

            dataType: 'json',


            success: function(response) {

                console.log(
                    "Delete Response:",
                    response
                );


                if (
                    response.status === 'success'
                ) {

                    alert(
                        response.message ||
                        "Bed category removed successfully."
                    );


                    // Currently editing same item
                    if (
                        String($('#id').val()) ===
                        String(id)
                    ) {

                        clearBedCategoryForm();

                    }


                    // Reload table
                    loadBedCategories();

                }

                else {

                    alert(
                        response.message ||
                        "Delete failed."
                    );

                }

            },


            error: function(xhr) {

                console.log(
                    xhr.responseText
                );


                alert(
                    "Server error while deleting bed category."
                );

            }

        });

    }

});

$(document).on('click', '#clearBtn', function(e) {

    e.preventDefault();

    $('#id').val('');
    $('#name').val('');
    $('#status').val('1');

    mode = 'save';

    $('#saveBtn').text('Save');

});