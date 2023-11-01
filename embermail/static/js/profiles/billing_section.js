var download = function (urls) {
  for (var i = 0; i < urls.length; i++) {
    var iframe = $(
      '<iframe class="d-none" style="visibility: collapse;"></iframe>'
    );
    $("body").append(iframe);
    var content = iframe[0].contentDocument;
    var form = '<form action="' + urls[i] + '" method="GET"></form>';
    content.write(form);
    $("form", content).submit();
    setTimeout(
      (function (iframe) {
        return function () {
          iframe.remove();
        };
      })(iframe),
      20000
    );
  }
};

$(document).ready(() => {
  // For Download Invoices
  let selected_a_tags = [];

  $(document).on("click", "#select_all_invoices", function(e) {
    if (!e.target.checked) {
      selected_a_tags = [];
    }
  });

  $(document).on("change", "#select_all_invoices", function(e) {
    let all_checkboxes = $(".all_download_checkboxes");
    if (e.target.checked) {
      selected_a_tags = [];
      $.each(all_checkboxes, (index, checkbox) => {
        checkbox.checked = true;
        selected_a_tags.push(checkbox.value);
      });
    } else {
      $.each(all_checkboxes, (index, checkbox) => {
        checkbox.checked = false;
        selected_a_tags.splice(selected_a_tags.indexOf(checkbox.value), 1);
      });
    }
  });

  $(document).on("change", ".all_download_checkboxes", function(e){
    let selected_payment_url = e.currentTarget.value;
    if (e.target.checked) {
      selected_a_tags.push(selected_payment_url);
    } else {
      $("#select_all_invoices")[0].checked = false;
      selected_a_tags.splice(selected_a_tags.indexOf(selected_payment_url), 1);
    }
  });

  $(document).on("click", "#download_all_btn", function (e) {
    if (selected_a_tags.length == 0){
      addLoader();
      $("#select_all_invoices").click();
    }
    download(selected_a_tags);
    removeLoader();
  });

  // For Searching Functionality
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
    const search_value = $("#search_input_billing_history").val();
    $.ajax({
      url: "/profiles/billing/section/search/",
      type: "POST",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      data: JSON.stringify({
        search_value: search_value,
      }),
      success: function (result) {
        $("#invoice_table_div").empty();
        selected_a_tags = [];
        $("#invoice_table_div").append(result);
      },
      error: function (error) {
        console.log(`Error ${error}`);
      },
    });
  }

  // Attach input event with debouncing
  const inputDelay = 500; // Set the delay time in milliseconds
  $(document).on("input", "#search_input_billing_history", debounce(performAjaxCall, inputDelay));
});
