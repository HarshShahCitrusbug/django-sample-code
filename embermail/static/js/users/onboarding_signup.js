$(document).ready(() => {
  let passwordInput = document.getElementById("signup_password");
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

  $("#signup_btn").click(() => {
    $("#strong_password_error").addClass("d-none");
    $("#email_error").html("");
    $("#password_error").html("");
    $("#common_error").html("");

    var email = $("#email").val();
    let signup_flow;
    if (!email){
      email = $("#email").text();
      signup_flow = "join_team"
    };

    var password = $("#signup_password").val();
    if (emailValidate(email)){
      addLoader();
      $.ajax({
        url: "/onboarding/",
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
          if (result["exist"]) {
              $("#signup_password_div").remove();
              ChooseOnboardingAjaxCall(email)
          }
        },
        error: function (error) {
          console.log(`Error ${error}`);
        },
      });
      if (password){
        if (passwordValidate(password)){
          addLoader();
          $("#strong_password_error").addClass("d-none");
          $.ajax({
            url: "/onboarding/signup/",
            type: "POST",
            headers: {
              "X-Requested-With": "XMLHttpRequest",
              "X-CSRFToken": getCookie("csrftoken"),
            },
            data: JSON.stringify({
              email: email,
              password: password,
              signup_flow : signup_flow,
            }),
            success: function (result) {
              removeLoader();
              if (result["registered"]) {
                window.location.href = "/onboarding";
              } else if(result['logged_in']) {
                window.location.href = "/campaigns/joining/flow/imap-access-details/";
              } else {
                $(`#${result["error_tag"]}_error`).html(`${result["error_message"]}`);
              }
            },
            error: function (error) {
              console.log(`Error: ${error}`);
            },
          });
        }else{
          $("#strong_password_error").removeClass("d-none");
        }
      }else {
        $("#password_error").html("Please, Enter password.")
      }
      
    }else{
      $("#email_error").html("Please, Enter valid email.");
    }
  });
});
