// ========== LOAD BED INFO DROPDOWN (FILTER BY CATEGORY) ==========
// ============================================================
// LOAD BED INFO COMBO
// ============================================================

console.log('Loading bed info combo...');

function loadBedInfoCombo(category_id = '') {

    $.ajax({

        url: '/bed_info/get/',
        method: 'GET',

        data: {
            category_id: category_id
        },

        success: function(response) {

            let beds = response.bed_info || [];

            let html =
                '<option value="">Select Bed Info</option>';


            $.each(beds, function(index, bed) {


                // =================================================
                // ONLY VACANT + ACTIVE BED
                // =================================================

                if (
                    bed.occupancy === 'vacant' &&
                    String(bed.status) === '1'
                ) {

                    html += `
                        <option value="${bed.id}">
                            Bed ${bed.bed_no} (${bed.category_name})
                        </option>
                    `;

                }

            });


            // =================================================
            // SET BED INFO COMBO
            // =================================================

            $('#bed_info_id').html(html);

        },


        error: function(xhr) {

            console.log(
                'Error loading bed info:',
                xhr.responseText
            );

        }

    });

}


// ============================================================
// ON PAGE LOAD
// ============================================================

$(document).ready(function() {


    $('#bed_info_id').html(
        '<option value="">Select Bed Info</option>'
    );


    // ========================================================
    // WHEN BED CATEGORY CHANGES
    // ========================================================

    $('#bed_category_id').on(
        'change',
        function() {

            let category_id =
                $(this).val();


            if (category_id) {

                loadBedInfoCombo(
                    category_id
                );

            }

            else {

                $('#bed_info_id').html(
                    '<option value="">Select Bed Info</option>'
                );

            }

        }
    );

});