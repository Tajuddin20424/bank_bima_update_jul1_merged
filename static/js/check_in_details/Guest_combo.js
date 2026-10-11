// ============================================================
// LOAD HOTEL GUEST COMBO
// ============================================================

console.log('Loading guest combo...');

function loadGuestCombo(selected_id = '') {

    $.ajax({

        url: '/check_in_details/load-guests/',
        method: 'GET',

        success: function(response) {

            let guests = response.guests || [];

            let html =
                '<option value="">Select Guest</option>';


            $.each(guests, function(index, guest) {


                // =================================================
                // ONLY ACTIVE GUEST (status = 1 from backend)
                // =================================================

                html += `
                    <option value="${guest.id}">
                        ${guest.guest_name} (${guest.mobile || '-'})
                    </option>
                `;

            });


            // =================================================
            // SET GUEST COMBO
            // =================================================

            $('#hotel_guest_id').html(html);

            if (selected_id) {
                $('#hotel_guest_id').val(String(selected_id));
            }

        },


        error: function(xhr) {

            console.log(
                'Error loading guest:',
                xhr.responseText
            );

        }

    });

}


$(document).ready(function() {

    if ($('#hotel_guest_id').length) {
        loadGuestCombo();
    }

});