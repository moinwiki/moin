$(document).ready(function (){
    // this depends on the id's used for different tab-panes in modify.html (Basic Theme)
    var edit = false;
    $('#meta, #help').removeClass('active');
    $('#password, #notification, #ui, #navigation, #options, #acl, #subscriptions').removeClass('active');
    $('textarea').autosize();
    $('#moin-save-text-button').click(function (){
        edit = true;
    });
    window.onbeforeunload = function(e) {
        // previously checked if the URL is of the form http://host/+modify/page
        // it is bad way if we rewrite URL's, hence used a div with id -> "checkmodifyview" in the modify view
        var test = $('#checkmodifyview').length;
        if (test == 1 && edit == false) {
    		return "Data you may have entered will be discarded!";
    	}
        edit = false;
    }
    $('div.dropup').removeClass('menu');
    $('ul.dropdown-menu').removeClass('submenu');
    $('.topnavcollapse').addClass('collapse');
    $('.moin-navbar-collapse').removeClass('in');
});
