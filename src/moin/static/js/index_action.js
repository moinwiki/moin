/*
 * Click and submit handlers for form elements on the global index and subitem index pages.
 * Copyright 2011, AkashSinha<akash2607@gmail.com>
 * License: GNU GPL v2 (or any later version), see LICENSE.txt for details.
 */

/*jslint browser: true, nomen: true*/
/*global $:true, _:true */

// This anonymous function is executed once after a global index page loads.
$(function () {

    "use strict";

    // life expectancy of iframe used for file downloads
    const IFRAME_REMOVE_DELAY = 3000;

    // delete and destroy process started and completed messages
    var ACTION_LOADING = {'delete': _("Deleting.."),
                          'destroy': _("Destroying..")},
        ACTION_DONE = {'delete': _("Items deleted: "),
                       'destroy': _("Items destroyed: ")},
        ACTION_FAILED = {'delete': _(", Not authorized, items not deleted: "),
                         'destroy': _(", Not authorized, items not destroyed: ")},
        POPUP_DELETE_HEADER = _("Add optional comment for Delete change log. "),
        POPUP_DESTROY_HEADER = _("Add optional comment for Destroy change log. ");

    // return a list of item names having checked boxes
    function get_checked() {
        var checked_names = [];
        $("input.moin-item:checked").each(function () {
            var itemname = $(this).attr("value");
            checked_names.push(itemname);
        });
        return checked_names;
    }

    // add a list of all selected, alias, subitem, and rejected names to comment popup
    function get_subitem_names(action) {
        var checked_names = get_checked(),
            wiki_root = $('#moin-wiki-root').val(),
            checked_name,
            alias_names = [],
            subitem_names = [];
        $.ajax({
            url: wiki_root + "/+ajaxsubitems",
            type: "POST",
            dataType: "json",
            data: {item_names: checked_names, action_auth: action},
            success: (function(response) {
                $('input[name="selected-names"]').val(JSON.stringify(response.selected_names));
                if (response.rejected_names.length) {
                    $('p.popup-rejected-names > span').text(response.rejected_names.join(', '));
                    $('p.popup-rejected-names').removeClass("hidden");
                }
                $('p.popup-selected-names > span').text(response.selected_names.join(', '));
                $('p.popup-alias-names > span').text(response.alias_names.join(', '));
                $('p.popup-subitem-names > span').text(response.subitem_names.join(', '));
            }),
            error: (function(xhr, textstatus, message) {
                if(textstatus === "timeout") {
                    alert("Server operation timed out: " + "textstatus = "+ textstatus + ",  message = " + message);
                } else {
                    alert("Unknown server error =" + "textstatus = "+ textstatus + " message = " + message);
                }
            })
        })
    }

    // called by click handlers Delete item, and Destroy item within Actions dropdown menu
    function show_popup(action) {
        $('input[name="delete-action"]').val(action);
        // hide Actions popup and show Comment popup
        $(".popup-comment").val("");
        $(".popup-action").val(action);
        if (action === "delete") {
            $(".popup-header > span").html(POPUP_DELETE_HEADER);
        } else{
            $(".popup-header > span").html(POPUP_DESTROY_HEADER);
        }
        get_subitem_names(action);
        $("#popup").removeClass("hidden");
        $(".popup-comment").focus();
        $("#lightbox").css("display", "block");
    }

    // called by click handlers within "Create new item" and "Please provide comment" popups
    function hide_popup() {
        $("#popup").addClass("hidden");
        $("#lightbox").css("display", "none");
    }

    // called by Actions Download click handler
    function startFileDownload(elem) {
        // create a hidden iframe to start a file download, then remove it after 3 seconds
        var frame = $('<iframe style="display: none;"></iframe>');
        frame.attr('src', $(elem).attr('href'));
        $(elem).after(frame);
        setTimeout(function () { frame.remove(); }, IFRAME_REMOVE_DELAY);
    }

    // executed via the "provide comment" popup triggered by an Actions Delete or Destroy selection
    function do_action(itemnames, comment, action) {
        $("#popup").addClass("hidden");
        // remove any flash messages, display "deleting..." or "destroying..." flash msg while process is in progress
        // note the parent of .moin-flash messages is #moin-flash; moin-flash is used as both id and class
        $(".moin-flash").remove();
        MoinMoin.prototype.moinFlashMessage(MoinMoin.prototype.MOINFLASHINFO, ACTION_LOADING[action]);
        // create a transaction to delete or destroy selected items
        const actionTrigger = `moin-${action}-trigger`;
        const url = $("#" + actionTrigger).attr("data-actionurl");
        // outgoing itemnames is an array of checked item names; comment is from text field of popup,
        // do_subitems is state of checkbox - true if subitems are to be processed
        const data = {
            action: action,
            itemnames: itemnames,
            comment: comment,
            do_subitems: $('input[name="moin-do-subitems"]').is(":checked")
        };
        $.ajax({
            type: "POST",
            url: url,
            contentType: "application/json; charset=utf-8",
            data: JSON.stringify(data),
            dataType: "json",
        }).done(function (data) {
            // incoming itemnames is list of item names (including alias names) successfully deleted/destroyed
            const itemnames = data.itemnames;
            // display success/fail flash messages created by server for each selected item and subitem
            for (let idx = 0; idx < data.messages.length; idx += 1) {
                MoinMoin.prototype.moinFlashMessage(MoinMoin.prototype.MOINFLASHINFO, data.messages[idx]);
            }
            // remove index rows for all deleted/destroyed items; including alias names (items with alias names have multiple rows)
            $.each(itemnames, function (itemindex, itemname) {
                const isLastElement = itemindex == itemnames.length - 1;
                $('input[value="' + itemname + '"]').parent().parent().parent().remove();
                if (isLastElement) {
                    MoinMoin.prototype.moinFlashMessage(MoinMoin.prototype.MOINFLASHINFO, _("Action complete."));
                    // update item count in upper left of table
                    $(".moin-num-rows").text($('.moin-index tbody tr').length);
                    // remove Deleting... flash message
                    $('#moin-flash').find('p').first().remove();
                }
            });
        });
    }

    // hide the upload button (used when javascript is disabled)
    $("#upload-file-btn").addClass("hidden");

    // add click handler to "Select All" tab to select/deselect all items
    $(".moin-select-toggle").on("change", function () {
        if ($(this).find("input").prop("checked")) {
            $(".moin-select-item > input.moin-item").each(function () {
                $(this).prop('checked', true);
            });
        } else {
            $(".moin-select-item > input.moin-item").each(function () {
                $(this).prop('checked', false);
            });
        }
    });

    // add click handler to Cancel buttons and red "X" on Delete, Destroy popups
    $('button[name="popup-cancel"], button[name="popup-close"]').on("click", function () {
        hide_popup();
        return false;
    });

    // add click handler to "Download" button of Actions dropdown
    $("#moin-download-trigger").on("click", function (event) {
        event.preventDefault();
        if (!($(".moin-item:checked").length)) {
            $(".moin-flash").remove();
            MoinMoin.prototype.moinFlashMessage(MoinMoin.prototype.MOINFLASHWARNING, _("Download failed, no items were selected."));
        } else {
            // download selected files
            $(".moin-item:checked").siblings(".moin-download-link").each(function (index, element) {
                startFileDownload(element);
            });
            $("input.moin-item:checked").prop('checked', false);
        }
    });

    // add click handler to "Delete" and "Destroy" buttons of Actions dropdown
    $(".moin-action-tab").on("click", function (event) {
        event.preventDefault();
        const action = this.getAttribute("data-action");
        // Show error msg if nothing selected, else show comment popup. Hide actions dropdown.
        if (!($(".moin-item:checked").length)) {
            $(".moin-flash").remove();
            MoinMoin.prototype.moinFlashMessage(MoinMoin.prototype.MOINFLASHWARNING, action + ' failed, no items were selected.');
        } else {
            show_popup(action);
        }
        return false;
    });

    // add click handler to "Submit" button on "Please provide comment..." popup
    $('button[name="popup-submit"]').on("click", function (event) {
        event.preventDefault();
        // process delete or destroy action
        const itemnames = JSON.parse($('input[name="selected-names"]').val());
        const comment = $('input[name="moin-comment"]').val().trim();
        const action = $('input[name="delete-action"]').val();
        do_action(itemnames, comment, action);
        hide_popup();
        return false;
    });

    // add click handler to "Toggle" button on "Filter by content type" dropdown
    $(".moin-filter-toggle").on("click", function (event) {
        event.preventDefault();
        // reverse checked/unchecked for each content type
        $(".moin-contenttype-selection").find("input[type='checkbox']").each(function () {
            $(this).prop('checked', !$(this).is(':checked'));
        });
        return false;
    });

    // Filter, Namespace, New Item buttons have similar actions, show last clicked action, hide others
    // add click handler to toggle button for content type "Filter" dropdown
    $(".moin-ct-toggle").on("click", function (event) {
        event.preventDefault();
        // show/hide content type selection
        $(".moin-contenttype-selection").toggleClass("hidden");
        $(".moin-namespace-selection").addClass("hidden");
        $(".moin-newitem-selection").addClass("hidden");
        return false;
    });

    // add click handler to toggle button on "Namespace" dropdown
    $(".moin-ns-toggle").on("click", function (event) {
        event.preventDefault();
        // show/hide namespace selection
        $(".moin-namespace-selection").toggleClass("hidden");
        $(".moin-contenttype-selection").addClass("hidden");
        $(".moin-newitem-selection").addClass("hidden");
        return false;
    });

    // add click handler to toggle button on "New Item" dropdown
    $(".moin-newitem-toggle").on("click", function (event) {
        event.preventDefault();
        // show/hide new item selection
        $(".moin-newitem-selection").toggleClass("hidden");
        $(".moin-contenttype-selection").addClass("hidden");
        $(".moin-namespace-selection").addClass("hidden");
        return false;
    });

    // add click handlers to all items shown on global index page
    $(".moin-select-item").on("click", function () {
        // toggle selection classes
        $(this > "input[type='checkbox']").prop('checked', !$(this > "input[type='checkbox']").is(':checked'));
        if ($(this).parent().hasClass("selected-item")) {
            $(this).parent().removeClass("selected-item");
            if ($(".moin-select-allitem").hasClass("allitem-selected")) {
                $(".moin-select-allitem").removeClass("allitem-selected").addClass("allitem-toselect");
            }
        } else {
            $(this).parent().addClass("selected-item");
        }
    });

    // add item count to upper left of table
    $(".moin-num-rows").text($('.moin-index tbody tr').length);
});
