$(document).ready(() => {
  $("#password_reset_btn").on("click", () => {
    $("#common_error_div").addClass("d-none");
    $("#email_not_exist_message").addClass("d-none");
    var email = $("#email").val();
    if (email) {
      if (emailValidate(email)) {
        addLoader();
        $.ajax({
          url: "/password-reset/",
          type: "POST",
          headers: {
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRFToken": getCookie("csrftoken"),
          },
          data: JSON.stringify({
            email: email,
          }),
          success: function (result) {
            removeLoader();
            if (result["email_exists"]) {
              window.location.assign("/onboarding/");
            } else if (result["email_exists"] == false) {
              $("#entered_email").html(email);
              $("#email_not_exist_message").removeClass("d-none");
            } else {
              $("#common_error").html(
                "Something went wrong, please try again later."
              );
              $("#common_error_div").removeClass("d-none");
            }
          },
          error: function (error) {
            console.log(`Error ${error}`);
          },
        });
      }
    } else {
      $("#email_error").html("Please, Enter email address.");
    }
  });
});
