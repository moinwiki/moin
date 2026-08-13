/*
    * Copyright 2010, Sebastian Tschan, https://blueimp.net
-   * Licensed under the MIT license:
-   * http://creativecommons.org/licenses/MIT/

    * Copyright 2021 MoinMoin:RogerHaase, modified for moinmoin2
    * License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

    Upload multiple jpg files using jquery-file-upload. Tested with version 10.31.0.

    Reference: https://github.com/blueimp/jQuery-File-Upload/wiki/Basic-plugin#how-to-display-individual-upload-progress-with-the-basic-plugin

    Uploads are started when files are selected, there are no limits on file size
    nor number of files.
*/

$(function () {
    "use strict";
    $('#jfu-fileupload').fileupload({
        dataType: 'json',
        start: function (e) {
            $("#jfu-progress").removeClass("hidden");
        },
        add: function(e, data) {
            // show file upload progress bar and overall progress bar after user selects files
            const progress = Object.assign(document.createElement('p'), { className: 'jfu-file' });
            progress.textContent = 'Uploading... ';
            const fileName = Object.assign(document.createElement('b'), { textContent: data.files[0].name });
            progress.appendChild(fileName);
            const progressContainer = document.getElementById('jfu-progress');
            if (progressContainer) {
                progressContainer.appendChild(progress);
            }
            data.context = progress;
            data.submit();
        },
        progressall: function (e, data) {
            // overall progress bar
            var progress = parseInt(data.loaded / data.total * 100, 10);
            $('#jfu-progress .jfu-bar').text('\u00a0 Overall Progress');
            $('#jfu-progress .jfu-bar').css('padding', '1em 0 1em 0');
            $('#jfu-progress .jfu-bar').css('width', `${progress}%`);
        },
        progress: function(e, data) {
            // create file progress bar for each file selected
            var progress = parseInt((data.loaded / data.total) * 100, 10);
            data.context.style.backgroundPositionX = `${100 - progress}%`;
        },
        done: function (e, data) {
            const response = data.result;
            // show success/fail message for the file uploaded file
            data.context.textContent = response.message;
            // class is passed when upload fails, 403s are returned as 200 with error message
            data.context.classList.add(response.css_class);
            // if the upload succeeded add a row to the index table; not all cells are populated
            if (!response.css_class) {
                const rawHtmlFragment = `
                    <tr class="jfu-recent">
                        <td class="moin-index-icons">
                        <span class="moin-select-item" onclick="classtoggle(this)">
                            <input class="moin-item" type="checkbox" value="${response.url}" />
                        </span>
                        <span><i class="fa fa-upload"></i></span>
                        </td>
                        <td><a href="${response.url}">${response.url}</a></td>
                        <td class="moin-integer">${response.size}</td>
                        <td class="moin-integer">1</td>
                        <td></td>
                        <td></td>
                    </tr>`.trim();
                const template = document.createElement('template');
                template.innerHTML = window.moinPolicy.createHTML(rawHtmlFragment)
                const newRow = template.content.firstElementChild;
                const tbody = document.querySelector('table.moin-index tbody');
                if (tbody && newRow) {
                    tbody.insertAdjacentElement('afterbegin', newRow);
                }
                // update item count in upper left of table
                $(".moin-num-rows").text($('.moin-index tbody tr').length);
            }
        },
    });
});

function classtoggle(e) {
    "use strict";
    e.parent().toggleClass("selected-item");
}
