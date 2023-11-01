$(document).ready(() => {
  // Focus on Input Field
  $("#app_password").focus();

  let selected_flow = getUrlParameter("selected_flow");
  let email_provider = getUrlParameter("email_provider");
  let email = getUrlParameter("email");
  $("#email_message_div").html(email);
  $("#app_password_continue_btn").on("click", () => {
    let app_password = $("#app_password").val();
    if (app_password != "" && app_password) {
      addLoader();
      $.ajax({
        url: "/campaigns/app-password/",
        type: "POST",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": getCookie("csrftoken"),
        },
        data: JSON.stringify({
          selected_flow: selected_flow,
          email_provider: email_provider,
          email: email,
          app_password: app_password,
        }),
        success: function (result) {
          removeLoader();
          if (result["valid_credentials"]) {
            window.location.assign(`/payment/plan/selection/`)
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
