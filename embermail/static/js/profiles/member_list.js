$(document).ready(() => {
  $(document).on("click", ".member_list_arrow", function(e) {
    $("#send_invitation_btn").addClass('d-none');
    campaign_id = e.currentTarget.id;
    $.ajax({
      url: "/profiles/member/list/",
      type: "POST",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      data: JSON.stringify({
        campaign_id: campaign_id,
      }),
      success: function (result) {
        if (result["redirect"]) {
          window.location.assign(`${result["redirect"]}`);
        } else if (result["campaign"]) {
          let campaign = JSON.parse(result["campaign"]);
          $("#modal_email").text(`${campaign["email"]}`);
          let first_name = campaign["first_name"]
          if (first_name){
            $("#modal_name").text(`${first_name}`);
          };
          $("#modal_plan").text(`${campaign["plan_name"]}`);
          $("#modal_payment_amount").html(
            `$${campaign["plan_amount"]} <span>Per Month</span>`
          );
          $("#modal_next_invoice").text(`${campaign["next_invoice"]}`);
          $("#modal_domain_type").text(`${campaign["domain_type"]}`);
          let campaign_status = campaign["status"]
          if (campaign_status != 'Active'){
            $("#modal_status").removeClass('active-text')
            $("#modal_status").addClass('red-text')
          }else{
            $("#modal_status").removeClass('red-text')
            $("#modal_status").addClass('active-text')
          };
          $("#modal_status").text(`${campaign_status}`);
          if (!campaign['user_id']){
            let hiddenText = `${campaign['email']}break_pointmember_list`
            $("#send_invitation_btn").attr('href', `/campaigns/send-invitation-link/${hiddenText}/`);
            $("#send_invitation_btn").removeClass('d-none');
          };
          $("#member_detail_modal").modal("show");
        }
      },
      error: function (error) {
        console.log(`Error ${error}`);
      },
    });
  });

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

  function performAjaxCall() {
    const search_value = $("#member_list_search").val();
    $.ajax({
      url: "/profiles/member/list/search/",
      type: "POST",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      data: JSON.stringify({
        search_value: search_value,
      }),
      success: function (result) {
        $("#member_list_tbody").remove();
        $("#member_list_table").append(result);
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
    "#member_list_search",
    debounce(performAjaxCall, inputDelay)
  );
});
