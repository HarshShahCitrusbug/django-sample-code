function preventBack(){
  window.history.forward();
}
setTimeout(preventBack(), 0);
window.onunload = function() {null};

$(document).ready(() => {
  // Focus on Input Field
  $("#email").focus();
  $("#email_submit_btn").on("click", () => {
    let selected_flow = getUrlParameter("selected_flow");
    let email_provider = getUrlParameter("email_provider");
    let email = $("#email").val();
    if (emailValidate(email)) {
      addLoader();
      if (selected_flow == "invite") {
        $.ajax({
          url: "/campaigns/add-email/",
          type: "POST",
          headers: {
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRFToken": getCookie("csrftoken"),
          },
          data: JSON.stringify({
            selected_flow: selected_flow,
            email_provider: email_provider,
            email: email,
          }),
          success: function (result) {
            removeLoader();
            if (result["redirect"]) {
              window.location.assign(`${result["redirect"]}`)
            } else {
              $("#email_error").html(`${result['error_message']}`)
            }
          },
          error: function (error) {
            console.log(`Error ${error}`);
          },
        });
      } else {
        $.ajax({
          url: "/campaigns/add-email/",
          type: "POST",
          headers: {
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRFToken": getCookie("csrftoken"),
          },
          data: JSON.stringify({
            selected_flow: selected_flow,
            email_provider: email_provider,
            email: email,
          }),
          success: function (result) {
            removeLoader();
            if (result["redirect"]) {
              window.location.assign(`${result["redirect"]}`)
            } else {
              $("#email_error").html(`${result['error_message']}`)
            }
          },
          error: function (error) {
            console.log(`Error ${error}`);
          },
        });
      }
    }
  });
});
