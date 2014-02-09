$(document).ready(function(){
	// kill form action on pressing Enter
	$('#moin-long-searchform').submit(function(e){
		e.preventDefault();
		return false;
	});

	// hide form submit button
	$('#moin-long-searchform .button').hide();

	function ajaxify(query, allrevs) {
		$.ajax({
  			type: "GET",
  			url: "/+search",
  			data: { q: query, history: allrevs, boolajax: true }
		}).done(function( html ) {
			$('#finalresults').html(html)
		});
	}
	$('#moin-search-query').keyup(function() {
		var allrev = false
		if($('[name="history"]').prop('checked')){
 			allrev = true;
		}		
  		ajaxify($(this).val(), allrev);
	});
});