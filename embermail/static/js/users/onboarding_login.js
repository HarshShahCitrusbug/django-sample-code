$(document).ready(() => {
  let passwordInput = document.getElementById("login_password");
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

  $("#login_btn").on("click", () => {
    $("#common_error").html("");
    $("#password_error").html("");
    $("#common_error_div").addClass("d-none");

    var email = $("#email").val();
    var password = $("#login_password").val();

    if (emailValidate(email)) {
      if (password) {
        addLoader();
        $.ajax({
          url: "/onboarding/login/",
          type: "POST",
          headers: {
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRFToken": getCookie("csrftoken"),
          },
          data: JSON.stringify({
            email: email,
            password: password,
          }),
          success: function (result) {
            removeLoader();
            if (result["logged_in"]) {
              window.location.assign(result["redirect"]);
            } else {
              if (result["error_message"]) {
                $(`#${result["error_tag"]}_error`).html(
                  `${result["error_message"]}`
                );
                if (result["error_tag"] == "common") {
                  $("#common_error_div").removeClass("d-none");
                }
              } else {
                $("#common_error_div").addClass("d-none");
                $("#login_password_div").remove();
                $("#onboarding_box").append(result);
                $("#signup_password").focus();
                $("#fill_email").html(email);
              }
            }
          },
          error: function (error) {
            console.log(`Error ${error}`);
          },
        });
      } else {
        $("#password_error").html("Please, Enter Password.");
      }
    }
  });
});
