$(document).ready(function (){
    // this depends on the id's used for different tab-panes in modify.html (Basic Theme)
    var edit = false;
    $('#meta, #help').removeClass('active');
    $('#password, #notification, #ui, #navigation, #options, #acl, #subscriptions').removeClass('active');
    $('textarea').autosize();
    $('div.dropup').removeClass('menu');
    $('ul.dropdown-menu').removeClass('submenu');
    $('.topnavcollapse').addClass('collapse');
    $('.moin-navbar-collapse').removeClass('in');
});
