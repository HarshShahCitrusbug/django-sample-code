$(document).ready(() => {
  // Focus on Submit Button
  $("#save_button").focus();
  
  // select dropdown js
  // Change option selected
  const label = document.querySelector(".dropdown__filter-selected");
  const options = Array.from(
    document.querySelectorAll(".dropdown__select-option")
  );

  options.forEach((option) => {
    option.addEventListener("click", () => {
      label.textContent = option.textContent;
    });
  });

  // Close dropdown onclick outside
  document.addEventListener("click", (e) => {
    const toggle = document.querySelector(".dropdown__switch");
    const element = e.target;

    if (element == toggle) return;

    const isDropdownChild = element.closest(".dropdown__filter");

    if (!isDropdownChild && toggle) {
      toggle.checked = false;
    }
  });

  $("#max_emails").attr("disabled", "disabled");
  $("#step_up").attr("disabled", "disabled");

  let selectedCampaignId = "new_domain";

  $("#domain_options li").on("click", (e) => {
    let selectedTarget = e.currentTarget;
    selectedCampaignId = selectedTarget.id;
    let selectedCampaignName = selectedTarget.dataset.name;
    let selectedCampaignMaxEmail = selectedTarget.dataset.max_emails;
    let selectedCampaignStepUp = selectedTarget.dataset.step_up;

    $("#max_emails").attr("disabled", "disabled");
    $("#step_up").attr("disabled", "disabled");

    $("#selected_domain_option").html(selectedCampaignName);

    $("#max_emails").val(selectedCampaignMaxEmail);
    $("#step_up").val(selectedCampaignStepUp);

    if (selectedCampaignId == "custom") {
      $("#max_emails").removeAttr("disabled");
      $("#step_up").removeAttr("disabled");
    }
  });

  $("#save_button").on("click", function () {
    $("#common_error").html("");
    let maxEmailPerDay = $("#max_emails").val();
    let stepUp = $("#step_up").val();
    // let campaignType = $("#dropdown_link").text()

    if (selectedCampaignId && maxEmailPerDay && stepUp) {
      addLoader();
      let url = "/campaigns/update/";
      if (window.location.href.indexOf("joining") > -1) {
        url = "/campaigns/joining/flow/update/";
      }
      $.ajax({
        url: url,
        type: "POST",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": getCookie("csrftoken"),
        },
        data: JSON.stringify({
          max_emails_per_day: maxEmailPerDay,
          step_up: stepUp,
          campaign_type: selectedCampaignId,
        }),
        success: function (result) {
          removeLoader();
          if (result["redirect"]) {
            window.location.assign(result["redirect"]);
          }
          if (result["error_message"]) {
            $("#common_error").html(result["error_message"]);
          }
        },
        error: function (error) {
          console.log(`Error ${error}`);
        },
      });
    }
  });
});
