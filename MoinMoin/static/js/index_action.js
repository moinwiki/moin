/*
 * Script for the actions performed on the items at index page.
 * Copyright 2011, AkashSinha<akash2607@gmail.com>
 */
/*jslint browser: true, */
/*global $:false */

var actionLoading = [];
actionLoading["delete"] = "Deleting..";
actionLoading.destroy = "Destroying..";

var actionDone = [];
actionDone["delete"] = "deleted";
actionDone.destroy = "destroyed";

function enablelink(downloadlink) {
    "use strict";
    var url = downloadlink.attr("title");
    downloadlink.attr("href", url);
    downloadlink.addClass("active-link");
}

function disablelink(downloadlink) {
    "use strict";
    downloadlink.attr("href", "about:blank");
    downloadlink.removeClass("active-link");
}

function showpop(action) {
    "use strict";
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

function hidepop() {
    "use strict";
    $("#popup").css("display", "none");
    $("#lightbox").css("display", "none");
}

function hide(item_link) {
    "use strict";
    item_link.parent().remove();
}

function show_conflict(item_link) {
    "use strict";
    item_link.removeClass().addClass("moin-conflict");
    item_link.parent().removeClass();
}

function do_action(comment, action) {
    "use strict";
    var links = [], itemnames, actionTrigger, url;
    $(".selected-item").children("a.moin-item").each(function () {
        var itemname = $(this).attr("title");
        links.push(itemname);
    });
    itemnames = JSON.stringify(links);
    actionTrigger = "moin-" + action + "-trigger";
    url = $("#" + actionTrigger).attr("data-actionurl");
    $("#popup").css("display", "none");
    $(".moin-index-message span").text(actionLoading[action]);
    $(".moin-index-message").css("display", "block");
    $.post(url, {
        itemnames: itemnames,
        comment: comment
    }, function (data) {
        var itemnames = data.itemnames,
            action_status = data.status,
            success_item = 0,
            left_item = 0,
            message;
        $.each(itemnames, function (itemindex, itemname) {
            if (action_status[itemindex]) {
                hide($('.selected-item').children('a.moin-item[title="' + itemname + '"]'));
                success_item += 1;
            } else {
                show_conflict($('.selected-item').children('a.moin-item[title="' + itemname + '"]'));
                left_item += 1;
            }
        });
        message = "Items " + actionDone[action] + ": " + success_item;
        if (left_item) {
            message += ", Items not " + actionDone[action] + ": " + left_item + ".";
        }
        $(".moin-index-message span").text(message);
        setTimeout(function () {
            $(".moin-index-message").fadeOut();
        }, 4000);
    }, "json");
}

$("document").ready(function () {
    "use strict";
    $(".moin-contenttypes-wrapper").children("div").click(function () {
        var wrapper = $(this).parent();
        if (wrapper.find("form:visible").length) {
            $(".moin-contenttypes-wrapper").find("form").fadeOut(200);
            $(this).removeClass().addClass("ct-hide");
        } else {
            $(".moin-contenttypes-wrapper").find("form").fadeIn(200);
            $(this).removeClass().addClass("ct-shown");
        }
    });

    $(".filter-toggle").click(function () {
        $(".moin-contenttypes-wrapper form").find("input[type='checkbox']").each(function () {
            if ($(this).attr("checked")) {
                $(this).removeAttr("checked");
            } else {
                $(this).attr("checked", "checked");
            }
        });
        return false;
    });

    $(".filter-more").click(function () {
        var helper_texts = $(".moin-contenttypes-wrapper form").find(".helper-text:visible");
        if (helper_texts.length) {
            helper_texts.fadeOut();
        } else {
            $(".moin-contenttypes-wrapper form").find(".helper-text").css("display", "block");
        }

        return false;
    });

    $(".moin-select-item").click(function () {
        var downloadlink;
        if ($(this).parent().hasClass("selected-item")) {
            $(this).parent().removeClass("selected-item");
            downloadlink = $(this).parent().children(".moin-download-link");
            disablelink(downloadlink);
            if ($(".moin-select-allitem").hasClass("allitem-selected")) {
                $(".moin-select-allitem").removeClass("allitem-selected").addClass("allitem-toselect");
            }
        } else {
            $(this).parent().addClass("selected-item");
            downloadlink = $(this).parent().children(".moin-download-link");
            enablelink(downloadlink);
        }
    });

    $(".show-action").click(function () {
        var actionsDiv = $(this).parent().parent();
        if (actionsDiv.find("ul:first").is(":visible")) {
            actionsDiv.find("ul:first").fadeOut(200);
            actionsDiv.removeClass("action-visible");
        } else {
            actionsDiv.find("ul:first").fadeIn(200);
            actionsDiv.addClass("action-visible");
        }
    });

    $(".moin-select-allitem").click(function () {
        var downloadlink;
        if ($(this).hasClass("allitem-toselect")) {
            $(".moin-item-index div").removeClass().addClass("selected-item");
            $(".moin-item-index div").each(function () {
                downloadlink = $(this).children(".moin-download-link");
                enablelink(downloadlink);
            });
            $(this).removeClass("allitem-toselect").addClass("allitem-selected");
        } else {
            $(this).removeClass("allitem-selected").addClass("allitem-toselect");
            $(".moin-item-index div").removeClass();
            $(".moin-item-index div").each(function () {
                downloadlink = $(this).children(".moin-download-link");
                disablelink(downloadlink);
            });
        }
    });

    $(".moin-action-tab").click(function () {
        if (!($("div.selected-item").length)) {
            $(".moin-index-message span").text("Nothing was selected.");
            $(".moin-index-message").fadeIn();
            setTimeout(function () {
                $(".moin-index-message").fadeOut();
            }, 4000);
        } else {
            if (this.id === "moin-delete-trigger") {
                showpop("delete");
            } else {
                showpop("destroy");
            }
        }
        $(".show-action").trigger("click");
    });

    $("#moin-create-newitem").click(function () {
        showpop("newitem");
        $(".show-action").trigger("click");

    });

    $(".popup-cancel").click(function () {
        if ($("#popup-for-newitem:visible").length) {
            $("#file_upload").appendTo("#moin-upload-cont");
            $(".upload-form").css("display", "none");
        }
        hidepop();
    });

    $(".popup-submit").click(function () {
        var comment = $(".popup-comment").val(),
            action = $(".popup-action").val();
        comment = $.trim(comment);
        do_action(comment, action);
        hidepop();
    });

    $("#popup-for-newitem").find("form:first").submit(function () {
        var itembox = $(this).children("input[name='newitem']"),
            itemname = itembox.val();
        if ($.trim(itemname) === "") {
            itembox.addClass("blank");
            itembox.focus();
            return false;
        }
    });

    $("#moin-download-trigger").click(function () {
        if (!($("a.active-link").length)) {
            $(".moin-index-message span").text("Nothing was selected.");
            $(".moin-index-message").fadeIn();
            setTimeout(function () {
                $(".moin-index-message").fadeOut();
            }, 4000);
        }
        $(".show-action").trigger("click");
    });

    $('.moin-download-link').multiDownload();
    $('#moin-download-trigger').multiDownload('click', { delay: 3000 });

});

