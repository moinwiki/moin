/*
    * Copyright 2013 MoinMoin:sharky93
    * Copyright 2014 MoinMoin:AjiteshGupta
    * Copyright 2022 MoinMoin:RogerHaase
    * License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

    search.js is loaded by search.html which includes ajaxsearch.html.

    These functions monitor changes to the Search Options form and create an ajax transaction after each
    key stroke or mouse click. When the transaction completes the ajaxsearch.html content is updated
    with the transaction results.
*/

$(document).ready(function(){

    // user friendly browsers may retain form state after a reload, we want form defaults
    // select the first radio buttons; Latest in Revisions and Highest Score in Sort By
    $("input[type=radio]:first").attr("checked", true);
    // select the last checkbox All in Content Types
    $("input[type=checkbox]:checked").removeAttr("checked");
    $("input[type=checkbox]:last").prop("checked", true)

    // kill form action on pressing Enter, all transactions are ajax
    $('#moin-long-searchform').submit(function(e){
        e.preventDefault();
        return false;
    });

    // hide/show Search Options form
    $(document).on("click", ".moin-search-option-bar", (function(){
        $('.moin-searchoptions').toggleClass('hidden');
        $('.moin-search-option-bar > p').toggleClass('fa-chevron-down fa-chevron-up');
    }));

    // TODO: Basic theme should do this some other way
    $('.moin-loginsettings').addClass('navbar-right');

    // execute ajax transaction and replace old ajaxsearch.html content with updated ajaxsearch.html results
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

    // detect radio button or checkbax form change and call moin-search query function below
    $(document).on("click", "input", (function(){
        $('.moin-search-query').keyup();
    }));

    // detects change in search text field, or is called by function above. Collects form data and passes it to `ajaxify` function above
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
