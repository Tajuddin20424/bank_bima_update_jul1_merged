$(document).ready(function() {

    // ================= CSRF HELPER =================
    function getCSRF() {
        return $("input[name='csrfmiddlewaretoken']").val() || $("meta[name='csrf-token']").attr("content");
    }

    // ================= OPEN ADD MODAL =================
    $("#addBtn").click(function() {
        $("#patientForm")[0].reset();         // Clear all fields
        $("#patient_id").val("");             // Clear hidden id
        $("#modalTitle").text("Add Patient"); // Set modal title
        $("#saveBtn").text("Save");
        $("#patientModal").modal("show");
    });

    // ================= OPEN EDIT MODAL =================
    $(document).on("click", ".editBtn", function() {
        let row = $(this).closest("tr");
        let id = row.data("id");

        $.ajax({
            url: "/dcc/patients/fetch/",   // Django view to fetch patient by ID
            type: "GET",
            data: { id: id },
            success: function(res) {
                if (res.error) {
                    alert(res.error);
                    return;
                }

                $("#patient_id").val(res.id);
                $("#modalTitle").text("Edit Patient");
                $("#saveBtn").text("Update");

                // Populate fields dynamically
                for (let key in res) {
                    let field = $(`[name=${key}]`);
                    if (field.length) {
                        if (field.is("select") || field.is("input") || field.is("textarea")) {
                            field.val(res[key]);
                        }
                    }
                }

                $("#patientModal").modal("show");
            },
            error: function(err) {
                console.error(err);
                alert("Failed to fetch patient data.");
            }
        });
    });

    // ================= SAVE / UPDATE =================
    $("#patientForm").submit(function(e) {
        e.preventDefault();

        let id = $("#patient_id").val();
        let url = id ? "/dcc/patients/" + id + "/update/" : "/dcc/patients/store/";

        $.ajax({
            url: url,
            type: "POST",
            data: $(this).serialize(),
            headers: { "X-CSRFToken": getCSRF() },
            success: function(res) {
                if (res.success) {
                    alert(id ? "Patient updated successfully!" : "Patient added successfully!");
                    $("#patientModal").modal("hide");
                    location.reload(); // Reload table
                } else {
                    alert(res.error || "Operation failed");
                }
            },
            error: function(err) {
                console.error(err);
                alert("Server error during save/update");
            }
        });
    });

    // ================= DELETE PATIENT =================
    $(document).on("click", ".deleteBtn", function() {
        if (!confirm("Are you sure you want to delete this patient?")) return;

        let row = $(this).closest("tr");
        let id = row.data("id");

        $.ajax({
            url: "/dcc/patients/" + id + "/delete/",
            type: "POST",
            data: { csrfmiddlewaretoken: getCSRF() },
            success: function(res) {
                if (res.success) {
                    row.fadeOut();
                    alert("Patient deleted successfully!");
                } else {
                    alert(res.error || "Delete failed");
                }
            },
            error: function(err) {
                console.error(err);
                alert("Server error during delete");
            }
        });
    });

    // ================= PRESCRIBE BUTTON =================
    $(document).on("click", ".prescribeBtn", function() {
        let row = $(this).closest("tr");
        let patientId = row.data("id"); 
        window.location.href = "/dcc/patients/report/?patient_id=" + encodeURIComponent(patientId);
    });

});