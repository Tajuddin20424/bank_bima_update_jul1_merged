
let mode = "save";
let allHotels = [];


// ==========================================
// LOAD HOTEL GUEST
// ==========================================
function loadHotel() {

    $.ajax({
        url: '/hotel/load-hotel/',
        type: 'GET',

        success: function (response) {

            allHotels = response.hotels || [];

            showHotelList(allHotels);
        },

        error: function (xhr) {

            console.log(xhr.responseText);

            alert("Failed to load hotel guest list.");
        }
    });
}


// ==========================================
// SHOW HOTEL GUEST LIST
// ==========================================
function showHotelList(hotels) {

    let html = '';

    if (hotels.length == 0) {

        html = `
            <tr>
                <td colspan="7" class="text-center text-muted">
                    No Guest Found
                </td>
            </tr>
        `;

        $('#guestTableBody').html(html);

        return;
    }


    $.each(hotels, function (index, guest) {

        // STATUS
        let status = guest.status == 'A'
            ? '<span class="badge bg-success">Active</span>'
            : '<span class="badge bg-danger">Inactive</span>';


        // IMAGE
        let image = 'No Image';

        if (guest.image) {

            image = `
                <img
                    src="/media/${guest.image}"
                    width="50"
                    height="50"
                    style="object-fit:cover; border-radius:50%;"
                >
            `;
        }


        html += `
            <tr>

                <td>
                    ${index + 1}
                </td>

                <td>
                    ${image}
                </td>

                <td>
                    ${guest.title || ''}
                    ${guest.guest_name || ''}
                </td>

                <td>
                    ${guest.mobile || ''}
                </td>

                <td>
                    ${guest.bed_category || ''}
                </td>

                <td>
                    ${status}
                </td>

                <td>

                    <button
                        type="button"
                        class="btn btn-sm btn-warning editBtn"
                        data-id="${guest.id}"
                    >
                        Edit
                    </button>

                    <button
                        type="button"
                        class="btn btn-sm btn-danger deleteBtn"
                        data-id="${guest.id}"
                        data-name="${guest.guest_name || ''}"
                    >
                        Delete
                    </button>

                </td>

            </tr>
        `;
    });


    $('#guestTableBody').html(html);
}


// ==========================================
// SEARCH OLD GUEST
// ==========================================
$('#oldGuestSearch').on('input', function () {

    let search = $(this)
        .val()
        .trim()
        .toLowerCase();


    // EMPTY = SHOW ALL
    if (search == '') {

        showHotelList(allHotels);

        return;
    }


    let filteredGuests = allHotels.filter(function (guest) {

        let guestId = String(
            guest.guest_id || ''
        ).toLowerCase();

        let guestName = String(
            guest.guest_name || ''
        ).toLowerCase();

        let mobile = String(
            guest.mobile || ''
        ).toLowerCase();

        let address = String(
            guest.address || ''
        ).toLowerCase();


        return (
            guestId.includes(search) ||
            guestName.includes(search) ||
            mobile.includes(search) ||
            address.includes(search)
        );
    });


    showHotelList(filteredGuests);
});


// ==========================================
// SAVE / UPDATE
// ==========================================
$('#saveBtn').click(function (e) {

    e.preventDefault();


    let id = $('#guest_db_id').val();

    let guest_name = $('#guest_name').val();
    let mobile = $('#mobile').val();

    let bed_category_id =
        $('#bed_category_id').val();

    let bed_info_id =
        $('#bed_info_id').val();


    // VALIDATION
    if (!guest_name) {

        alert("Please enter guest name.");

        return;
    }


    if (!mobile) {

        alert("Please enter mobile number.");

        return;
    }


    if (!bed_category_id) {

        alert("Please select bed category.");

        return;
    }


    if (!bed_info_id) {

        alert("Please select bed.");

        return;
    }


    // FORM DATA
    let formData = new FormData();


    formData.append(
        'title',
        $('#title').val()
    );


    formData.append(
        'guest_name',
        guest_name
    );


    formData.append(
        'mobile',
        mobile
    );


    formData.append(
        'gender',
        $('#gender').val()
    );


    formData.append(
        'date_of_birth',
        $('#date_of_birth').val()
    );


    formData.append(
        'nationality',
        $('#nationality').val()
    );


    formData.append(
        'address',
        $('#address').val()
    );


    formData.append(
        'check_in',
        $('#check_in').val()
    );


    formData.append(
        'check_out',
        $('#check_out').val()
    );


    formData.append(
        'booking_source',
        $('#booking_source').val()
    );


    formData.append(
        'guest_category',
        $('#guest_category').val()
    );


    formData.append(
        'bed_category_id',
        bed_category_id
    );


    formData.append(
        'bed_info_id',
        bed_info_id
    );


    formData.append(
        'emergency_guest_contact',
        $('#emergency_contact').val()
    );


    formData.append(
        'entry_by',
        $('#entry_by').val()
    );


    formData.append(
        'status',
        $('#status').val()
    );


    // IMAGE
    let image = $('#image')[0];


    if (
        image &&
        image.files &&
        image.files.length > 0
    ) {

        formData.append(
            'image',
            image.files[0]
        );
    }


    // SAVE OR UPDATE URL
    let url = '/hotel/save-hotel/';


    if (mode == 'update') {

        formData.append(
            'id',
            id
        );

        url = '/hotel/update-hotel/';
    }


    // AJAX
    $.ajax({

        url: url,

        type: 'POST',

        headers: {
            "X-CSRFToken": csrftoken
        },

        data: formData,

        processData: false,

        contentType: false,


        success: function (response) {

            if (response.status == 'success') {

                alert(
                    response.message ||
                    "Saved successfully."
                );


                clearHotelForm();

                loadHotel();

            } else {

                alert(
                    response.message ||
                    "Save failed."
                );
            }
        },


        error: function (xhr) {

            console.log(
                xhr.responseText
            );

            alert(
                "Something went wrong."
            );
        }
    });
});


