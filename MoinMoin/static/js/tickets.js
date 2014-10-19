$(document).ready(function () {
    "use strict";
    $("table").tablesorter({
        widgets: ["resizable"],
        widgetOptions : {
            // css class name applied to the sticky header
            resizable : false
        },
        headers: {
            // remove sorting option for tags column
            7: { sorter: false }
        }
    });

    $('.moin-loginsettings').addClass('navbar-right');

    // executed when user clicks tickets tab tags button and conditionally on page load
    $('.ticket-tags-toggle').click(function () {
        // Toggle visibility tags
        var tags = $('.moin-ticket-tags');
        if (tags.is(':hidden')) {
            tags.show();
            $('.ticket-tags-toggle').attr('title', _("Hide tags")).addClass('active');
        } else {
            tags.hide();
            $('.ticket-tags-toggle').attr('title', _("Show all tags")).removeClass('active');
            location.search = '';
        }
    });
    // ticket tags are initially hidden by css; if a tag is selected: show the tags
    if (location.search.indexOf("selected_tags") >= 0) {
        $('.ticket-tags-toggle').click();
    }
});
