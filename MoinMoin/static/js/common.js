//
// MoinMoin commonly used JavaScript functions
//

var QUICKLINKS_EXPAND = ">>>";
var QUICKLINKS_COLLAPSE = "<<<";

// use this instead of assigning to window.onload directly:
function addLoadEvent(func) {
    // alert("addLoadEvent " + func)
    var oldonload = window.onload;
    if (typeof window.onload != 'function') {
        window.onload = func;
    } else {
        window.onload = function() {
            oldonload();
            func();
        }
    }
}

// copy from fckeditor browser check code (fckeditor.js:298, function : FCKeditor_IsCompatibleBrowser)
function can_use_gui_editor() {
    var sAgent = navigator.userAgent.toLowerCase() ;

    // Internet Explorer 5.5+
    if ( /*@cc_on!@*/false && sAgent.indexOf("mac") == -1 )
    {
        var sBrowserVersion = navigator.appVersion.match(/MSIE (.\..)/)[1] ;
        return ( sBrowserVersion >= 5.5 ) ;
    }

    // Gecko (Opera 9 tries to behave like Gecko at this point).
    if ( navigator.product == "Gecko" && navigator.productSub >= 20030210 && !( typeof(opera) == 'object' && opera.postError ) )
        return true ;

    // Opera 9.50+
    if ( window.opera && window.opera.version && parseFloat( window.opera.version() ) >= 9.5 )
        return true ;

/*
  // disable safari : until fck devteam fix http://dev.fckeditor.net/ticket/2333

    // Adobe AIR
    // Checked before Safari because AIR have the WebKit rich text editor
    // features from Safari 3.0.4, but the version reported is 420.
    if ( sAgent.indexOf( ' adobeair/' ) != -1 )
        return ( sAgent.match( / adobeair\/(\d+)/ )[1] >= 1 ) ; // Build must be at least v1

    // Safari 3+
    if ( sAgent.indexOf( ' applewebkit/' ) != -1 )
        return ( sAgent.match( / applewebkit\/(\d+)/ )[1] >= 522 ) ;    // Build must be at least 522 (v3)
*/
    return false ;

}


function update_edit_links() {
    // Update editlink according if if the browser is compatible
    if (can_use_gui_editor() == false){
        //alert("update_edit_links: can't use gui editor");
        return;
    }
    var editlinks = document.getElementsByName("editlink");
    for (i = 0; i < editlinks.length; i++) {
        var link = editlinks[i];
        href = link.href.replace('editor=textonly','editor=guipossible');
        link.href = href;
        //alert("update_edit_links: modified to guipossible");
    }
}


function add_gui_editor_links() {
    // Add gui editor link after the text editor link

    // If the variable is not set or browser is not compatible, exit
    try {gui_editor_link_href}
    catch (e) {
        //alert("add_gui_editor_links: gui_editor_link_href not here");
        return
    }
    if (can_use_gui_editor() == false){
        //alert("add_gui_editor_links: can't use gui_editor");
        return;
    }
    var all = document.getElementsByName('texteditlink');
    for (i = 0; i < all.length; i++) {
        var textEditorLink = all[i];
        // Create a list item with a link
        var guiEditorLink = document.createElement('a');
        guiEditorLink.href = gui_editor_link_href;
        var text = document.createTextNode(gui_editor_link_text);
        guiEditorLink.appendChild(text);
        var listItem = document.createElement('li')
        listItem.appendChild(guiEditorLink);
        // Insert in the itemviews
        var itemviews = textEditorLink.parentNode.parentNode
        var nextListItem = textEditorLink.parentNode.nextSibling;
        itemviews.insertBefore(listItem, nextListItem);
        //alert("add_gui_editor_links: added gui editor link");
    }
}


function show_switch2gui() {
    // Show switch to gui editor link if the browser is compatible
    if (can_use_gui_editor() == false) return;

    var switch2gui = document.getElementById('switch2gui')
    if (switch2gui) {
        switch2gui.style.display = 'inline';
    }
}

// for long documents with many comments this is expensive to calculate,
// thus we keep it here:
comments = null;

function toggleComments() {
    // Toggle visibility of every tag with class "comment"
    for (i = 0; i < comments.length; i++){
        el = comments[i];
        if ( el.style.display != 'none' ) {
            el.style.display = 'none';
        } else {
            el.style.display = '';
        }
    }
}

function show_toggleComments() {
    // Show edit bar item for toggling inline comments on/off only if inline comments exist on the page
    comments = getElementsByClassName('comment', null, document);
    if (comments.length > 0) {
        var buttons = getElementsByClassName('toggleCommentsButton', null, document);
        for (i = 0; i < buttons.length; i++){
            el = buttons[i];
            el.style.display = '';
        }
    }
}


