

$(function () {
  "use strict";

  // Active menu
  $(function () {
    for (var e = window.location, o = $(".navbar-nav .dropdown-item").filter(function () {
      return this.href == e
    }).addClass("active").parent().addClass("active"); o.is("li");) o = o.parent("").addClass("").parent("").addClass("")
  }),


    // back to top //
    $(document).ready(function () {
      $(window).on("scroll", function () {
        $(this).scrollTop() > 300 ? $(".back-to-top").fadeIn() : $(".back-to-top").fadeOut()
      }), $(".back-to-top").on("click", function () {
        return $("html, body").animate({
          scrollTop: 0
        }, 600), !1
      })
    }),



    /* Theme switcher */
    $("#LightTheme").on("click", function () {
      $("html").attr("data-bs-theme", "light");
      localStorage.setItem('theme', 'light');
    }),

    $("#DarkTheme").on("click", function () {
      $("html").attr("data-bs-theme", "dark");
      localStorage.setItem('theme', 'dark');
    }),

    /* Theme toggle button */
    $("#themeToggleBtn").on("click", function () {
      const currentTheme = $("html").attr("data-bs-theme");
      const newTheme = currentTheme === "light" ? "dark" : "light";
      $("html").attr("data-bs-theme", newTheme);
      localStorage.setItem('theme', newTheme);

      // Update radio buttons in the switcher panel
      if (newTheme === "light") {
        $("#LightTheme").prop("checked", true);
      } else {
        $("#DarkTheme").prop("checked", true);
      }
    }),

    /* Load saved theme on page load */
    $(document).ready(function() {
      const savedTheme = localStorage.getItem('theme') || 'light';
      $("html").attr("data-bs-theme", savedTheme);

      // Remove any extra theme options that shouldn't be there
      $("#BlueTheme, #SemiDarkTheme, #BoderedTheme").closest('.col-12').remove();

      // Update radio buttons
      if (savedTheme === "light") {
        $("#LightTheme").prop("checked", true);
      } else {
        $("#DarkTheme").prop("checked", true);
      }
    }),

    /* Force remove extra theme options on DOM ready */
    $(document).ready(function() {
      // Wait a bit for any dynamic content to load, then remove extra themes
      setTimeout(function() {
        $("#BlueTheme, #SemiDarkTheme, #BoderedTheme").closest('.col-12').remove();
        $('input[name="theme-options"]:not(#LightTheme):not(#DarkTheme)').closest('.col-12').remove();
      }, 100);
    })





  // dropdown slide

  $('.dropdown-menu a.dropdown-toggle').on('click', function (e) {
    if (!$(this).next().hasClass('show')) {
      $(this).parents('.dropdown-menu').first().find('.show').removeClass("show");
    }
    var $subMenu = $(this).next(".dropdown-menu");
    $subMenu.toggleClass('show');


    $(this).parents('li.nav-item.dropdown.show').on('hidden.bs.dropdown', function (e) {
      $('.submenu .show').removeClass("show");
    });


    return false;
  });




});










