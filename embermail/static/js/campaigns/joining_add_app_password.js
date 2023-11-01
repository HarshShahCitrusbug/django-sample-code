$(document).ready(() => {
  // Focus on Input Field
  $("#app_password").focus();
  
  $("#app_password_continue_btn").on("click", () => {
    let app_password = $("#app_password").val();

    if (app_password != "" && app_password) {
      addLoader();
      $.ajax({
        url: "/campaigns/joining/flow/app-password/",
        type: "POST",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": getCookie("csrftoken"),
        },
        data: JSON.stringify({
          app_password: app_password,
        }),
        success: function (result) {
          removeLoader();
          if (result["success"]) {
            window.location.assign(`/campaigns/joining/flow/update/`)
          } else if (result['error_tag'] == '404') {
            window.location.assign(`/page-not-found/`)
          } else {
            $("#app_password_error").html(result['error_message'])
          }
        },
        error: function (error) {
          console.log(`Error ${error}`);
        },
      });
    } else {
      $("#app_password_error").html("Enter Valid App Password.");
    }
  });
});
