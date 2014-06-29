$(document).ready(function(){

    // adds filter option in /+tickets view
    // User can click on on any td element in the table to filter according to the value in that
    function filter(selected_column) {
        return function () {
            var table = document.getElementById('ticket-list');
            var cols = table.rows[0].cells.length;
            var columns = table.getElementsByTagName("td");
            var rows = table.getElementsByTagName("tr");
            var selected_row = parseInt(selected_column/cols) + 1;
            selected_column = selected_column%cols;
            var data_to_filter = table.rows[selected_row].cells[selected_column].innerHTML;
            var len = columns.length;

            for ( var i = len-1; i >= 0; i-- ) {
                if( i%cols == selected_column ) {
                    var row = parseInt(i/cols) + 1;
                    var data = table.rows[row].cells[selected_column].innerHTML;
                    if( data != data_to_filter ) {
                        rows[row].remove();
                        i = i - selected_column;
                    }
                }
            }
        };
    }

    var table = document.getElementById('ticket-list');
    var cols = table.rows[0].cells.length;
    var columns = table.getElementsByTagName("td");
    for (var  i = 0; i < columns.length; i++ ) {
    // listener not required for Summary and Itemid columns
        if ( i%cols != 0 && i%cols != 1 ) {
            columns[i].onclick = filter(i);
        }
    }

    $("#ticket-list").tablesorter();

});
