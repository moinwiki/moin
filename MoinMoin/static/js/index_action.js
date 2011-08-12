/*
 * Script for the actions performed on the items at index page.
 * Copyright 2011, AkashSinha<akash2607@gmail.com> 
 */

function enablelink(downloadlink) {
    url=downloadlink.attr("title");
    downloadlink.attr("href",url);
    downloadlink.addClass("active-link");
}

function disablelink(downloadlink) {
    downloadlink.attr("href","about:blank");
    downloadlink.removeClass("active-link");
}

function showpop()
{
    $("#popup").fadeIn();
    $(".popup-comment").removeClass("blank");
    $(".popup-comment").val("");
}

function hide(item_link)
{
   item_link.parent().remove();
}

function show_conflict(item_link)
{
   item_link.removeClass().addClass("moin-conflict");
}

function delete_item(comment) {
    var links = [];
    $(".selected-item").children("a.moin-item").each(function () {
        itemname = $(this).attr("title");
        links.push(itemname);
    });
    var itemnames = JSON.stringify(links);
    url = $("#moin-delete-trigger").attr("actionurl");
    $("#popup").css("display", "none");
    $(".moin-index-message span").text("Deleting...");
    $(".moin-index-message").css("display", "block");
    $.post(url, {
            itemnames: itemnames,
            comment: comment,
            }, function (data) {
                var itemnames = data.itemnames;
                var delete_status = data.status;
                var deleted_item = 0;
                var left_item = 0;
                $.each(itemnames, function (itemindex, itemname) {
                    if(delete_status[itemindex]) {
                        hide($('.selected-item').children('a.moin-item[title="' + itemname + '"]'));
                        deleted_item++;
                    }
                    else {
                        show_conflict($('.selected-item').children('a.moin-item[title="' + itemname + '"]'));
                        left_item++;
                   }  
                   });
                   var message = "Items deleted: " + deleted_item ;
                   if(left_item)
                       message += ", Items not deleted: " + left_item + ".";
                   $(".moin-index-message span").text(message);
                   setTimeout(function () {
                       $(".moin-index-message").fadeOut();
                   }, 4000);
            }, "json");
}

$("document").ready(function () {

    $(".moin-select-item").click(function () {
    if($(this).parent().hasClass("selected-item")) {
        $(this).parent().removeClass("selected-item");
        downloadlink=$(this).parent().children(".moin-download-link");
        disablelink(downloadlink);
        if($(".moin-select-allitem").hasClass("allitem-selected")) {
            $(".moin-select-allitem").removeClass("allitem-selected").addClass("allitem-toselect");
        }
    }
    else {
        $(this).parent().addClass("selected-item");
        downloadlink=$(this).parent().children(".moin-download-link");
        enablelink(downloadlink);
    }
    });

    $(".show-action").click(function () {
        actionsDiv = $(this).parent().parent();
         if(actionsDiv.find("ul:first").is(":visible")) {
             actionsDiv.find("ul:first").fadeOut(200);
             actionsDiv.removeClass("action-visible");
         }
         else {
             actionsDiv.find("ul:first").fadeIn(200);
             actionsDiv.addClass("action-visible");
         }
    });
    
    $(".moin-select-allitem").click(function () {
        if($(this).hasClass("allitem-toselect")) {
            $(".moin-item-index div").removeClass().addClass("selected-item");
            $(".moin-item-index div").each(function () {
                downloadlink=$(this).children(".moin-download-link");
                enablelink(downloadlink);
            });
            $(this).removeClass("allitem-toselect").addClass("allitem-selected");

        }
        else {
            $(this).removeClass("allitem-selected").addClass("allitem-toselect");
            $(".moin-item-index div").removeClass();
            $(".moin-item-index div").each(function () {
                downloadlink=$(this).children(".moin-download-link");
                disablelink(downloadlink);
            });
        }
    });

    $("#moin-delete-trigger").click(function () {
        if(!($("div.selected-item").length)) {
            $(".moin-index-message span").text("Nothing was selected.");
            $(".moin-index-message").fadeIn();
            setTimeout(function () {
                $(".moin-index-message").fadeOut();
            }, 4000);
        }
        else {
            showpop();
        }
        $(".show-action").trigger("click");
    });
    
    $(".popup-cancel").click(function () {
        $("#popup").fadeOut();
    });

    $(".popup-submit").click(function () {
        var comment = $(".popup-comment").val();
        if($.trim(comment) == "") {
            $(".popup-comment").addClass("blank");
            $(".popup-comment").focus();
        }
        else { 
            delete_item(comment);
        }
    });

    $("#moin-download-trigger").click(function () {
        if(!($("a.active-link").length)) {
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
