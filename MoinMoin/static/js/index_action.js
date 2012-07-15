/*
 * Click and submit handlers for form elements on the global index page.
 * Copyright 2011, AkashSinha<akash2607@gmail.com>
 * License: GNU GPL v2 (or any later version), see LICENSE.txt for details.
 */

/*jslint browser: true, */
/*global $:false */

// This anonymous function is executed once after a global index page loads.
$("document").ready(function () {
    "use strict";

    var POPUP_FADE_TIME = 200, // fade in, fade out times for selected popups
        IFRAME_CREATE_DELAY = 200, // delay between start of multiple downloads
        IFRAME_REMOVE_DELAY = 3000, // life expectancy of iframe used for file downloads
        MESSAGE_VIEW_TIME = 4000, // life expectancy of delete/destroy status messages
        ACTION_LOADING = {"delete": "Deleting..", "destroy": "Destroying.."}, // process started messages
        ACTION_DONE = {"delete": "deleted", "destroy": "destroyed"}; // process completed messages

    // called by click handlers New Item, Delete item, and Destroy item within Actions dropdown menu
    function showpop(action) {
        // hide Actions popup and show either New Item or Comment popup
        $(".popup-container").css("display", "none");
        if (action === "newitem") {
            $("#popup-for-newitem").css("display", "block");
            $("#file_upload").appendTo("#popup-for-newitem .popup-body");
            $(".upload-form").css("display", "block");
        } else {
            $("#popup-for-action").css("display", "block");
            $(".popup-comment").removeClass("blank");
            $(".popup-comment").val("");
            $(".popup-action").val(action);
        }
        $("#popup").fadeIn();
        $("#lightbox").css("display", "block");
    }

    // called by click handlers within "Create new item" and "Please provide comment" popups
    function hidepop() {
        // hide popup
        $("#popup").css("display", "none");
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

    // called by do_action when an item is successfully deleted or destroyed
    function hide(item_link) {
        // remove a deleted or destroyed item from current display
        item_link.parent().remove();
    }

    // called by do_action when item cannot be deleted or destroyed
    function show_conflict(item_link) {
        // mark an item as having failed a delete or destroy operation
        item_link.removeClass().addClass("moin-conflict");
        item_link.parent().removeClass();
    }

    // executed via the "provide comment" popup triggered by an Actions Delete or Destroy selection
    function do_action(comment, action) {
        // create an array of selected item names
        var links = [],
            itemnames,
            actionTrigger,
            url;
        $(".selected-item").children("a.moin-item").each(function () {
            var itemname = $(this).attr("title");
            links.push(itemname);
        });
        // hide comment popup, display "deleting..." or "destroying..."
        $("#popup").css("display", "none");
        $(".moin-index-message span").text(ACTION_LOADING[action]);
        $(".moin-index-message").css("display", "block");
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
                    hide($('.selected-item').children('a.moin-item[title="' + itemname + '"]'));
                    success_item += 1;
                } else {
                    show_conflict($('.selected-item').children('a.moin-item[title="' + itemname + '"]'));
                    left_item += 1;
                }
            });
            // show a message summarizing delete/destroy results for 4 seconds
            message = "Items " + ACTION_DONE[action] + ": " + success_item;
            if (left_item) {
                message += ", Items not " + ACTION_DONE[action] + ": " + left_item + ".";
            }
            $(".moin-index-message span").text(message);
            setTimeout(function () {
                $(".moin-index-message").fadeOut();
            }, MESSAGE_VIEW_TIME);
        }, "json");
    }

    // -- Select All handlers start here

    // add click handler to "Select All" tab to select/deselect all items
    $(".moin-select-allitem").click(function () {
        // toggle classes
        if ($(this).hasClass("allitem-toselect")) {
            $(".moin-item-index div").removeClass().addClass("selected-item");
            $(this).removeClass("allitem-toselect").addClass("allitem-selected");
        } else {
            $(this).removeClass("allitem-selected").addClass("allitem-toselect");
            $(".moin-item-index div").removeClass();
        }
    });

    // -- Actions handlers start here

    // add click handler to "Actions" drop down list
    // also executed via .click call when user clicks on an action (new, download, delete, destroy)
    $(".show-action").click(function () {
        // show/hide actions drop down list
        var actionsDiv = $(this).parent().parent();
        if (actionsDiv.find("ul:first").is(":visible")) {
            actionsDiv.find("ul:first").fadeOut(POPUP_FADE_TIME);
            actionsDiv.removeClass("action-visible");
        } else {
            actionsDiv.find("ul:first").fadeIn(POPUP_FADE_TIME);
            actionsDiv.addClass("action-visible");
        }
    });

    // add click handler to "New Item" action tab entry
    $("#moin-create-newitem").click(function () {
        // show new item popup and hide actions dropdown
        showpop("newitem");
        $(".show-action").trigger("click");
    });

    // add click handler to close button "X" on new item popup
    $(".popup-cancel").click(function () {
        // if files are selected for upload, add to drag and drop area; hide popup
        if ($("#popup-for-newitem:visible").length) {
            $("#file_upload").appendTo("#moin-upload-cont");
            $(".upload-form").css("display", "none");
        }
        hidepop();
    });

    // add submit handler to "Create" button on new item popup
    // This is a workaround for browsers that do not support "required" attribute (ie9, safari 5.1)
    // note: The creation of a new item is performed via action=... attribute on form
    $("#popup-for-newitem").find("form:first").submit(function () {
        // if no item name was provided show hint and stop form action
        var itembox = $(this).children("input[name='newitem']"),
            itemname = itembox.val();
        if ($.trim(itemname) === "") {
            itembox.addClass("blank");
            itembox.focus();
            return false;
        }
    });

    // add click handler to "Download" button of Actions dropdown
    $("#moin-download-trigger").click(function () {
        if (!($("div.selected-item").length)) {
            // no items selected, show message for 4 seconds
            $(".moin-index-message span").text("Nothing was selected.");
            $(".moin-index-message").fadeIn();
            setTimeout(function () {
                $(".moin-index-message").fadeOut();
            }, MESSAGE_VIEW_TIME);
        } else {
            // download selected files (add small delay to start of multiple downloads for IE9)
            $(".selected-item").children(".moin-download-link").each(function (index, element) {
                // at 0 ms IE9 skipped 41 of 42 downloads, at 100 ms IE9 skipped 14 of 42, success at 200 ms
                var wait = index * IFRAME_CREATE_DELAY;
                setTimeout(function () { startFileDownload(element); }, wait);
            });
        }
        // hide the list of actions
        $(".show-action").trigger("click");
    });

    // add click handler to "Delete" and "Destroy" buttons of Actions dropdown
    $(".moin-action-tab").click(function () {
        // Show error msg if nothing selected, else show comment popup. Hide actions dropdown.
        if (!($("div.selected-item").length)) {
            $(".moin-index-message span").text("Nothing was selected.");
            $(".moin-index-message").fadeIn();
            setTimeout(function () {
                $(".moin-index-message").fadeOut();
            }, MESSAGE_VIEW_TIME);
        } else {
            if (this.id === "moin-delete-trigger") {
                showpop("delete");
            } else {
                showpop("destroy");
            }
        }
        $(".show-action").trigger("click");
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

    // -- Filter by content type handlers start here

    // add click handler to "Filter by content type" button
    $(".moin-contenttypes-wrapper").children("div").click(function () {
        // show/hide content type dropdown
        var wrapper = $(this).parent();
        if (wrapper.find("form:visible").length) {
            $(".moin-contenttypes-wrapper").find("form").fadeOut(POPUP_FADE_TIME);
            $(this).removeClass().addClass("ct-hide");
        } else {
            $(".moin-contenttypes-wrapper").find("form").fadeIn(POPUP_FADE_TIME);
            $(this).removeClass().addClass("ct-shown");
        }
    });

    // add click handler to "Toggle" button on "Filter by content type" dropdown
    $(".filter-toggle").click(function () {
        // reverse checked/unchecked for each content type
        $(".moin-contenttypes-wrapper form").find("input[type='checkbox']").each(function () {
            if ($(this).attr("checked")) {
                $(this).removeAttr("checked");
            } else {
                $(this).attr("checked", "checked");
            }
        });
        return false;
    });

    // add click handler to "More" button on "Filter by content type" dropdown
    $(".filter-more").click(function () {
        // show/hide help text describing each content type
        var helper_texts = $(".moin-contenttypes-wrapper form").find(".helper-text:visible");
        if (helper_texts.length) {
            helper_texts.fadeOut();
        } else {
            $(".moin-contenttypes-wrapper form").find(".helper-text").css("display", "block");
        }

        return false;
    });

    // -- individual item handlers start here

    // add click handlers to all items shown on global index page
    $(".moin-select-item").click(function () {
        // toggle selection classes
        if ($(this).parent().hasClass("selected-item")) {
            $(this).parent().removeClass("selected-item");
            if ($(".moin-select-allitem").hasClass("allitem-selected")) {
                $(".moin-select-allitem").removeClass("allitem-selected").addClass("allitem-toselect");
            }
        } else {
            $(this).parent().addClass("selected-item");
        }
    });
});

