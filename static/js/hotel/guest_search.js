$(document).ready(function () {

    let allGuests = [];
    let filteredGuests = [];
    let activeIndex = -1;


    // ==========================================
    // LOAD GUEST
    // ==========================================
    $.ajax({
        url: window.APP_URLS.HOTEL_GUEST_COMBO_URL,
        type: "GET",

        success: function (response) {

            if (response.status === "success") {
                allGuests = response.results || [];
            }

        },

        error: function (xhr) {
            console.log(xhr.responseText);
        }
    });


    // ==========================================
    // SEARCH GUEST
    // ==========================================
    $("#guestSearch").on("input", function () {

        let search = $(this).val().trim().toLowerCase();

        if (!search) {
            $("#guestSearchResult").hide();
            return;
        }


        filteredGuests = allGuests.filter(function (guest) {

            let guestId = String(guest.guest_id || "").toLowerCase();
            let name = String(guest.guest_name || "").toLowerCase();
            let mobile = String(guest.mobile || "").toLowerCase();
            let address = String(guest.address || "").toLowerCase();

            return (
                guestId.includes(search) ||
                name.includes(search) ||
                mobile.includes(search) ||
                address.includes(search)
            );

        }).slice(0, 10);


        activeIndex = -1;

        showGuests();

    });


    // ==========================================
    // SHOW SEARCH RESULT
    // ==========================================
    function showGuests() {

        let html = "";


        if (filteredGuests.length === 0) {

            html = `
                <tr>
                    <td colspan="4" class="text-center">
                        No Guest Found
                    </td>
                </tr>
            `;

        } else {

            filteredGuests.forEach(function (guest, index) {

                html += `
                    <tr class="guest-row"
                        data-index="${index}"
                        style="cursor:pointer;">

                        <td>${guest.guest_id || "-"}</td>
                        <td>${guest.guest_name || "-"}</td>
                        <td>${guest.mobile || "-"}</td>
                        <td>${guest.address || "-"}</td>

                    </tr>
                `;

            });

        }

        $("#guestSearchBody").html(html);

        $("#guestSearchResult").show();

    }


    // ==========================================
    // CLICK GUEST
    // ==========================================
    $(document).on("click", ".guest-row", function () {

        let index = $(this).data("index");

        selectGuest(
            filteredGuests[index]
        );

    });


    // ==========================================
    // KEYBOARD
    // ==========================================
    $("#guestSearch").on("keydown", function (e) {

        if (filteredGuests.length === 0) {
            return;
        }


        // DOWN
        if (e.key === "ArrowDown") {
            e.preventDefault();

            activeIndex++;

            if (activeIndex >= filteredGuests.length) {
                activeIndex = 0;
            }

            activeRow();

        }


        // UP
        else if (e.key === "ArrowUp") {

            e.preventDefault();

            activeIndex--;

            if (activeIndex < 0) {
                activeIndex = filteredGuests.length - 1;
            }

            activeRow();

        }


        // ENTER
        else if (e.key === "Enter") {

            e.preventDefault();

            if (activeIndex >= 0) {

                selectGuest(
                    filteredGuests[activeIndex]
                );

            }

        }


        // ESC
        else if (e.key === "Escape") {

            $("#guestSearchResult").hide();

        }

    });


    // ==========================================
    // ACTIVE ROW
    // ==========================================
    function activeRow() {

        $(".guest-row").removeClass("table-primary");

        $(".guest-row")
            .eq(activeIndex)
            .addClass("table-primary");

    }


    // ==========================================
    // SELECT GUEST
    // ==========================================
    function selectGuest(guest) {

        if (!guest) {
            return;
        }


        $("#guest_id").val(
            guest.id || ""
        );

        $("#guest_user_id").val(
            guest.guest_id || ""
        );

        $("#guest_id_display").val(
            guest.guest_id || ""
        );

        $("#pat_title").val(
            guest.title || "Mr."
        );

        $("#guest_name").val(
            guest.guest_name || ""
        );

        $("#guest_phone").val(
            guest.mobile || ""
        );

        $("#guest_address").val(
            guest.address || ""
        );


        // Selected Guest
        $("#guestSearch").val(
            (guest.guest_id || "")
            + " - "
            + (guest.guest_name || "")
        );


        $("#guestSearchResult").hide();

        filteredGuests = [];
        activeIndex = -1;


        // Go to SR
        $("#sr_lookup").focus();

    }


    // ==========================================
    // CLICK OUTSIDE
    // ==========================================
    $(document).on("click", function (e) {

        if (
            !$(e.target).closest(
                "#guestSearch, #guestSearchResult"
            ).length
        ) {

            $("#guestSearchResult").hide();

        }

    });

});