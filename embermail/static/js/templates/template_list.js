$(document).ready(() => {
  let selectedWarmupEmail = $("#selected_warmup_email").text().trim();
  let selectedWarmupId = $("#selected_warmup_email").data("campaign_id");

  // Get Warmup Email from Selection Dropdown
  $(document).on("click", ".warmup_email_list_item", function (e) {
    selectedWarmupId = $(this).data("campaign_id");
    selectedWarmupEmail = e.currentTarget.id;
    $("#selected_warmup_email").text(`${selectedWarmupEmail}`);
    $(location).attr("href", "?selected_warmup=" + selectedWarmupId);
  });

  // Add and Edit Template Modal Close Event 
  $(document).on(
    "hide.bs.modal",
    "#add_new_template, #exampleModal",
    function () {
      // Remove Errors on Discard Button Click
      $("#add_template_error").html("");
      $("#edit_template_error").html("");

      // Remove all Contents 
      $("#template_name").val("");
      $("#template_subject").val("");
      $("#edit_template_name").val("");
      $("#edit_template_subject").val("");
    }
  );

  // Add New Template
  $("#add_template_btn").on("click", () => {
    $("#add_template_error").html("");
    let template_name = $("#template_name").val();
    let template_subject = $("#template_subject").val();
    if (template_name != "" && template_subject != "") {
      // AJAX for Adding new Template
      $.ajax({
        url: "/templates/add/",
        type: "POST",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": getCookie("csrftoken"),
        },
        data: JSON.stringify({
          template_name: template_name,
          template_subject: template_subject,
          selected_email: selectedWarmupEmail,
        }),
        success: function (result) {
          if (result["redirect"]) {
            window.location.reload(true);
          } else if (result["error_message"]) {
            $("#add_template_error").html(`${result["error_message"]}`);
          }
        },
        error: function (error) {
          console.log(`Error ${error}`);
        },
      });
    } else {
      $("#add_template_error").html("All Fields are Required.");
    }
  });

  // Change Status (Active/InActive)
  $(".active_buttons").on("click", (e) => {
    template_id = e.currentTarget.id.split("_")[0];
    // AJAX for Change Status (Active/InActive)
    $.ajax({
      url: "/templates/update/status/",
      type: "POST",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      data: JSON.stringify({
        template_id: template_id,
        selected_email: selectedWarmupEmail,
      }),
      success: function (result) {
        if (result["redirect"]) {
          window.location.reload(true);
        }
      },
      error: function (error) {
        console.log(`Error ${error}`);
      },
    });
  });

  // Edit Templates
  $(".edit_buttons").on("click", (e) => {
    let template_id = e.currentTarget.id.split("_")[0];
    let template_name = e.currentTarget.dataset.name;
    let template_subject = e.currentTarget.dataset.subject;

    $("#edit_template_name").val(template_name);
    $("#edit_template_subject").val(template_subject);

    $("#edit_template_btn").on("click", () => {
      $("#edit_template_error").html("");
      let updated_name = $("#edit_template_name").val();
      let updated_subject = $("#edit_template_subject").val();
      if (updated_name != "" && updated_subject != "") {
        // AJAX for Edit Templates
        $.ajax({
          url: "/templates/update/",
          type: "POST",
          headers: {
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRFToken": getCookie("csrftoken"),
          },
          data: JSON.stringify({
            template_id: template_id,
            name: updated_name,
            subject: updated_subject,
            selected_email: selectedWarmupEmail,
          }),
          success: function (result) {
            if (result["redirect"]) {
              window.location.reload(true);
            } else if (result["error_message"]) {
              $("#edit_template_error").html(`${result["error_message"]}`);
            }
          },
          error: function (error) {
            console.log(`Error ${error}`);
          },
        });
      } else {
        $("#edit_template_error").html("All Fields are Required.");
      }
    });
  });

  // Delete Templates
  $(".delete_buttons").on("click", (e) => {
    let template_id = e.currentTarget.id.split("_")[0];
    let template_name_show = e.currentTarget.dataset.name;

    $("#template_name_filling").html(template_name_show);
    $("#delete_template_modal").modal("show");
    $(document).on("click", "#delete_template_btn", function () {
      // AJAX for Delete Templates
      $.ajax({
        url: "/templates/delete/",
        type: "POST",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": getCookie("csrftoken"),
        },
        data: JSON.stringify({
          template_id: template_id,
          selected_email: selectedWarmupEmail,
        }),
        success: function (result) {
          if (result["redirect"]) {
            window.location.reload(true);
            // window.location.assign(result["redirect"]);
          }
        },
        error: function (error) {
          console.log(`Error ${error}`);
        },
      });
    });
  });

  // Thread
  $(".thread_buttons").on("click", (e) => {
    let template_id = e.currentTarget.id.split("_")[0];
    window.location.assign(`/templates/threads/list/${template_id}/`);
  });

  // Add Default Templates
  $(".add_default_template_buttons").on("click", (e) => {
    addLoader();
    let template_id = e.currentTarget.id.split("_")[0];
    // AJAX for Add Default Templates
    $.ajax({
      url: "/templates/add/default/",
      type: "POST",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      data: JSON.stringify({
        template_id: template_id,
        selected_email: selectedWarmupEmail,
      }),
      success: function (result) {
        removeLoader();
        if (result["redirect"]) {
          window.location.reload(true);
        }
      },
      error: function (error) {
        console.log(`Error ${error}`);
      },
    });
  });
});
