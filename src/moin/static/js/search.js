/*
    * Copyright 2013 MoinMoin:sharky93
    * Copyright 2014 MoinMoin:AjiteshGupta
    * Copyright 2022 MoinMoin:RogerHaase
    * License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

    search.js is loaded by search.html which includes ajaxsearch.html.

    These functions monitor changes to the Search Options form and create an ajax transaction
    once the user pauses typing or clicking. When the transaction completes the ajaxsearch.html
    content is updated with the transaction results.

    Searching is expensive on the server, so we:
    - wait until the input has been quiet for SEARCH_DELAY_MS before sending a request,
    - do not send a request if the search parameters did not change (e.g. arrow keys, shift),
    - abort a still running request when a newer one is sent and ignore stale responses,
      so results are never shown out of order.
*/

$(document).ready(function(){

    var SEARCH_DELAY_MS = 300;
    var searchTimer = null;  // pending delayed search
    var currentRequest = null;  // the most recent ajax request, while it is running
    var lastParams = null;  // serialized parameters of the most recent request

    // user friendly browsers may retain form state after a reload, we want form defaults
    // select the first radio buttons; Latest in Revisions and Highest Score in Sort By
    $("input[type=radio]:first").attr("checked", true);
    // kill form action on pressing Enter, all transactions are ajax; search right away
    $('#moin-long-searchform').submit(function(e){
        e.preventDefault();
        runSearch();
        return false;
    });

    // hide/show Search Options form
    $(document).on("click", ".moin-search-option-bar", (function(){
        $('.moin-searchoptions').toggleClass('hidden');
        $('.moin-search-option-bar > p').toggleClass('fa-chevron-down fa-chevron-up');
    }));

    // TODO: Basic theme should do this some other way
    $('.moin-loginsettings').addClass('navbar-right');

    // collect the search text and Search Options form data
    function searchParams() {
        var filetypes = "";
        var namespaces = "";
        $('[name="itemtype"]:checked').each(function() {
            filetypes += $(this).val() + ',';
        });
        $('[name="namespace"]:checked').each(function() {
            namespaces += $(this).val() + ',';
        });
        return {
            q: $('.moin-search-query').val(),
            history: $('[name="history"]:checked').val() === "all",
            time_sorting: $('[name="modified_time"]:checked').val(),
            filetypes: filetypes,
            namespaces: namespaces,
            trash: $('[name="trash"]:checked').val() === "include",
            boolajax: true
        };
    }

    // execute ajax transaction and replace old ajaxsearch.html content with updated ajaxsearch.html results
    function runSearch() {
        if (searchTimer !== null) {
            clearTimeout(searchTimer);
            searchTimer = null;
        }
        var params = searchParams();
        var serialized = $.param(params);
        if (serialized === lastParams) {
            return;  // nothing changed, the shown results are still valid
        }
        lastParams = serialized;
        if (currentRequest !== null) {
            // forget it before aborting: abort() runs its fail/always handlers right away,
            // and these must not reset the state that belongs to the new request
            var staleRequest = currentRequest;
            currentRequest = null;
            staleRequest.abort();
        }
        var wiki_root = $('#moin-wiki-root').val();
        var request = $.ajax({
            type: "GET",
            url: wiki_root + "/+search",
            data: params
        });
        currentRequest = request;
        request.done(function(data) {
            if (request !== currentRequest) {
                return;  // a newer request was sent meanwhile, ignore this stale response
            }
            if (data.search(/doctype/i) > 0) {
                // this is a full page with a flash error message, replace everything
                $("body").html(data);
                // empty search text field
                $("input[type=search]").val("");
                $('#moin-flash').remove();
                lastParams = null;
            } else {
                // normal response replaces old ajaxsearch.html
                $('#finalresults').html(data);
                // ajax search does not support search by item name; hide "item search' heading if present
                $('#moin-content h2').hide();
            }
        }).fail(function() {
            if (request === currentRequest) {
                lastParams = null;  // allow retrying the same search
            }
        }).always(function() {
            if (request === currentRequest) {
                currentRequest = null;
            }
        });
    }

    // run the search once the input has been quiet for SEARCH_DELAY_MS
    function scheduleSearch() {
        if (searchTimer !== null) {
            clearTimeout(searchTimer);
        }
        searchTimer = setTimeout(runSearch, SEARCH_DELAY_MS);
    }

    // detect radio button or checkbox form change
    $(document).on("change", ".moin-searchoptions input", scheduleSearch);

    // detect change in search text field (typing, pasting, cutting, clearing)
    $('.moin-search-query').on("input", scheduleSearch);
});
