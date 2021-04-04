/*
 * Click and submit handlers for form elements on the global index and subitem index pages.
 * Copyright 2011, AkashSinha<akash2607@gmail.com>
 * License: GNU GPL v2 (or any later version), see LICENSE.txt for details.
 */

/*jslint browser: true, nomen: true*/
/*global $:true, _:true */

// This anonymous function is executed once after a global index page loads.
$("document").ready(function () {
    "use strict";

    var POPUP_FADE_TIME = 200, // fade in, fade out times for selected popups
        IFRAME_CREATE_DELAY = 200, // delay between start of multiple downloads
        IFRAME_REMOVE_DELAY = 3000, // life expectancy of iframe used for file downloads
        // delete and destroy process started and completed messages
        ACTION_LOADING = {'delete': _("Deleting.."), 'destroy': _("Destroying..")},
        ACTION_DONE = {'delete': _("Items deleted: "), 'destroy': _("Items destroyed: ")},
        ACTION_FAILED = {'delete': _(", Not authorized, items not deleted: "), 'destroy': _(", Not authorized, items not destroyed: ")};

    // called by click handlers New Item, Delete item, and Destroy item within Actions dropdown menu
    function showpop(action) {
        // hide Actions popup and show either New Item or Comment popup
        $(".popup-container").css("display", "none");
        $("#popup-for-action").css("display", "block");
        $(".popup-comment").val("");
        $(".popup-action").val(action);
        $("#popup").fadeIn();
        $(".popup-comment").focus();
        $("#lightbox").css("display", "block");
    }

    // called by click handlers within "Create new item" and "Please provide comment" popups
    function hidepop() {
        // hide popup
        $("#popup").css("display", "none");
        $("#lightbox").css("display", "none");  // qqq
    }

    // called by Actions Download click handler
    function startFileDownload(elem) {
        // create a hidden iframe to start a file download, then remove it after 3 seconds
        var frame = $('<iframe style="display: none;"></iframe>');
        frame.attr('src', $(elem).attr('href'));
        $(elem).after(frame);
        setTimeout(function () { frame.remove(); }, IFRAME_REMOVE_DELAY);
    }

    // called by do_action when an item is successfully deleted or destroyed
    function hide(item_link) {
        // remove a deleted or destroyed item from current display
        item_link.parent().remove();
    }

    // called by do_action when item cannot be deleted or destroyed
    function show_conflict(item_link) {
        // highlight item that failed a delete or destroy operation
        item_link.addClass("moin-auth-failed");
        // cleanup display by unchecking checkbox and removing selected class
        item_link.prev().children().prop("checked", false);
        item_link.parent().removeClass("selected-item");
    }

    // executed via the "provide comment" popup triggered by an Actions Delete or Destroy selection
    function do_action(comment, action) {
        // create an array of selected item names
        var links = [],
            itemnames,
            actionTrigger,
            url;
        $(".selected-item").children().children("input.moin-item").each(function () {
            var itemname = $(this).attr("value").slice(1);
            links.push(itemname);
        });
        // remove any flash messages, display "deleting..." or "destroying..." briefly while process is in progress
        $("#popup").css("display", "none");
        // note the parent of .moin-flash messages is #moin-flash; moin-flash is used as both id and class
        $(".moin-flash").remove();
        MoinMoin.prototype.moinFlashMessage(MoinMoin.prototype.MOINFLASHINFO, ACTION_LOADING[action]);

        // create a transaction to delete or destroy selected items
        itemnames = JSON.stringify(links);
        actionTrigger = "moin-" + action + "-trigger";
        url = $("#" + actionTrigger).attr("data-actionurl");
        $.post(url, {
            itemnames: itemnames,
            comment: comment
        }, function (data) {
            // process post results
            var itemnames = data.itemnames,
                action_status = data.status,
                success_item = 0,
                left_item = 0,
                message;
            $.each(itemnames, function (itemindex, itemname) {
                // hide (remove) deleted/destroyed items, or show conflict (ACL rules, or ?)
                if (action_status[itemindex]) {
                    hide($('.selected-item'));
                    success_item += 1;
                } else {
                    show_conflict($('.selected-item').children('a.moin-item[href="/' + itemname + '"]'));
                    left_item += 1;
                }
            });
            // show a message summarizing delete/destroy
            message = ACTION_DONE[action] + success_item;
            if (left_item) {
                message += ACTION_FAILED[action] + left_item + ".";
            }
            $(".moin-flash").remove();
            MoinMoin.prototype.moinFlashMessage(MoinMoin.prototype.MOINFLASHWARNING, message);
        }, "json");
    }

    // add click handler to "Select All" tab to select/deselect all items
    $(".moin-select-allitem").click(function () {
        // toggle classes
        if ($(this).hasClass("allitem-toselect")) {
            $(".moin-index tbody tr td:first-child").removeClass().addClass("selected-item");
            $(this).removeClass("allitem-toselect").addClass("allitem-selected");
            $(this).children("i").removeClass("fa-square-o").addClass("fa fa-check-square-o");
            $(".moin-select-button-text").text(_("Deselect All"));
            $(".moin-select-item > input[type='checkbox']").each(function () {
                $(this).prop('checked', true);
            });
            $(".moin-auth-failed").removeClass("moin-auth-failed");
        } else {
            $(this).removeClass("allitem-selected").addClass("allitem-toselect");
            $(".moin-index tbody tr td:first-child").removeClass();
            $(this).children("i").removeClass("fa-check-square-o").addClass("fa-square-o");
            $(".moin-select-button-text").text(_("Select All"));
            $(".moin-select-item > input[type='checkbox']").each(function () {
                $(this).prop('checked', false);
            });
        }
    });

    // add click handler to Cancel buttons and red "X" on Delete, Destroy popups
    $(".popup-cancel").click(function () {
        hidepop();
    });

    // add click handler to "Download" button of Actions dropdown
    $("#moin-download-trigger").click(function () {
        if (!($("td.selected-item").length)) {
            $(".moin-flash").remove();
            MoinMoin.prototype.moinFlashMessage(MoinMoin.prototype.MOINFLASHWARNING, _("Download failed, no items were selected."));
        } else {
            // download selected files (add small delay to start of multiple downloads for IE9)
            $(".selected-item").children(".moin-download-link").each(function (index, element) {
                // at 0 ms IE9 skipped 41 of 42 downloads, at 100 ms IE9 skipped 14 of 42, success at 200 ms
                var wait = index * IFRAME_CREATE_DELAY;
                setTimeout(function () { startFileDownload(element); }, wait);
            });
        }
    });

    // add click handler to "Delete" and "Destroy" buttons of Actions dropdown
    $(".moin-action-tab").click(function () {
        var action = this.text;
        // Show error msg if nothing selected, else show comment popup. Hide actions dropdown.
        if (!($("td.selected-item").length)) {
            $(".moin-flash").remove();
            MoinMoin.prototype.moinFlashMessage(MoinMoin.prototype.MOINFLASHWARNING, action + ' failed, no items were selected.');
        } else {
            if (this.id === "moin-delete-trigger") {
                showpop("delete");
            } else {
                showpop("destroy");
            }
        }
    });

    // add click handler to "Submit" button on "Please provide comment..." popup
    $(".popup-submit").click(function () {
        // process delete or destroy action
        var comment = $(".popup-comment").val(),
            action = $(".popup-action").val();
        comment = $.trim(comment);
        do_action(comment, action);
        hidepop();
    });

    // add click handler to "Toggle" button on "Filter by content type" dropdown
    $(".moin-filter-toggle").click(function () {
        // reverse checked/unchecked for each content type
        $(".moin-contenttype-selection form").find("input[type='checkbox']").each(function () {
            $(this).prop('checked', !$(this).is(':checked'));
        });
        return false;
    });

    // Filter, Namespace, New Item buttons have similar actions, show last clicked action, hide others
    // add click handler to toggle button for content type "Filter" dropdown
    $(".moin-ct-toggle").click(function () {
        // show/hide content type selection
        $(".moin-contenttype-selection").toggle();
        $(".moin-namespace-selection").css("display", "none");
        $(".moin-newitem-selection").css("display", "none");
    });

    // add click handler to toggle button on "Namespace" dropdown
    $(".moin-ns-toggle").click(function () {
        // show/hide namespace selection
        $(".moin-namespace-selection").toggle();
        $(".moin-contenttype-selection").css("display", "none");
        $(".moin-newitem-selection").css("display", "none");
    });

    // add click handler to toggle button on "New Item" dropdown
    $(".moin-newitem-toggle").click(function () {
        // show/hide new item selection
        $(".moin-newitem-selection").toggle();
        $(".moin-contenttype-selection").css("display", "none");
        $(".moin-namespace-selection").css("display", "none");
    });

    // add click handlers to all items shown on global index page
    $(".moin-select-item").click(function () {
        // toggle selection classes
        $(this > "input[type='checkbox']").prop('checked', !$(this > "input[type='checkbox']").is(':checked'));
        if ($(this).parent().hasClass("selected-item")) {
            $(this).parent().removeClass("selected-item");
            if ($(".moin-select-allitem").hasClass("allitem-selected")) {
                $(".moin-select-allitem").removeClass("allitem-selected").addClass("allitem-toselect");
            }
        } else {
            $(this).parent().addClass("selected-item");
            $(this).next().removeClass("moin-auth-failed");
        }
    });

    // add item count to upper left of table
    $(".moin-num-rows").text($('.moin-index tbody tr').length);

    });
