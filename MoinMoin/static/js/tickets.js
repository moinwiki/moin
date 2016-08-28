/*global $, _*/

$(document).ready(function () {
    "use strict";

    function post_comment(reply_to, refers_to, data) {
        var wiki_root = $('#moin-wiki-root').val();
        $.ajax({
            type: "POST",
            url: wiki_root + "/+comment",
            data: {reply_to: reply_to, refers_to: refers_to, data: data}
        }).done(function (html) {
            location.reload(true);
        });
    }

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

    // executed when user clicks Reply button to respond to a prior comment
    $('.reply').click(function (e) {
        e.preventDefault();
        var reply_to = $(this).attr('data-reply_to');
        var refers_to = $(this).attr('data-refers_to');
        var reply_insert = '<div class="comment-box">' +
                '<textarea class="comment-reply" type="text" />' +
                '<p>' +
                '<button type="button" class="moin-button" id="save">Save</button>' +
                '<button type="button" class="moin-button" id="cancel">Cancel</button>' +
                '</p>' +
                '</div>';
        if (!$('#' + reply_to).find("textarea.comment-reply").length) {
            $('#' + reply_to).append(reply_insert);
            $('#' + reply_to).find("textarea.comment-reply").focus();
            // add click actions to Save and Cancel buttons created above
            $('#save').on('click', function (e) {
                var data = $('textarea.comment-reply').val();
                $('div.comment-box').remove();
                post_comment(reply_to, refers_to, data);
                return false;
            });
            $('#cancel').on('click', function (e) {
                $('div.comment-box').remove();
                return false;
            });
        }
    });

    $(".jumper").on("click", function (e) {
        e.preventDefault();
        $("body, html").animate({
            scrollTop: $($(this).attr('href')).offset().top
        }, 600);
    });

    // when user clicks the tag, it is added to input field
    $('.moin-ticket-tags a').click(function () {
        var value = $(this).text();
        var input = $('#f_meta_tags');
        if (!input.val()) {
            input.val(value);
        } else {
            input.val(input.val() + ', ' + value);
        }
        return false;
    });
});
