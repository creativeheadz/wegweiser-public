

$(function () {
  "use strict";

  // Active menu
  $(function() {
		for (var e = window.location, o = $(".navbar-nav .dropdown-item").filter(function() {
				return this.href == e
			}).addClass("active").parent().addClass("active"); o.is("li");) o = o.parent("").addClass("").parent("").addClass("")
	}),

  
  // back to top //
  $(document).ready(function() {
    $(window).on("scroll", function() {
      $(this).scrollTop() > 300 ? $(".back-to-top").fadeIn() : $(".back-to-top").fadeOut()
    }), $(".back-to-top").on("click", function() {
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

  /* Load saved theme on page load */
  $(document).ready(function() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    $("html").attr("data-bs-theme", savedTheme);

    // Update radio buttons
    if (savedTheme === "light") {
      $("#LightTheme").prop("checked", true);
    } else {
      $("#DarkTheme").prop("checked", true);
    }
  })




  
// dropdown slide

  $('.dropdown-menu a.dropdown-toggle').on('click', function(e) {
		if (!$(this).next().hasClass('show')) {
		  $(this).parents('.dropdown-menu').first().find('.show').removeClass("show");
		}
		var $subMenu = $(this).next(".dropdown-menu");
		$subMenu.toggleClass('show');
	  
	  
		$(this).parents('li.nav-item.dropdown.show').on('hidden.bs.dropdown', function(e) {
		  $('.submenu .show').removeClass("show");
		});
	  
	  
		return false;
	  });




});










