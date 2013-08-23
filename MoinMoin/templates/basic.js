$(document).ready(function (){
    // this depends on the id's used for different tab-panes in modify.html (Basic Theme)
    var edit = false;
    $('#meta, #help').removeClass('active');
    $('textarea').autosize();
    $('textarea').change(function() {
    	edit = true;
    })
    window.onbeforeunload = function(e) {
    	if (edit) {
    		edit = false;
    		return "You have unsaved changes!";
    	}
    }
    $('div.dropup').removeClass('menu');
    $('ul.dropdown-menu').removeClass('submenu');
});
