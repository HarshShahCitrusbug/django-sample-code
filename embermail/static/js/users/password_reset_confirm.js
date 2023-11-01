$(document).ready(() => {
  let passwordInput = document.getElementById("password");
  let toggle = document.getElementById("btnToggle");
  let icon = document.getElementById("eyeIcon");

  function togglePassword() {
    if (passwordInput.type === "password") {
      passwordInput.type = "text";
      icon.classList.add("fa-eye-slash");
      //toggle.innerHTML = 'hide';
    } else {
      passwordInput.type = "password";
      icon.classList.remove("fa-eye-slash");
      //toggle.innerHTML = 'show';
    }
  }
  toggle.addEventListener("click", togglePassword, false);

  $("#reset_password_btn").on("click", () => {
    $("#common_error_div").addClass("d-none");
    $("#strong_password_error").addClass("d-none");
    $("#password_error").html("");
    var password = $("#password").val();
    if (password) {
      if (passwordValidate(password)) {
        addLoader();
        token = $(location).attr("href").split("token=")[1];
        $.ajax({
          url: "/reset-password-confirm/",
          type: "POST",
          headers: {
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRFToken": getCookie("csrftoken"),
          },
          data: JSON.stringify({
            password: password,
            encoded_token: token,
          }),
          success: function (result) {
            removeLoader();
            if (result["reset_successful"]) {
              window.location.assign("/onboarding/");
            } else {
              $(`#${result["error_tag"]}_error`).html(
                `${result["error_message"]}`
              );
              if (result["error_tag"] == "common") {
                $("#common_error_div").removeClass("d-none");
              }
            }
          },
          error: function (error) {
            console.log(`Error ${error}`);
          },
        });
      } else {
        $("#strong_password_error").removeClass("d-none");
      }
    } else {
      $("#password_error").html("Please, Enter password.");
    }
  });
});