function load() {
    // Do not name this "onload", it does not work with IE :-)
    // TODO: create separate onload for each type of view and set the
    // correct function name in the html.
    // e.g <body onlod='editor_onload()'>

    // Page view stuff
    update_edit_links();
    add_gui_editor_links();

    // Editor stuff
    show_switch2gui();

    // Enable menu item "ToggleComments" if inline comments exist
    show_toggleComments();

    // data browser widget
    dbw_hide_buttons();
}


function before_unload(evt) {
    // TODO: Better to set this in the editor html, as it does not make
    // sense elsehwere.
    // confirmleaving is available when editing
    try {return confirmleaving();}
    catch (e) {}
}

// Initialize after loading the page
addLoadEvent(load)

// Catch before unloading the page
window.onbeforeunload = before_unload

function dbw_update_search(dbw_id)
{
    var table = document.getElementById(dbw_id+'table');
    var cell;
    var shown;
    var i
    var cols = table.rows[0].cells.length;
    var filter = new Array();
    var dofilter = new Array();
    var form = document.forms[dbw_id+'form'];

    for (i = 0; i < cols; i++) {
        dofilter[i] = false;
        if (form[dbw_id+'filter'+i]) {
            dofilter[i] = true;
            filter[i] = form[dbw_id+'filter'+i].value;
            if (filter[i] == '[all]')
                dofilter[i] = false;
            if (filter[i] == '[empty]')
                filter[i] = '';
        }
    }

    for (i = 1; i < table.rows.length; i++) {
        var show = true;
        for (col = 0; col < cols; col++) {
            if (!dofilter[col])
                continue;

            cell = table.rows[i].cells[col];

            if (filter[col] == '[notempty]') {
                if (cell.abbr == '') {
                    show = false;
                    break;
                }
            } else if (filter[col] != cell.abbr) {
                show = false;
                break;
            }
        }
        if (show)
            table.rows[i].style.display = '';
        else
            table.rows[i].style.display = 'none';
    }
}

function dbw_hide_buttons() {
    var form;
    var elem;
    var name;

    for (var fidx = 0; fidx < document.forms.length; fidx++) {
        form = document.forms[fidx];
        for (var eidx = 0; eidx < form.elements.length; eidx++) {
            elem = form.elements[eidx];
            name = elem.name;
            if (name) {
                if (name.indexOf('dbw.') >= 0 && name.substr(-7) == '.submit')
                    elem.style.display = 'none';
            }
        }
    }
}

/*  getElementsByClassName
    Developed by Robert Nyman, http://www.robertnyman.com
    Code/licensing: http://code.google.com/p/getelementsbyclassname/ (MIT license)
    Version: 1.0.1
*/
var getElementsByClassName = function (className, tag, elm){
    if (document.getElementsByClassName) {
        getElementsByClassName = function (className, tag, elm) {
            elm = elm || document;
            var elements = elm.getElementsByClassName(className),
                nodeName = (tag)? new RegExp("\\b" + tag + "\\b", "i") : null,
                returnElements = [],
                current;
            for(var i=0, il=elements.length; i<il; i+=1){
                current = elements[i];
                if(!nodeName || nodeName.test(current.nodeName)) {
                    returnElements.push(current);
                }
            }
            return returnElements;
        };
    }
    else if (document.evaluate) {
        getElementsByClassName = function (className, tag, elm) {
            tag = tag || "*";
            elm = elm || document;
            var classes = className.split(" "),
                classesToCheck = "",
                xhtmlNamespace = "http://www.w3.org/1999/xhtml",
                namespaceResolver = (document.documentElement.namespaceURI === xhtmlNamespace)? xhtmlNamespace : null,
                returnElements = [],
                elements,
                node;
            for(var j=0, jl=classes.length; j<jl; j+=1){
                classesToCheck += "[contains(concat(' ', @class, ' '), ' " + classes[j] + " ')]";
            }
            try {
                elements = document.evaluate(".//" + tag + classesToCheck, elm, namespaceResolver, 0, null);
            }
            catch (e) {
                elements = document.evaluate(".//" + tag + classesToCheck, elm, null, 0, null);
            }
            while ((node = elements.iterateNext())) {
                returnElements.push(node);
            }
            return returnElements;
        };
    }
    else {
        getElementsByClassName = function (className, tag, elm) {
            tag = tag || "*";
            elm = elm || document;
            var classes = className.split(" "),
                classesToCheck = [],
                elements = (tag === "*" && elm.all)? elm.all : elm.getElementsByTagName(tag),
                current,
                returnElements = [],
                match;
            for(var k=0, kl=classes.length; k<kl; k+=1){
                classesToCheck.push(new RegExp("(^|\\s)" + classes[k] + "(\\s|$)"));
            }
            for(var l=0, ll=elements.length; l<ll; l+=1){
                current = elements[l];
                match = false;
                for(var m=0, ml=classesToCheck.length; m<ml; m+=1){
                    match = classesToCheck[m].test(current.className);
                    if (!match) {
                        break;
                    }
                }
                if (match) {
                    returnElements.push(current);
                }
            }
            return returnElements;
        };
    }
    return getElementsByClassName(className, tag, elm);
};


