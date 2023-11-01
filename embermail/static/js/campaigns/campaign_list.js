$(document).ready(() => {
  // Debounce function implementation
  function debounce(func, wait) {
    let timeout;
    return function executedFunction(args) {
      const later = () => {
        timeout = null;
        func.apply(this, args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  }

  function ajaxCallSearching() {
    const search_value = $("#campaign_list_search").val();
    $.ajax({
      url: "/campaigns/list/search/",
      type: "POST",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      data: JSON.stringify({
        search_value: search_value,
      }),
      success: function (result) {
        $("#campaign_list_tbody").remove();
        $("#campaign_list_table").append(result);
      },
      error: function (error) {
        console.log(`Error ${error}`);
      },
    });
  }

  // Attach input event with debouncing
  const inputDelay = 500; // Set the delay time in milliseconds
  $(document).on(
    "input",
    "#campaign_list_search",
    debounce(ajaxCallSearching, inputDelay)
  );

  // Play and Pause Campaign
  $(document).on("click", ".play_pause_button", function (e) {
    campaign_id = e.currentTarget.id;
    $.ajax({
      url: "/campaigns/list/",
      type: "POST",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      data: JSON.stringify({
        ajax_call_for: "play_pause",
        campaign_id: campaign_id,
      }),
      success: function (result) {
        if(result['error_tag'] == 'payment_required'){
          window.location.assign(`/payment/plan/selection/?campaign=${campaign_id}`)
        } else if(result['error_tag'] == 'complete_required_steps'){
            window.location.assign('/campaigns/joining/flow/imap-access-details/')
        }else{
          window.location.reload(true);
        }
    
      },
      error: function (error) {
        console.log(`Error ${error}`);
      },
    });
  });

  // Show Modal with Campaign Details
  $(document).on("click", ".edit_button", function (e) {
    $("#send_invitation_btn").addClass("d-none");
    $("#cancel_subscription_message").addClass("d-none");
    campaign_id = e.currentTarget.id.split("_")[0];
    $.ajax({
      url: "/campaigns/list/",
      type: "POST",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      data: JSON.stringify({
        ajax_call_for: "edit",
        campaign_id: campaign_id,
      }),
      success: function (result) {
        let campaign = JSON.parse(result["campaign"]);
        $("#modal_email").text(`${campaign["email"]}`);
        $("#modal_plan").text(`${campaign["plan_name"]}`);
        if (campaign['is_cancelled']){
          // Remove Next Invoice Text and Add Cancelled at and Add Cancelled Message
          $("#next_invoice_or_cancelled").html("Cancelled At");
          $("#cancel_subscription_message").html(`**Subscription was cancelled. Campaign will be stopped on ${campaign["next_invoice_date"]}.`)
          $("#cancel_subscription_message").removeClass("d-none");
          // Remove All Buttons and Add Make Payment Button
          $("#cancel_subscription_btn").remove();
          // $("#button_div").empty();
          // $("#button_div").append(
          //   `<a href="/payment/plan/selection/?campaign=${campaign_id}" class="btn save-btn upgrade-btn submit-btn">Make Payment</a>`
          // );
        };
        $("#modal_next_invoice").text(`${campaign["next_invoice_date"]}`);
        if (campaign["plan_amount_per_month"]) {
          $("#modal_payment_amount").html(
            `$${campaign["plan_amount_per_month"]} <span>Per Month</span>`
          );
        } else {
          $("#modal_payment_amount").html("-");
          // Remove All Buttons and Add Make Payment Button
          $("#button_div").empty();
          $("#button_div").append(
            `<a href="/payment/plan/selection/?campaign=${campaign_id}" class="btn save-btn upgrade-btn submit-btn">Make Payment</a>`
          );
        };
        if (!campaign["user_id"]) {
          let hiddenText = `${campaign['email']}break_pointcampaign_list`
          $("#send_invitation_btn").attr('href', `/campaigns/send-invitation-link/${hiddenText}/`);
          $("#send_invitation_btn").removeClass("d-none");
        };
        $("#modal_domain_type").text(`${campaign["domain_type"]}`);
        let campaign_status = campaign["status"];
        if (campaign_status != "Running") {
          $("#modal_status").removeClass("active-text");
          $("#modal_status").addClass("red-text");
        } else {
          $("#modal_status").removeClass("red-text");
          $("#modal_status").addClass("active-text");
        }
        $("#modal_status").text(`${campaign_status}`);
        $("#campaign_detail_modal").modal("show");

        // Update href attribute of Schedule Edit Button
        editScheduleUrl = `/campaigns/update/?email=${campaign["email"]}`;
        $("#schedule_edit_btn").attr("href", editScheduleUrl);

        // Showing Cancel Subscription Modal and Hiding Info Modal
        $("#cancel_subscription_btn").on("click", () => {
          $("#fill_email_span").text(`${campaign["email"]}`);
          $("#cancel_subscription_modal").modal("show");
          $("#campaign_detail_modal").modal("hide");
        });

        // Back Button of Cancel Subscription Modal Click Event
        $("#subscription_modal_back_btn").on("click", () => {
          window.location.reload(true);
        });

        // Cancel Subscription Button Click Event with Ajax Call
        $("#cancel_subscription_modal_btn").on("click", () => {
          $.ajax({
            url: "/campaigns/cancel/subscription/",
            type: "POST",
            headers: {
              "X-Requested-With": "XMLHttpRequest",
              "X-CSRFToken": getCookie("csrftoken"),
            },
            data: JSON.stringify({
              warmup_email: campaign["email"],
            }),
            success: function (result) {
              window.location.reload(true);
            },
            error: function (error) {
              console.log(`Error ${error}`);
            },
          });
        });
      },
      error: function (error) {
        console.log(`Error ${error}`);
      },
    });
  });
});
