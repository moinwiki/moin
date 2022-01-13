// MoinMoin search actions, loaded by search.html

$(document).ready(function(){
    // kill form action on pressing Enter
    $('#moin-long-searchform').submit(function(e){
        e.preventDefault();
        return false;
    });

    // hide/show long search form
    $(document).on("click", "#moin-long-searchform .button", (function(){
        $('.moin-search-query').change();
    }));

    // detect form change and start ajax update
    $(document).on("click", "label", (function(){
        $('.moin-search-query').keyup();
    }));

    // hide/show long options search form
    $(document).on("click", ".moin-search-option-bar", (function(){
        $('.moin-searchoptions').toggleClass('hidden');
        $('.moin-search-option-bar > p').toggleClass('fa-chevron-down fa-chevron-up');
    }));

    // TODO: Basic theme should do this some other way
    $('.moin-loginsettings').addClass('navbar-right');

    // replace everything after Search Options form with updated search results
    function ajaxify(query, allrevs, time_sorting, filetypes, is_ticket) {
        var wiki_root = $('#moin-wiki-root').val();
        $.ajax({
            type: "GET",
            url: wiki_root + "/+search",
            data: { q: query, history: allrevs, time_sorting: time_sorting, filetypes: filetypes, boolajax: true, is_ticket: is_ticket }
        }).done(function( html ) {
            $('#finalresults').html(html);
            // ajax search does not support search by item name; hide "item search' heading if present
            $('#moin-content h2').hide();
        });
    }

    // collect form data and pass to ajaxify function
    $('.moin-search-query').keyup(function() {
        var allrev, time_sorting;
        var filetypes= '';
        var is_ticket = '';
        if( $('input[name="meta_summary"]').length ){
            is_ticket = true;
        }
        allrev = $('[name="history"]:checked').val() === "all";
        time_sorting = $('[name="modified_time"]:checked').val();
        $('[name="itemtype"]:checked').each(function() {
            filetypes += $(this).val() + ',';
        });
        ajaxify($(this).val(), allrev, time_sorting, filetypes, is_ticket);
    });
});