// ===========================================================================
// The following functions are part of scroll edit textarea on double-click
//
// This code is public domain (or primarily public domain).
// Do whatever you want with it.  In particular, you may release it under
// GPL 2.0 or incorporate it into projects that use GPL 2.0.
// -- Radomir Dopieralski and Roger D. Haase

// Debugging helpers
//  save debugging state in cookie - presence of a cookie means debugging mode is on
cookiePath = '/';
function autoScrollSetCookie (){
    document.cookie = 'autoscrolldebug=on; path=' + cookiePath + '; ';
}
function autoScrollDeleteCookie (){
    var cookie_date = new Date ( );  // current date & time
    cookie_date.setTime ( cookie_date.getTime() - 1 );
    document.cookie = 'autoscrolldebug=; expires=' + cookie_date.toGMTString() + '; path=' + cookiePath + '; ';
}
function autoScrollGetCookie (){
    var results = document.cookie.match ( '(^|;) ?' + "autoscrolldebug" + '=([^;]*)(;|$)' );
    if ( results ) {
        return ( unescape ( results[2] ) );
    } else {
        return null;
    }
}
// turn on debugging mode by previewing, saving or reading a page with "auto scroll debug on" within an h1 header
// = My Page auto scroll debug on =
// once set on,debug mode says on for current session or until turned off with
// = My Page auto scroll debug off =
autoScrollDebugOn = 0;
// this function executed on page load
function turnDebugOnOrOff () {
    // set global variable for use by cookie functions
    cookiePath = document.getElementsByName('edit_on_doubleclick')[0].content;
    var hOnes = document.getElementsByTagName('H1');
    for (var i = 0; i < hOnes.length; ++i) {
        var header = hOnes[i].textContent || hOnes[i].innerText;
        if (header.match ('auto scroll debug on')) {
            autoScrollSetCookie ();
        }
        if (header.match ('auto scroll debug off')) {
            autoScrollDeleteCookie ();
        }
    }
    if (autoScrollGetCookie ()) {
        autoScrollDebugOn = 1;
    } else {
        autoScrollDebugOn = 0;
    }
}

// functions used for testing - mouseover tooltip with tagName and scroll line number
function doMouseOver(e) {
    var targ = getNode(e);
    targ.title = 'tagName='+targ.tagName+'  line='+targ.scrollLine;
}
function doMouseOut(e) {
    var targ = getNode(e);
    targ.removeAttribute('title');
}
// add leading zeros to hours, minutes, seconds, milliseconds
function leadingZeros (nbr,count) {
    var strNbr = nbr + '';
    while (strNbr.length < count) {
        strNbr = "0" + strNbr;
    }
    return strNbr;
}
// format hours, minutes, seconds, and ms
function formatTime (t) {
    var sHours = leadingZeros (t.getHours(), 2);
    var sMinutes = leadingZeros (t.getMinutes (), 2);
    var sSeconds = leadingZeros (t.getSeconds (), 2);
    var sMilliseconds = leadingZeros (t.getMilliseconds (), 3);
    return sHours + ':' + sMinutes + ':' + sSeconds + ':' + sMilliseconds;
}

// this variable is available as easy way to display trace info
autoDebugTrace = '';
function showStartStopTimes (startTime) {
    // display a message with start and end times at top of page
    var endTime = new Date();
    var tStart ='auto scroll debug on -- Initialization start H:M:S:ms=' + formatTime (startTime);
    var tEnd = '  end H:M:S:ms=' + formatTime (endTime);
    var timingMsg = document.createElement ('P');
    timingMsg.innerHTML = tStart + tEnd;
    timingMsg.style. color = "red";
    var contentDiv;
    if (document.getElementById ('preview')) {
        contentDiv = document.getElementById ('preview');
    } else {
        contentDiv = document.getElementById ('content');
    }
    contentDiv.insertBefore (timingMsg, contentDiv.firstChild);
    // display trace info is there is any
    if (autoDebugTrace) {
        alert(autoDebugTrace);
    }
}
// end of debugging helpers

