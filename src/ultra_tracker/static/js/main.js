$(document).ready(function(){
    $(".tab-link").on("click", function(){
        var tabId = $(this).attr("href");
        $(".tab-content").removeClass("active");
        $(".tab-link").removeClass("active"); // Remove active class from all tabs
        $(this).addClass("active"); // Add active class to the clicked tab
        $(tabId).addClass("active");
        // Store selected tab in local storage
        localStorage.setItem('selectedTab', tabId);
    });
    // Check if there's a selected tab in local storage and activate it
    var selectedTab = localStorage.getItem('selectedTab');
    if (selectedTab) {
        $(selectedTab).addClass('active');
        $('a[href="' + selectedTab + '"]').addClass('active');
    }
});


document.addEventListener('DOMContentLoaded', function() {
  Prism.highlightAll();
});
