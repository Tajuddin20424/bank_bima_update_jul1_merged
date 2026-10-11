$(document).ready(function() {

    // ================= CSRF HELPER =================
    function csrfToken() {
        return $('input[name="csrfmiddlewaretoken"]').val() || $("meta[name='csrf-token']").attr("content");
    }

    // ================= ADD SUPER ADMIN =================
    $("#addSaveBtn").off("click").on("click", function() {
        let name = $("#addName").val().trim();
        let email = $("#addEmail").val().trim();
        let phone = $("#addPhone").val().trim();
        let companyId = $("#addCompany").val(); //        let locationId = $("#addLocation").val(); //        let password = $("#addPassword").val();
        let confirmPassword = $("#addConfirmPassword").val();
        let image = $("#addImage")[0].files[0];

        if (!name || !email || !phone || !companyId || !locationId || !password || !confirmPassword) { //            alert("All fields are required");
            return;
        }

        if (password !== confirmPassword) {
            alert("Passwords do not match");
            return;
        }

        let formData = new FormData();
        formData.append("name", name);
        formData.append("email", email);
        formData.append("phone", phone);
        formData.append("company_id", companyId); //        formData.append("location_id", locationId); //        formData.append("password", password);
        formData.append("confirm_password", confirmPassword);
        if (image) formData.append("logo", image);
        formData.append("csrfmiddlewaretoken", csrfToken());

        $.ajax({
            url: "/users/super-admin/create/",
            type: "POST",
            data: formData,
            contentType: false,
            processData: false,
            success: function(res) {
                if (res.success) {
                    let imgTag = res.logo_url ? `<img src="${res.logo_url}" style="height:40px;">` : "No Image";
                    $("#superAdminTableBody").append(`
                        <tr data-id="${res.id}">
                            <td>${$("#superAdminTableBody tr").length + 1}</td>
                            <td class="sa-user-id">${res.user_id}</td>
                            <td class="sa-name">${res.name}</td>
                            <td class="sa-email">${res.email}</td>
                            <td class="sa-phone">${res.phone}</td>
                            <td class="sa-company" data-company-id="${res.company_id || ""}">${res.company_name || "-"}</td>
                            <td class="sa-location" data-location-id="${res.location_id || ""}">${res.location_name || "-"}</td>
                            <td class="sa-image">${imgTag}</td>
                            <td>
                                <button class="btn btn-sm btn-info edit-btn" data-bs-toggle="modal" data-bs-target="#editModal">Edit</button>
                                <button class="btn btn-sm btn-danger delete-btn">Delete</button>
                            </td>
                        </tr>
                    `);
                    $("#addModal").modal('hide');
                    $("#addName, #addEmail, #addPhone, #addPassword, #addConfirmPassword").val("");
                    $("#addCompany, #addLocation").val(""); //                    $("#addImage").val(null);
                } else {
                    alert(res.message || "Failed to create super admin");
                }
            },
            error: function(err) {
                console.error(err);
                alert("AJAX error. Check console.");
            }
        });
    });

    // ================= OPEN EDIT MODAL =================
    $(document).off("click", ".edit-btn").on("click", ".edit-btn", function() {
        let row = $(this).closest("tr");
        let id = row.data("id");
        let name = row.find(".sa-name").text();
        let email = row.find(".sa-email").text();
        let phone = row.find(".sa-phone").text();
        let companyId = row.find(".sa-company").data("company-id") || ""; //        let locationId = row.find(".sa-location").data("location-id") || ""; //
        $("#editId").val(id);
        $("#editName").val(name);
        $("#editEmail").val(email);
        $("#editPhone").val(phone);
        $("#editCompany").val(companyId); //        $("#editLocation").val(locationId); //        $("#editPassword, #editConfirmPassword").val("");
        $("#editImage").val(null);
    });

    // ================= UPDATE SUPER ADMIN =================
    $("#editSaveBtn").off("click").on("click", function() {
        let id = $("#editId").val();
        let name = $("#editName").val().trim();
        let email = $("#editEmail").val().trim();
        let phone = $("#editPhone").val().trim();
        let companyId = $("#editCompany").val(); //        let locationId = $("#editLocation").val(); //        let password = $("#editPassword").val();
        let confirmPassword = $("#editConfirmPassword").val();
        let image = $("#editImage")[0].files[0];

        if (!name || !email || !phone || !companyId || !locationId) { //            alert("Name, Email, Phone, Company, and Location are required"); //            return;
        }

        if (password && password !== confirmPassword) {
            alert("Passwords do not match");
            return;
        }

        let formData = new FormData();
        formData.append("name", name);
        formData.append("email", email);
        formData.append("phone", phone);
        formData.append("company_id", companyId); //        formData.append("location_id", locationId); //        if (password) formData.append("password", password);
        if (confirmPassword) formData.append("confirm_password", confirmPassword);
        if (image) formData.append("logo", image);
        formData.append("csrfmiddlewaretoken", csrfToken());

        $.ajax({
            url: `/users/super-admin/update/${id}/`,
            type: "POST",
            data: formData,
            contentType: false,
            processData: false,
            success: function(res) {
                if (res.success) {
                    let row = $(`tr[data-id='${id}']`);
                    row.find(".sa-name").text(res.name);
                    row.find(".sa-email").text(res.email);
                    row.find(".sa-phone").text(res.phone);
                    row.find(".sa-company").text(res.company_name || "-").attr("data-company-id", res.company_id || "").data("company-id", res.company_id || ""); //                    row.find(".sa-location").text(res.location_name || "-").attr("data-location-id", res.location_id || "").data("location-id", res.location_id || ""); //                    row.find(".sa-image").html(res.logo_url ? `<img src="${res.logo_url}" style="height:40px;">` : "No Image");
                    $("#editModal").modal('hide');
                } else {
                    alert(res.message || "Update failed");
                }
            },
            error: function(err) {
                console.error(err);
                alert("AJAX error. Check console.");
            }
        });
    });

    // ================= DELETE =================
    $(document).off("click", ".delete-btn").on("click", ".delete-btn", function() {
        if (!confirm("Are you sure you want to delete this super admin?")) return;

        let row = $(this).closest("tr");
        let id = row.data("id");

        $.ajax({
            url: `/users/super-admin/delete/${id}/`,
            type: "POST",
            data: { csrfmiddlewaretoken: csrfToken() },
            success: function(res) {
                if (res.success) {
                    row.remove();
                } else {
                    alert(res.message || "Delete failed");
                }
            },
            error: function(err) {
                console.error(err);
                alert("AJAX error. Check console.");
            }
        });
    });

});