// this scrolls the textarea after a doubleclick - jumpLine is scroll-to line
function scrollTextarea(jumpLine) {
    var txtBox = document.getElementById('editor-textarea');
    scroll(0,0);
    if (txtBox) {
        // Calculate the cursor position - IE supports innerText, not textContent
        var textLines = txtBox.textContent || txtBox.innerText;
        textLines = textLines.match(/(.*\n)/g);
        var scrolledText = '';
        for (var i = 0; i < textLines.length && i < jumpLine; ++i) {
            scrolledText += textLines[i];
        }
        txtBox.focus();
        if (txtBox.setSelectionRange) {
            // Standard-compliant browsers
            // Move the cursor
            txtBox.setSelectionRange(scrolledText.length, scrolledText.length);
            // Calculate how far to scroll, by putting the text that is to be
            // above the fold in a DIV, and checking the DIV's height.
            var scrollPre = document.createElement('pre');
            txtBox.parentNode.appendChild(scrollPre);
            var style = window.getComputedStyle(txtBox, '');
            scrollPre.style.lineHeight = style.lineHeight;
            scrollPre.style.fontFamily = style.fontFamily;
            scrollPre.style.fontSize = style.fontSize;
            scrollPre.style.padding = 0;
            scrollPre.style.letterSpacing = style.letterSpacing;
            // Different browsers call this value differently:
            try { scrollPre.style.whiteSpace = "-moz-pre-wrap"; } catch(e) {}
            try { scrollPre.style.whiteSpace = "-o-pre-wrap"; } catch(e) {}
            try { scrollPre.style.whiteSpace = "-pre-wrap"; } catch(e) {}
            try { scrollPre.style.whiteSpace = "pre-wrap"; } catch(e) {}
            scrollPre.textContent = scrolledText;
            txtBox.scrollTop = scrollPre.scrollHeight-100;
            scrollPre.parentNode.removeChild(scrollPre);
        } else if (txtBox.createTextRange) {
            // Microsoft Internet Explorer
            // We don't need to scroll, it will do it automatically, just move
            // the cursor.
            var range = txtBox.createTextRange();
            range.collapse(true);
            range.moveEnd('character', scrolledText.length);
            range.moveStart('character', scrolledText.length);
            range.select();
            txtBox.__column = 1;
        }
    }
}

// stop event bubbling
function stopBubbling(e) {
    if (e.stopPropagation) {
        e.stopPropagation();
    }
    e.cancelBubble = true;
}

// stop bubbling and return event node
function getNode(e) {
    // window.event and e.srcElement are IE
    var e = e || window.event;
    var targ = e.target || e.srcElement;
    if (targ.nodeType == 3) {
        // workaround safari
        targ = targ.parentNode;
    }
    stopBubbling(e);
    return targ;
}

// add action=edit and scrollLine to document.location
function doActionEdit(e) {
    var targ = getNode(e);
    // MoinMoin counts starting with 1, scrollTextarea starts with 0
    document.location.search = '?action=edit&line='+(targ.scrollLine-1);
}

// scroll textarea on this page
function doTextareaScroll(e) {
    var targ = getNode(e);
    scrollTextarea(targ.scrollLine-1);
}

// This is the function that registers double clicks.
// isPreview is true if the current page is an edit draft preview
function setCallback(node, line, isPreview) {
    if (node.scrollLine) {
        // this node already processed
        return;
    } else {
        node.scrollLine = line;
        if(window.addEventListener){
            if (isPreview) {
                node.addEventListener('dblclick',doTextareaScroll,false);
            } else {
                node.addEventListener('dblclick',doActionEdit,false);
            }
            if (autoScrollDebugOn) {
                node.addEventListener('mouseover', doMouseOver,false);
                node.addEventListener('mouseout',doMouseOut,false);
            }
        } else {
            // IE
            if (isPreview) {
                node.attachEvent('ondblclick',doTextareaScroll);
            } else {
                node.attachEvent('ondblclick',doActionEdit);
            }
            if (autoScrollDebugOn) {
                node.attachEvent('onmouseover', doMouseOver,false);
                node.attachEvent('onmouseout',doMouseOut,false);
            }
        }
    }
}

// walk part of DOM and add doubleclick function to all nodes with tagNames
function walkDom (someNode, lineNbr, isPreview, nextId, topId) {

    //~ // handle special cases of paragraph on line after <<TOC>> and ---- (horizontal rule)
    //~ //   But this effects paragraphs on multiple lines: doubleclick goes to paragraph bottom rather than top.
    //~ //   Seems best to live with TOC and HR problem and wait for Moin2.
    //~ var next1, next2, next3;
    //~ var nextNbr = 'line-' + (lineNbr-0+1);
    //~ if (someNode.parentNode.tagName == 'P' && someNode.parentNode.scrollLine) {
        //~ next1 = someNode.nextSibling;
        //~ if (next1 && next1.tagName != 'SPAN') {
            //~ next2 = next1.nextSibling;
        //~ }
        //~ if (next2 && next2.id == nextNbr) {
            //~ alert('Correcting scrollLine='+lineNbr);
            //~ someNode.parentNode.scrollLine = lineNbr;
            //~ return;
        //~ }
    //~ }

    var doChild = true;
    while (!(someNode.id == nextId) && !(someNode.id == topId)) {
        // add children, add siblings, add parent
        if (doChild && someNode.firstChild) {
            someNode = someNode.firstChild;
        } else {
            doChild = true;
            if (someNode.nextSibling) {
                someNode = someNode.nextSibling;
            } else {
                if (someNode.parentNode.nextSibling) {
                someNode = someNode.parentNode.nextSibling;
                } else {
                    doChild = false;
                    someNode = someNode.parentNode.parentNode;
                }
            }
        }
        if (doChild && someNode.tagName && !(someNode.id == nextId) && !(someNode.id == topId)) {
            setCallback(someNode, lineNbr, isPreview);
        }
    }
}

