$(document).ready(function (){
    // this depends on the id's used for different tab-panes in modify.html (Basic Theme)
    var edit = false;
    $('#meta, #help').removeClass('active');
    $('#password, #notification, #ui, #navigation, #options').removeClass('active');
    $('textarea').autosize();
    window.onbeforeunload = function(e) {
        // checks if the URL is of the form http://host/+modify/page
        var index = $.inArray("+modify", window.location.pathname.split('/'));
        if (index == 1) {
    		return "Data you may have entered will be discarded!";
    	}
    }
    $('div.dropup').removeClass('menu');
    $('ul.dropdown-menu').removeClass('submenu');
});
