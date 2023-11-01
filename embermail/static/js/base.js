$(document).ready(function () {
  // Automatic Fade Out Messages (Alerts)
  fadeOutMessageAutomatic();

  new WOW({}).init(),
    $("a.smoth-scroll").on("click", function (t) {
      var e = $(this);
      $("html, body")
        .stop()
        .animate({ scrollTop: $(e.attr("href")).offset().top - 70 }, 1500),
        t.preventDefault();
    });
  
    // sticky header js
  var headertopoption = $(window);
  var headTop = $(".header");

  headertopoption.on("scroll", function () {
    if (headertopoption.scrollTop() > 50) {
      headTop.addClass("fixed-top slideInDown animated");
    } else {
      headTop.removeClass("fixed-top slideInDown animated");
    }
  });

  // sidebar js
  hide = true;
  $("body").on("click", function () {
    if (hide) $(".em_sidebar").removeClass("open");
    hide = true;
  });

  // add and remove .active
  $("body").on("click", ".em_hamburger", function () {
    var self = $(".em_sidebar");

    if (self.hasClass("open")) {
      $(".em_sidebar").removeClass("open");
      return false;
    }

    $(".em_sidebar").removeClass("open");

    self.toggleClass("open");
    hide = false;
  });
});
