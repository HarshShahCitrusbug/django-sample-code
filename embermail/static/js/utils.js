// CUSTOM FUNCTIONS
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      // Does this cookie string begin with the name we want?
      if (cookie.substring(0, name.length + 1) === name + "=") {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

function emailValidate(email) {
  const emailRegEx = /^\w+([\.-]?\w+)*@\w+([\.-]?\w+)*(\.\w{2,3})+$/;
  if (!emailRegEx.test(email)) {
    $("#email_error").html("Please, Enter Valid Email.");
    return false;
  }
  $("#email_error").html("");
  return true;
}

function passwordValidate(password) {
  // Password Criteria
  // 1. At least one digit [0-9]
  // 2. At least one lowercase character [a-z]
  // 3. At least one uppercase character [A-Z]
  // 4. At least one special character [*.!@#$%^&(){}[]:;<>,.?/~_+-=|\]
  // 5. At least 8 characters in length, but no more than 32.
  const passwordRegex =
    /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*])[A-Za-z\d!@#$%^&*]{8,32}$/;
  if (!passwordRegex.test(password)) {
    return false;
  }
  $("#password_error").html("");
  return true;
}

function fadeOutMessageAutomatic() {
  $(".message-view-block").fadeOut(15000, () => {
    $(".message-view-block").remove();
  });
}

function getUrlParameter(sParam) {
  var sPageURL = window.location.search.substring(1),
    sURLVariables = sPageURL.split("&"),
    sParameterName,
    i;

  for (i = 0; i < sURLVariables.length; i++) {
    sParameterName = sURLVariables[i].split("=");

    if (sParameterName[0] === sParam) {
      return sParameterName[1] === undefined
        ? true
        : decodeURIComponent(sParameterName[1]);
    }
  }
  return false;
}

function addLoader() {
  $("#loader").removeClass("d-none");
  $("body").addClass("loader-active");
}

function removeLoader() {
  $("#loader").addClass("d-none");
  $("body").removeClass("loader-active");
}
