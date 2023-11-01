$(document).ready(() => {
  // Validate Personal Data
  let personal_data_valid = true;
  let full_name;
  let city;
  let zip;
  let country = $.trim($("#selected_country").text());

  $("#full_name").on("change", () => {
    full_name = $("#full_name").val();
    $("#full_name_error").html("");
    personal_data_valid = true;
    if (!full_name) {
      $("#full_name_error").html("Enter full name or Company.");
      personal_data_valid = false;
    }
  });

  $("#city").on("change", () => {
    city = $("#city").val();
    $("#city_error").html("");
    personal_data_valid = true;
    if (!city) {
      $("#city_error").html("Enter city name.");
      personal_data_valid = false;
    }
  });

  $("#zip").on("change", () => {
    zip = $("#zip").val();
    $("#zip_error").html("");
    personal_data_valid = true;
    if (!zip) {
      $("#zip_error").html("Enter Zip.");
      personal_data_valid = false;
    }
  });

  $(document).on("change", "#country",function () {
    country = $.trim($("#country_list option[value='" + $("#country").val() + "']").text());
    personal_data_valid = true;
  });

  // Stripe
  // Get public key using Ajax call while reloading this page
  let stripe = Stripe(
    "pk_test_51NTUXCCWIhbNpIvgBQT5O01OOiNg2DSzg6SZ12ZA8rVMI1Rz7KOy12UMAL6LYjWoR4ry6aQjuO6wdkcAnpVy1mod00j6Rnnai3"
  );

  var elements = stripe.elements();

  // Creating Card Number Element
  card_number_valid = false;
  let cardNumberEle = elements.create("cardNumber", {
    style: {
      base: {
        fontSize: "16px",
        color: "#32325d",
        "::placeholder": {
          color: "#aab7c4",
        },
      },
      invalid: {
        color: "#dc3545",
      },
    },
  });
  cardNumberEle.mount("#card_number_div");
  // Card Number Change Event
  cardNumberEle.on("change", function (event) {
    $("#card_number_error").html("");
    if (event.error) {
      $("#card_number_error").html(event.error.message);
    } else if (event.complete) {
      card_number_valid = true;
    }
  });

  // Creating Card Expiry Element
  card_expiry_valid = false;
  let cardExpiryEle = elements.create("cardExpiry", {
    style: {
      base: {
        fontSize: "16px",
        color: "#32325d",
        "::placeholder": {
          color: "#aab7c4",
        },
      },
      invalid: {
        color: "#dc3545",
      },
    },
  });
  cardExpiryEle.mount("#card_expiry_div");
  // Card Expiry Change Event
  cardExpiryEle.on("change", function (event) {
    $("#card_expiry_error").html("");
    if (event.error) {
      $("#card_expiry_error").html("Your card was expired.");
    } else if (event.complete) {
      card_expiry_valid = true;
    }
  });

  // Creating Card CVV Element
  card_cvv_valid = false;
  let cardCvcEle = elements.create("cardCvc", {
    style: {
      base: {
        fontSize: "16px",
        color: "#32325d",
        "::placeholder": {
          color: "#aab7c4",
        },
      },
      invalid: {
        color: "#dc3545",
      },
    },
  });
  cardCvcEle.mount("#card_cvc_div");
  // Card CVV Change Event
  cardCvcEle.on("change", function (event) {
    $("#card_cvv_error").html("");
    if (event.error) {
      $("#card_cvv_error").html(event.error.message);
    } else if (event.complete) {
      card_cvv_valid = true;
    }
  });

  // On Submit Button Click Event
  $("#validate").on("click", function () {
    $("#common_error").html("");

    if (!full_name) {
      $("#full_name_error").html("Enter full name or Company.");
      personal_data_valid = false;
    }
    if (!city) {
      $("#city_error").html("Enter city name.");
      personal_data_valid = false;
    }
    if (!zip) {
      $("#zip_error").html("Enter Zip.");
      personal_data_valid = false;
    }

    // Checking All Fields Are Correct
    if (
      card_number_valid &&
      card_expiry_valid &&
      card_cvv_valid &&
      personal_data_valid
    ) {
      addLoader();
      // Create Payment Method
      stripe
        .createPaymentMethod({
          type: "card",
          card: cardNumberEle,
          billing_details: {
            name: full_name,
            address: {
              city: city,
              country: country,
              line1: full_name + ", " + city,
              line2: city + ", " + country + "-" + zip + ".",
              postal_code: zip,
            },
          },
        })
        .then(function (result) {
          if (result.error) {
            removeLoader();
            $("#common_error").html("result.error");
          } else {
            let paymentMethodId = result.paymentMethod.id;

            // AJAX Call for Payment Method ID
            $.ajax({
              url: "/payment/complete/",
              type: "POST",
              headers: {
                "X-Requested-With": "XMLHttpRequest",
                "X-CSRFToken": getCookie("csrftoken"),
              },
              contentType: "application/json",
              data: JSON.stringify({
                stripe_payment_method_id: paymentMethodId,
              }),
              success: function (result) {
                removeLoader();
                if (result["error_message"]) {
                  if (result["error"]["message"]) {
                    $("#common_error").html(`${result["error"]["message"]}`);
                  } else {
                    $("#common_error").html(`${result["error_message"]}`);
                  }
                }
                if (result["payment_status"]) {
                  window.location.assign("/campaigns/update/");
                }
              },
              error: function (error) {
                console.log(`Error ${error}`);
              },
            });
          }
        });
    } else {
      $("#common_error").html("All fields must be completed.");
    }
  });
});
