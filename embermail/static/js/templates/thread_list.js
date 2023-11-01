$(document).ready(() => {
  // CK Editor for Add New Thread
  let editorContent;
  DecoupledEditor.create(document.querySelector("#editor"))
    .then((editor) => {
      const toolbarContainer = document.querySelector("#toolbar-container");

      toolbarContainer.appendChild(editor.ui.view.toolbar.element);
      editorContent = editor;
    })
    .catch((error) => {
      console.error(error);
    });

  // CK Editor for Edit Thread
  let edit_editorContent;
  DecoupledEditor.create(document.querySelector("#edit_editor"))
    .then((edit_editor) => {
      const editToolbarContainer = document.querySelector(
        "#edit_toolbar-container"
      );

      editToolbarContainer.appendChild(edit_editor.ui.view.toolbar.element);
      edit_editorContent = edit_editor;
    })
    .catch((error) => {
      console.error(error);
    });

  let template_id = $("#template_id").html();

  // Edit threads
  $(".edit_buttons").on("click", (e) => {
    let thread_id = e.currentTarget.id.split("_")[0];
    let thread_body = e.currentTarget.dataset.body;
    edit_editorContent.setData(thread_body);

    $("#edit_thread_btn").on("click", () => {
      let updated_body = edit_editorContent.getData();

      if (updated_body != "") {
        // AJAX for Edit threads
        $.ajax({
          url: "/templates/threads/update/",
          type: "POST",
          headers: {
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRFToken": getCookie("csrftoken"),
          },
          data: JSON.stringify({
            template_id: template_id,
            thread_id: thread_id,
            body: updated_body,
          }),
          success: function (result) {
            if (result["redirect"]) {
              window.location.assign(result["redirect"]);
            }
          },
          error: function (error) {
            console.log(`Error ${error}`);
          },
        });
      } else {
        $("#edit_thread_error").html("Thread Body field is required.");
      }
    });
  });

  // Add New Thread
  $("#add_thread_btn").on("click", () => {
    let body = editorContent.getData();
    if (body != "") {
      $.ajax({
        url: "/templates/threads/add/",
        type: "POST",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": getCookie("csrftoken"),
        },
        data: JSON.stringify({
          template_id: template_id,
          body: body,
        }),
        success: function (result) {
          if (result["redirect"]) {
            window.location.assign(result["redirect"]);
          }
        },
        error: function (error) {
          console.log(`Error ${error}`);
        },
      });
    } else {
      $("#add_thread_error").html("Thread Body field is required.");
    }
  });

  // Delete threads
  $(".delete_buttons").on("click", (e) => {
    let thread_id = e.currentTarget.id.split("_")[0];

    $("#delete_thread_modal").modal("show");
    $(document).on("click", "#delete_thread_btn", function () {
      $.ajax({
        url: "/templates/threads/delete/",
        type: "POST",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": getCookie("csrftoken"),
        },
        data: JSON.stringify({
          thread_id: thread_id,
          template_id: template_id,
        }),
        success: function (result) {
          if (result["redirect"]) {
            window.location.assign(result["redirect"]);
          }
        },
        error: function (error) {
          console.log(`Error ${error}`);
        },
      });
    });
  });
});
