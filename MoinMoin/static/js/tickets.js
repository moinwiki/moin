$(document).ready(function(){

    $("table").tablesorter({
    widgets: ["resizable"],
    widgetOptions : {
        // css class name applied to the sticky header
        resizable : false
    },
    headers: {
        // remove sorting option for tags column
        7: { sorter: false }
    }
  });

});
