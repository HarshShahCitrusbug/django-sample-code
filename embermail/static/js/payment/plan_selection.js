$(document).ready(() => {
  $("#plan_selection_continue_btn").on("click", () => {
    let selected_plan = $("input[name='plan-list']:checked");
    let plan_id = selected_plan.attr("id");
    if (selected_plan.length >= 1 && plan_id) {
      window.location.assign(`/payment/complete/?plan=${plan_id}`);
    } else {
      $("#plan_selection_error").html(
        "You missed Plan selection. Please, Select anyone Plan."
      );
    }
  });
});
