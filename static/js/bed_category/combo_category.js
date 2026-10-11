//========== LOAD BED CATEGORY DROPDOWN ==========
console.log('hello');
function loadBedCategoryCombo() {
    $.ajax({
        url: '/bed_category/get/',
        method: 'GET',
 
        success: function(response) {
            let categories = response.bed_categories;
            let html = '<option value="">Select Bed Category</option>';
 
            $.each(categories, function(index, c) {
                if (c.status == 1) {
                    html += `<option value="${c.id}">${c.name}</option>`;
                }
            });
 
            $('#bed_category_id').html(html);
        },
 
        error: function(xhr) {
            console.log('Error loading bed categories');
        }
    });
}

$(document).ready(function() {
    loadBedCategoryCombo();
});
 
 