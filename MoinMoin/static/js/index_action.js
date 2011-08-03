$("document").ready(function (){

    $(".moin-select-item").live("click", function (){
    if($(this).parent().hasClass("selected-item"))
        $(this).parent().removeClass("selected-item");
    else
        $(this).parent().addClass("selected-item");
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
            $(this).removeClass("allitem-toselect").addClass("allitem-selected");
        }
        else {
            $(this).removeClass("allitem-selected").addClass("allitem-toselect");
            $(".moin-item-index div").removeClass();
        }
    });
});
