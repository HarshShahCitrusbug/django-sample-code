function ChooseOnboardingAjaxCall(email) {
  let requestPageFor;
  if (emailValidate(email)) {
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
          requestPageFor = "login";
        } else {
          requestPageFor = "registration";
        }
        $("#email_submit_btn").remove();
        $("#login-password-div").remove();
        $("#signup-password-div").remove();
        selectOnboardingFlow(requestPageFor, email);
      },
      error: function (error) {
        console.log(`Error ${error}`);
      },
    });
  }
}

function selectOnboardingFlow(requestPageFor, email) {
  addLoader();
  $.ajax({
    url: "/onboarding/",
    type: "GET",
    data: { onboarding_selected: requestPageFor , email: email},
    success: function (result) {
      removeLoader();
      $("#onboarding_box").append(result);
      $("#login_password").focus();
      $("#signup_password").focus();
    },
    error: function (error) {
      console.log(`Error ${error}`);
    },
  });
}

$(document).ready(() => {
  
  
  $("#email_submit_btn").on("click", () => {
    $("#error-msg").html("");
    $("#email_error").html("");
    var email = $("#email").val();
    if (! email){
      email = $("#email").text();
    }
    if(!email){
      $("#email_error").html("Please, Enter email address.");
    }else{
      ChooseOnboardingAjaxCall(email);
    }
    
  });

  // $(".email_list_item").on("click", (e) => {
  //   email = e.target.text;
  //   $("#email").val(email);
  //   ChooseOnboardingAjaxCall(email);
  // });
});