// run during page load when user may edit current page OR is viewing draft preview
function setSpanTags(isPreview) {
    // find all the SPAN tags with an ID beginning with "line-"
    var spanTags = document.getElementsByTagName('span');
    var marks = [];
    for (var i = 0; i < spanTags.length; ++i) {
        if (spanTags[i].id && spanTags[i].id.substring(0, 5) == 'line-') {
            marks.push(spanTags[i]);
        }
    }
    var top = document.getElementById('content');
    var bottom = document.getElementById('bottom');
    // add expected stopping point to end of array for convenience
    if (bottom) {
        marks.push(bottom);
    } else {
        if (autoScrollDebugOn) {
            alert("auto scroll debug 1: document.getElementById('bottom') failed");
        }
    }
    var skipTo = -1;
    // loop through span tags and apply double-click events to appropriate node(s)
    for (i = 0; i < marks.length-1; ++i) {
        var mark = marks[i];
        // skip span tags generated by embedded parsers
        if (i > skipTo) {
            // split the ID into parts: looks line "line-22" or "line-22-1"
            var lineParts = mark.id.split('-');
            var line = lineParts[1];
            if (lineParts.length == 3) {
                // have found output from embedded parser
                // find next span id that looks like "line-n" and the "line-n-n" just before it
                var j = i - 0;
                while (lineParts.length == 3) {
                    j++;
                    lineParts = marks[j].id.split('-');
                }
                // determine how many lines, starting line number, and add double-click events
                var nbrParsedLines = j - i;
                var parsedLineNbr = lineParts[1] - nbrParsedLines - 1;
                for (var k = 0; k < nbrParsedLines; ++k) {
                    if (marks[i+k] && marks[i+k+1] && marks[i+k+1].id) {
                        walkDom (marks[i+k], parsedLineNbr+k, isPreview, marks[i+k+1].id, top.id);
                    } else {
                        if (autoScrollDebugOn) {
                            alert('auto scroll debug 2: skipping walkDom, i=' + i + ' k=' + k + ' marks[i].id=' + marks[i].id);
                        }
                    }
                }
                // done with embedded parser lines, tell main loop to skip these
                skipTo = j - 1;
            } else {
                // walk part of DOM and apply doubleclick function to every node with a tagname
                if (marks[i+1] && marks[i+1].id) {
                    walkDom (mark, line, isPreview, marks[i+1].id, top.id);
                } else {
                    if (autoScrollDebugOn) {
                        alert('auto scroll debug 3: skipping walkDom, i=' + i + ' marks[i].id=' + marks[i].id);
                    }
                }
            }
        }
    }
    if (autoScrollDebugOn)  {
        for (i = 0; i < marks.length-1; ++i) {
            marks[i].innerHTML = ' ' + marks[i].id + ' ';
            marks[i].style. color = "red";
        }
    }
}

// test to see if this user has selected or defaulted to edit_on_doubleclick AND
// whether we are viewing a page, editing a page, or previewing an edit draft
function scrollTextareaInit() {
    // look for meta tag -- is edit_on_doubleclick present?
    if (!document.getElementsByName('edit_on_doubleclick').length) {
        return;
    }
    turnDebugOnOrOff ();
    // are we viewing a page - both gui and text editors will have button named button_save
    if (!document.getElementsByName('button_save').length) {
        setSpanTags(0);
        return;
    }
    // we are in editor -- is there a line number specified in URL?
    var lineMatch = document.location.search.match(/line=(\d*)/);
    if (lineMatch) {
        scrollTextarea(lineMatch[1]);
        return;
    }
    if (document.getElementById('preview')) {
        // is an editor preview
        setSpanTags(1);
    }
}

