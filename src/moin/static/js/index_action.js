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
        IFRAME_REMOVE_DELAY = 3000, // life expectancy of iframe used for file downloads
        // delete and destroy process started and completed messages
        ACTION_LOADING = {'delete': _("Deleting.."),
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
            var itemname = $(this).attr("value").slice(1);
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
    function showpop(action) {
        // hide Actions popup and show Comment popup
        $(".popup-container").css("display", "none");
        $("#popup-for-action").css("display", "block");
        $(".popup-comment").val("");
        $(".popup-action").val(action);
        if (action === "delete") {
            $(".popup-header > span").html(POPUP_DELETE_HEADER);
        } else{
            $(".popup-header > span").html(POPUP_DESTROY_HEADER);
        }
        get_subitem_names(action);
        $("#popup").fadeIn();
        $(".popup-comment").focus();
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

    // executed via the "provide comment" popup triggered by an Actions Delete or Destroy selection
    function do_action(comment, action) {
        var links = [],
            itemnames,
            actionTrigger,
            url;
        // create an array of selected item names
        $("input.moin-item:checked").each(function () {
            var itemname = $(this).attr("value").slice(1);
            links.push(itemname);
        });
        // remove any flash messages, display "deleting..." or "destroying..." flash msg while process is in progress
        $("#popup").css("display", "none");
        // note the parent of .moin-flash messages is #moin-flash; moin-flash is used as both id and class
        $(".moin-flash").remove();
        MoinMoin.prototype.moinFlashMessage(MoinMoin.prototype.MOINFLASHINFO, ACTION_LOADING[action]);
        // create a transaction to delete or destroy selected items
        itemnames = JSON.stringify(links);
        actionTrigger = "moin-" + action + "-trigger";
        url = $("#" + actionTrigger).attr("data-actionurl");
        // outgoing itemnames is an array of checked item names; comment is from text field of popup,
        // do_subitems is state of checkbox - true if subitems are to be processed
        $.post(url, {
            itemnames: itemnames,
            comment: comment,
            do_subitems: $("#moin-do-subitems").is(":checked") ? "true" : "false"
        }, function (data) {
            // incoming itemnames is url-encoded list of item names (including alias names) successfully deleted/destroyed
            var itemnames = data.itemnames,
                idx;
            // display success/fail flash messages created by server for each selected item and subitem
            for (idx = 0; idx < data.messages.length; idx += 1) {
                MoinMoin.prototype.moinFlashMessage(MoinMoin.prototype.MOINFLASHINFO, data.messages[idx]);
            }
            // remove index rows for all deleted/destroyed items; including alias names (items with alias names have multiple rows)
            $.each(itemnames, function (itemindex, itemname) {
                var isLastElement = itemindex == itemnames.length -1;
                $('input[value="' + itemname + '"]').parent().parent().parent().remove();
                if (isLastElement) {
                    MoinMoin.prototype.moinFlashMessage(MoinMoin.prototype.MOINFLASHINFO, _("Action complete."));
                    // update item count in upper left of table
                    $(".moin-num-rows").text($('.moin-index tbody tr').length);
                    // remove Deleting... flash message
                    $('#moin-flash').find('p').first().remove();
                }
            });
        }, "json");
    }

    // add click handler to "Select All" tab to select/deselect all items
    $(".moin-select-toggle").change(function () {
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
    $(".popup-cancel").click(function () {
        hidepop();
    });

    // add click handler to "Download" button of Actions dropdown
    $("#moin-download-trigger").click(function () {
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
    $(".moin-action-tab").click(function () {
        var action = this.innerText;
        // Show error msg if nothing selected, else show comment popup. Hide actions dropdown.
        if (!($(".moin-item:checked").length)) {
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
        }
    });

    // add item count to upper left of table
    $(".moin-num-rows").text($('.moin-index tbody tr').length);

    });
