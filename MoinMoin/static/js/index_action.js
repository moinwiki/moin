function enablelink(downloadlink) {
    url=downloadlink.attr("title");
    downloadlink.attr("href",url);
    downloadlink.addClass("active-link");
}

function disablelink(downloadlink) {
    downloadlink.attr("href","about:blank");
    downloadlink.removeClass("active-link");
}

$("document").ready(function (){

    $(".moin-select-item").live("click", function (){
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
            $(".moin-item-index div").each(function (){
                downloadlink=$(this).children(".moin-download-link");
                enablelink(downloadlink);
            });
            $(this).removeClass("allitem-toselect").addClass("allitem-selected");

        }
        else {
            $(this).removeClass("allitem-selected").addClass("allitem-toselect");
            $(".moin-item-index div").removeClass();
            $(".moin-item-index div").each(function (){
                downloadlink=$(this).children(".moin-download-link");
                disablelink(downloadlink);
            });
        }
    });

    $(".moin-download-trigger").click(function () {
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
    $('.moin-download-trigger').multiDownload('click', { delay: 3000 });

});
