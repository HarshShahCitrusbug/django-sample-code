// For Changing Password Type
let oldPasswordInput = document.getElementById("old_password_input");
let passwordInput = document.getElementById("password_input");
let toggle = document.getElementById("btnToggle");
let toggle1 = document.getElementById("btnToggle1");
let icon = document.getElementById("eyeIcon");
let icon1 = document.getElementById("eyeIcon1");

function togglePassword() {
  if (oldPasswordInput.type === "password") {
    oldPasswordInput.type = "text";
    icon.classList.add("fa-eye-slash");
    //toggle.innerHTML = 'hide';
  } else {
    oldPasswordInput.type = "password";
    icon.classList.remove("fa-eye-slash");
    //toggle.innerHTML = 'show';
  }
}

function togglePassword1() {
  if (passwordInput.type === "password") {
    passwordInput.type = "text";
    icon1.classList.add("fa-eye-slash");
    //toggle.innerHTML = 'hide';
  } else {
    passwordInput.type = "password";
    icon1.classList.remove("fa-eye-slash");
    //toggle.innerHTML = 'show';
  }
}

toggle.addEventListener("click", togglePassword, false);
toggle1.addEventListener("click", togglePassword1, false);

$(document).ready(() => {
  let input_name;
  let current_password;
  let new_password;

  // Update User Name
  $("#name_modal_btn").on("click", () => {
    $("#name_modal_error").html("");
    input_name = "";
    current_password = "";
    new_password = "";

    input_name = $("#name_input").val();
    if (input_name) {
      $.ajax({
        url: "/profiles/user-profile/",
        type: "POST",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": getCookie("csrftoken"),
        },
        data: JSON.stringify({
          input_name: input_name,
        }),
        success: function (result) {
          if (result["status"]) {
            window.location.reload(true);
          }
        },
        error: function (error) {
          console.log(`Error ${error}`);
        },
      });
    } else {
      $("#name_modal_error").html("Name Field is Required.");
    }
  });

  // Change Password
  $("#password_modal_btn").on("click", () => {
    $("#password_modal_error").html("");
    current_password = "";
    new_password = "";
    input_name = "";

    current_password = $("#old_password_input").val();
    new_password = $("#password_input").val();
    if (current_password && new_password) {
      if (passwordValidate(new_password)) {
        $.ajax({
          url: "/profiles/user-profile/",
          type: "POST",
          headers: {
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRFToken": getCookie("csrftoken"),
          },
          data: JSON.stringify({
            current_password: current_password,
            new_password: new_password,
          }),
          success: function (result) {
            if (result["status"]) {
              window.location.reload(true);
            }
            if (result["error_message"]) {
              $("#password_modal_error").html(result["error_message"]);
            }
          },
          error: function (error) {
            console.log(`Error ${error}`);
          },
        });
      } else {
        $("#password_modal_error").html(
          "Password should contain at least one digit, lowercase, uppercase, special character and length should be between 8-32."
        );
      }
    } else {
      $("#password_modal_error").html("Both Password Fields are Required.");
    }
  });
});