// Now to resolve the problem of how to best execute scrollTextareaInit
// -- We want to run as soon as DOM is loaded, perhaps many seconds before last big image is loaded
// -- If we wait for body.onload, the user may see and doubleclick on text before we are ready
// -- If every browser supported DOMContentLoaded, we could do:
//         document.addEventListener("DOMContentLoaded", scrollTextareaInit, false);
// -- If we had jQuery, we could do:
//         jQuery(scrollTextareaInit);
// -- Another possibility is to add a bit of script near the end of the mypage.HTML, hoping the DOM is ready
//         '<script type="text/javascript" language="javascript">scrollTextareaInit()</script>'
// -- Our choice is to speed up most current browsers and do slow but sure for the rest:

// run scrollTextareaInit one time;  this function will be called twice for almost all browsers,
scrollTextareaInitComplete = 0;
function runScrollTextareaInitOnce() {
    // uncomment next line to test - most browsers will display this alert twice
    //~ alert('scrollTextareaInitComplete=' + scrollTextareaInitComplete);
    if (scrollTextareaInitComplete) {
        return;
    }
    scrollTextareaInitComplete = 1;
    var startTime = new Date();
    scrollTextareaInit();
    if (autoScrollDebugOn && document.getElementById('content')) {
        showStartStopTimes(startTime);
    }
}

// speed up most browsers -- run my function As Soon As Possible
function runASAP(func) {
    if (document.addEventListener) {
        // Firefox 3.6, Chrome 4.0.249.89, Safari for Windows 4.04, Opera 10.5beta, and maybe older versions
        // schedule func to be run when DOM complete
        document.addEventListener("DOMContentLoaded", func, false);
    } else {
        // trick discovered by Diego Perini to test for IE DOM complete
        if (document.documentElement.doScroll && window == window.top) {
            try {
                document.documentElement.doScroll("left");
                // DOM is complete; run func now
                func();
            } catch(e) {
                // wait and try again
                setTimeout(arguments.callee, 1);
            }
        }
    }
}


runASAP(runScrollTextareaInitOnce);
// ensure init will be run by obsolete browsers
addLoadEvent(runScrollTextareaInitOnce);

// ===========================================================================
// The following functions are part of jQuery code

$(function() {
    // Only submit actions menu form if option of select is not first
    $('.moin-actionsmenu-select').change(function() {
        if ((this.selectedIndex != 0) && (this.options[this.selectedIndex].disabled == false)) {
            $(this).parents('form').submit();
        }
        this.selectedIndex = 0;
    });

});

// Insert Zero-Width-Space characters into long text strings of textNode elements.
// Firefox does not support CSS with {word-wrap: break-word;} within tables.
// As a result, Firefox may display tables with long urls or page names as very wide tables.
// This function alters tables by inserting a zero-width-space into long text strings after every 5 characters.
// The moin-wordbreak class is intended for use on TD elements, but may be used on TABLE, TR, THEAD, TBODY, or TFOOT.
function moinFirefoxWordBreak() {
    // TODO:  Test for browser version when/if a future Firefox supports break-word within tables.
    if (!jQuery.browser.mozilla) {
        return;
    }
    var child;
    var words;
    var parents;
    var i, j;
    // Only textNodes are of interest, but there is no way to select them directly.
    // Select all elements with the moin-wordbreak class and add all selectable descendants of those elements.
    // Then search for children that are textNodes; TDs or THs and elements descended from them are likely parents of textNodes.
    parents = jQuery(".moin-wordbreak").add(".moin-wordbreak *");
    for (i = 0; i < parents.length; i++) {
        child = parents[i].firstChild;
        while(child) {
            if (child.nodeType === 3) {
                words = child.textContent.split(" ");
                for (j = 0; j < words.length; j++) {
                    // \u200B denotes a zero-width-space character (for easy testing, replace with a visible character like Q)
                    words[j] = words[j].replace(/(.{5})/g,"$1\u200B");
                }
                child.textContent = words.join(" ");
            }
            child = child.nextSibling;
        }
    }
}
jQuery(moinFirefoxWordBreak);

/* For the overlays on transcluded objects */
function removeURLPrefixes(url) {
    return url.replace("+get/", "").replace("+modify/", "")
}
function attachHoverToObjects() {
    $(".page-object").mouseenter(function(e) {
        elements = $(".object-overlay", this)
        elements.each(function(i) {
            if (location.href == removeURLPrefixes(this.firstChild.href)) {
                var elem = $(this)
                setTimeout(function() {
                    elem.hide()
                }, 10)
            }
        })

        $(elements.slice(1)).hide()
    })
}

$(document).ready(attachHoverToObjects)

/*
    For the quicklinks patch that
    makes all quicklinks after the 5th visible only by mousing over an icon.
*/
function getLinks() {
    return jQuery(".userlink:not(.moin-navibar-icon)");
}

function createIcon(txt) {
    var li = document.createElement("li");
    li.setAttribute("class", "moin-userlink moin-navibar-icon");

    var txt = document.createTextNode(txt);
    li.appendChild(txt);

    return li
}

