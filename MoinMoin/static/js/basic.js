/*jslint browser: true, nomen: true, todo: true*/
/*global $:true*/

$(document).ready(function () {
    // this depends on the id's used for different tab-panes in modify.html and usersettings.html (Basic Theme)
    "use strict";
    $('#meta, #help').removeClass('active');
    $('#password, #notification, #personal, #navigation, #options, #acl, #subscriptions').removeClass('active');
    $('textarea').autosize();
    $('div.dropup').removeClass('menu');
    $('ul.dropdown-menu').removeClass('submenu');
    $('.topnavcollapse').addClass('collapse');
    if ($('li.active > a.moin-modify-button').length) {
        $('.moin-loginsettings').addClass('moin-pull-right');
    }
    // Support for extra small viewports, sidebar is initially hidden by CSS, made visible when user clicks button
    $('#hideshowsidebar').click(function() {
        $('#moin-main-wrapper').toggleClass('showsidebar');
    });
});
