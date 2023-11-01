$(document).ready(() => {
  $("#contact_us_submit_btn").on("click", function (e) {
    // Reseting Errors
    $("#email-error").html("");
    $("#message-error").html("");
    $("#common-error").html("");

    // Getting Contact Form Data
    let email = $("#contact_email").val();
    let contactMessage = $("#contact_message").val();
    // console.log(email, contactMessage);
    if (email && contactMessage) {
      if (emailValidate(email)) {
        addLoader();
        $.ajax({
          url: "/contact/",
          type: "POST",
          headers: {
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRFToken": getCookie("csrftoken"),
          },
          data: JSON.stringify({ email: email, contact_message: contactMessage }),
          success: function (result) {
            removeLoader();
            if(result['submitted']){
                window.location.reload(true);
            }
            if(result['error_message']){
                $("#common-error").html(`${result['error_message']}`)
            }
          },
          error: function (error) {
            console.log(`Error ${error}`);
          },
        });
      }else{
          $("#email-error").html("Please, Enter Valid Email.")
      }
    } else {
      if (!email && !contactMessage) {
        $("#email-error").html("Email Field is Required.");
        $("#message-error").html("Contact Message is Required.");
      } else if (!email) {
        $("#email-error").html("Email Field is Required.");
      } else {
        $("#message-error").html("Contact Message is Required.");
      }
    }
  });

  $(".message-view-block").fadeOut(15000, () => {
    $(".message-view-block").remove();
  });
  
});