function appendIcon(txt) {
    var elem = createIcon(txt);

    document.getElementById("moin-navibar").appendChild(elem);
    return elem
}

function shouldHide(links) {
    return (links.length > 5);
}

function getHideableLinks() {
    return getLinks().slice(5);
}

function hideShowHideableLinks(action) {
    getHideableLinks().each(function(i) {
        if (action == "hide") {
            $(this).hide();
        }
        else  {
            $(this).show();
        }
    });
}

function hideLinks() {
    hideShowHideableLinks("hide");
}

function showLinks() {
    hideShowHideableLinks("show");
}

function QuicklinksExpander() {
    this.getLinks = getLinks;
    this.appendIcon = appendIcon;
    this.shouldHide = shouldHide;
    this.getHideableLinks = getHideableLinks;
    this.hideLinks = hideLinks;
    this.showLinks = showLinks;

    this.navibar = $("#moin-header");
    this.links = this.getLinks();
    this.hideable = this.getHideableLinks();

    // If there's less than 5 items, don't bother doing anything.
    if (this.shouldHide(this.links)) {
        this.expandIcon = $(this.appendIcon(QUICKLINKS_EXPAND));
        this.closeIcon = $(this.appendIcon(QUICKLINKS_COLLAPSE));

        this.closeIcon.hide();

        // Hide everything after the first 5
        this.hideLinks();

        /*
        TODO: when FF4.0 becomes stable/popular, delete the following hack
        and use function.bind(this)
        */
        var newThis = this;

        // When the user mouses over the icon link,
        // Show the hidden links
        this.expandIcon.mouseenter(function(e) {
            newThis.showLinks();
            newThis.expandIcon.hide();
            newThis.closeIcon.show();

        });

        this.closeIcon.mouseenter(function(e) {
            newThis.hideLinks();
            newThis.expandIcon.show();
            newThis.closeIcon.hide();
        });
    }
}

jQuery(document).ready(function() {
    new QuicklinksExpander();
})

function toggleSubtree(item) {
    /* used to toggle subtrees in the subitem widget */
    var subtree = $(item).siblings("ul");
    subtree.toggle(200);
}