// ==========================================
// EDIT GUEST
// ==========================================
$(document).on(
    'click',
    '.editBtn',
    function () {

        let id = $(this).data('id');


        let guest = allHotels.find(
            function (item) {

                return String(item.id) ==
                    String(id);
            }
        );


        if (!guest) {

            alert(
                "Guest information not found."
            );

            return;
        }


        mode = "update";


        // ID
        $('#guest_db_id').val(
            guest.id
        );


        // BASIC INFO
        $('#title').val(
            guest.title || ''
        );


        $('#guest_name').val(
            guest.guest_name || ''
        );


        $('#mobile').val(
            guest.mobile || ''
        );


        $('#gender').val(
            guest.gender || ''
        );


        $('#date_of_birth').val(
            guest.date_of_birth || ''
        );


        $('#nationality').val(
            guest.nationality || ''
        );


        $('#address').val(
            guest.address || ''
        );


        // CHECK IN / OUT
        $('#check_in').val(
            guest.check_in || ''
        );


        $('#check_out').val(
            guest.check_out || ''
        );


        // OTHER INFO
        $('#booking_source').val(
            guest.booking_source || ''
        );


        $('#guest_category').val(
            guest.guest_category || ''
        );


        $('#emergency_contact').val(
            guest.emergency_guest_contact || ''
        );


        $('#entry_by').val(
            guest.entry_by || ''
        );


        // STATUS A / D
        $('#status').val(
            guest.status || 'A'
        );


        // BED CATEGORY
        $('#bed_category_id').val(
            guest.bed_category || ''
        );


        // BED INFO
        if (
            typeof loadBedInfoCombo ===
            'function'
        ) {

            loadBedInfoCombo(
                guest.bed_info || ''
            );

        } else {

            $('#bed_category_id')
                .trigger('change');


            setTimeout(function () {

                $('#bed_info_id').val(
                    guest.bed_info || ''
                );

            }, 500);
        }


        // IMAGE
        if (guest.image) {

            $('#imagePreview')
                .attr(
                    'src',
                    '/media/' + guest.image
                )
                .show();

        } else {

            $('#imagePreview')
                .attr('src', '')
                .hide();
        }


        $('#image').val('');


        // BUTTON
        $('#saveBtn').text(
            'Update'
        );


        // GO TO TOP FORM
        $('html, body').animate(
            {
                scrollTop: 0
            },
            300
        );
    }
);


// ==========================================
// DELETE GUEST
// ==========================================
$(document).on(
    'click',
    '.deleteBtn',
    function () {

        let id =
            $(this).data('id');

        let name =
            $(this).data('name');


        if (
            !confirm(
                "Confirm to remove " +
                name +
                "?"
            )
        ) {

            return;
        }


        $.ajax({

            url:
                '/hotel/delete-hotel/',

            type:
                'POST',

            headers: {

                "X-CSRFToken":
                    csrftoken
            },

            data: {

                id: id
            },


            success: function (response) {

                if (response.status == 'success') {

                    console.log(response.hotels);

                    allHotels = response.hotels || [];

                    showHotelList(allHotels);

                } else {

                    alert(
                        response.message ||
                        "Delete failed."
                    );
                }
            },


            error: function (xhr) {

                console.log(
                    xhr.responseText
                );

                alert(
                    "Something went wrong."
                );
            }
        });
    }
);


// ==========================================
// TITLE → GENDER
// ==========================================
$('#title').change(function () {

    let title =
        $(this).val();


    if (
        title == 'Mr.' ||
        title == 'Shri'
    ) {

        $('#gender').val(
            'Male'
        );

    } else if (
        title == 'Mrs.' ||
        title == 'Ms.' ||
        title == 'Miss' ||
        title == 'Shrimati'
    ) {

        $('#gender').val(
            'Female'
        );

    } else {

        $('#gender').val('');
    }
});


// ==========================================
// CLEAR FORM
// ==========================================
function clearHotelForm() {

    $('#guest_db_id').val('');


    $('#title').val('');

    $('#guest_name').val('');

    $('#mobile').val('');

    $('#gender').val('');


    $('#date_of_birth').val('');

    $('#nationality').val('');

    $('#address').val('');


    $('#booking_source').val('');

    $('#guest_category').val('');


    $('#bed_category_id').val('');


    $('#bed_info_id').html(
        '<option value="">Select Bed Info</option>'
    );


    $('#check_in').val('');

    $('#check_out').val('');


    $('#emergency_contact').val('');

    $('#entry_by').val('');


    // DEFAULT ACTIVE
    $('#status').val('A');


    $('#image').val('');


    $('#imagePreview')
        .attr('src', '')
        .hide();


    mode = "save";


    $('#saveBtn').text(
        'Save'
    );
}


// ==========================================
// CLEAR BUTTON
// ==========================================
$('#clearBtn').click(function (e) {

    e.preventDefault();

    clearHotelForm();
});


// ==========================================
// PAGE LOAD
// ==========================================
$(document).ready(function () {

    loadHotel();

});