function guessContentType() {
    /* Used in the modify_text template to guess the data content type client-side 
     * This approach has the advantage of reacting to content type changes for the 
     * link/transclude code without having to re-fetch the page */
    var meta_text = $("#f_meta_text").val();
    var ctype_regex = /["']contenttype["']\s*:\s*["']([\w-_+.]+\/[\w-_+.]+)(;|["'])/;
    if (meta_text) {
        var match = ctype_regex.exec(meta_text);
        if (match) return match[1];
    }
    // text/plain is the default value
    return "text/plain";
}

function transcludeSubitem(subitem_name, fullname) {
    function moinwiki(subitem_name, fullname) {
        return "{{" + fullname.replace("{{", "\\}}") + "}} ";
    }
    function mediawiki(subitem_name, fullname) {
        return "{{:" + fullname.replace("}}", "\\}}") + "}} ";
    }
    function rst(subitem_name, fullname) {
        return "\n.. include:: " + subitem_name + "\n";
    }
    function docbook(subitem_name, fullname) {
        return ""; //XXX: the docbook converter currently doesn't handle transclusion with <ref> tags
    }
    var transclude_formats = {
        "text/x.moin.wiki" : moinwiki,
        "text/x.moin.creole" : moinwiki,
        "text/x-mediawiki" : mediawiki,
        "text/x-rst" : rst,
        "application/docbook+xml" : docbook,
        "text/plain" : function(x){return x + " ";},
    }
    var ctype = guessContentType();
    var input_element = $("#f_data_text");
    var ctype_format = transclude_formats[ctype];
    if (!ctype_format) ctype_format = transclude_formats["text/plain"];
    input_element.val(input_element.val() + ctype_format(subitem_name, fullname));
    input_element.focus();
}

function linkSubitem(subitem_name, fullname) {
    function moinwiki(subitem_name, fullname) {
        return "[[" + fullname.replace("]", "\\]") + "|" + subitem_name.replace("]", "\\]") + "]] ";
    }
    function rst(subitem_name, fullname) {
        return "`" + subitem_name.replace(">", "\\>").replace("`", "\\`") + " <" + fullname.replace(">", "\\>") + ">`_ ";
    }
    function docbook(subitem_name, fullname) {
        return '<ulink url="/' + fullname.replace('"', '\\"') + '">' + subitem_name + "</ulink>";;
    }
    var link_formats = {
        "text/x.moin.wiki" : moinwiki,
        "text/x.moin.creole" : moinwiki,
        "text/x-mediawiki" : moinwiki,
        "text/x-rst" : rst,
        "application/docbook+xml" : docbook,
        "text/plain" : function(x){return x + " ";},
    }
    var ctype = guessContentType();
    var input_element = $("#f_data_text");
    var ctype_format = link_formats[ctype];
    if (!ctype_format) ctype_format = link_formats["text/plain"];
    input_element.val(input_element.val() + ctype_format(subitem_name, fullname));
    input_element.focus();
}

function initMoinTabs($) {
    "use strict";
    // find all .moin-tabs elements and initialize them
    $('.moin-tabs').each(function () {
        var tabs = $(this),
            titles = $(document.createElement('ul')),
            lastLocationHash;
        titles.addClass('moin-tab-titles');

        // switching between tabs based on the current location hash
        function updateFromLocationHash() {
            if (location.hash !== undefined && location.hash !== '' && tabs.children(location.hash).length) {
                if (location.hash !== lastLocationHash) {
                    lastLocationHash = location.hash;
                    tabs.children('.moin-tab-body').hide();
                    tabs.children(location.hash).show();
                    titles.children('li').children('a').removeClass('current');
                    titles.children('li').children('a[href="' + location.hash + '"]').addClass('current');
                }
            } else {
                $(titles.children('li').children('a')[0]).click();
            }
        }

        // move all tab titles to an <ul> at the beginning of .moin-tabs
        tabs.children('.moin-tab-title').each(function () {
            var li = $(document.createElement('li')),
                a = $(this).children('a');
            a.click(function () {
                location.hash = this.hash;
                updateFromLocationHash();
                return false;
            });
            li.append(a);
            titles.append(li);
            $(this).remove();
        });
        tabs.prepend(titles);

        updateFromLocationHash();
        setInterval(updateFromLocationHash, 40); // there is no event for that
    });
}

jQuery(document).ready(initMoinTabs);

function initMoinUsersettings($) {
    "use strict";
    // save initial values of each form
    $('#moin-usersettings form').each(function () {
        $(this).data('initialForm', $(this).serialize());
    });

    // check if any changes were made
    function changeHandler(ev) {
        var form = $(ev.currentTarget),
            title = $('.moin-tab-titles a.current', form.parentsUntil('.moin-tabs').parent()),
            e;
        if (form.data('initialForm') === form.serialize()) {
            // current values are identicaly to initial ones, remove all change indicators (if any)
            $('.change-indicator', title).remove();
        } else {
            // the values differ
            if (!$('.change-indicator', title).length) {
                // only add a change indicator if there none
                e = $(document.createElement('span'));
                e.addClass('change-indicator');
                e.text('*');
                title.append(e);
            }
        }
    }
    $('#moin-usersettings form').change(changeHandler);

    function submitHandler(ev) {
        var form = $(ev.target),
            button = $('button', form),
            buttonBaseText = button.html(),
            buttonDotList = [' .&nbsp;&nbsp;', ' &nbsp;.&nbsp;', ' &nbsp;&nbsp;.'],
            buttonDotIndex = 0,
            buttonDotAnimation;

        // disable the button
        button.attr('disabled', true);

        // remove change indicators from the current tab as we are now saving it
        $('.moin-tab-titles a.current .change-indicator',
                form.parentsUntil('.moin-tabs').parent()).remove();

        // animate the submit button to indicating a running request
        function buttonRunAnimation() {
            button.html(buttonBaseText + buttonDotList[buttonDotIndex % buttonDotList.length]);
            buttonDotIndex += 1;
        }
        buttonDotAnimation = setInterval(buttonRunAnimation, 500);
        buttonRunAnimation();

        // send the form to the server
        $.post(form.attr('action'), form.serialize(), function (data) {
            var i, f, newform;
            clearInterval(buttonDotAnimation);
            // if the response indicates a redirect, set the new location
            if (data.redirect) {
                location.href = data.redirect;
                return;
            }
            // remove all flash messages previously added via javascript
            $('#moin-header .moin-flash-javascript').remove();
            // add new flash messages from the response
            for (i = 0; i < data.flash.length; i += 1) {
                f = $(document.createElement('p'));
                f.html(data.flash[i][0]);
                f.addClass('moin-flash');
                f.addClass('moin-flash-javascript');
                f.addClass('moin-flash-' + data.flash[i][1]);
                $('#moin-header').append(f);
            }
            // get the new form element from the response
            newform = $(data.form);
            // set event handlers on the new form
            newform.submit(submitHandler);
            newform.change(changeHandler);
            // store the forms initial data
            newform.data('initialForm', newform.serialize());
            // replace the old form with the new one
            form.replaceWith(newform);
        }, 'json');
        return false;
    }
    $('#moin-usersettings form').submit(submitHandler);
}

jQuery(document).ready(initMoinUsersettings);
