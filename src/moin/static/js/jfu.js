/*
 * Copyright 2021 MoinMoin:RogerHaase
 * License: GNU GPL v2 (or any later version), see LICENSE.txt for details.
 *
 * Upload multiple files from the +index view, without any 3rd party upload library.
 *
 * Files can be selected with the file input's dialog or dropped anywhere on the page.
 * Each file is POSTed in a separate request (as multipart/form-data field "file_storage")
 * to the URL given in the file input's data-url attribute (the +jfu-server view), which
 * answers with JSON: {message, url, size} or {message, css_class: "jfu-failed"}.
 *
 * Uploads start as soon as files are selected. There are no limits on file size
 * nor number of files.
 */

document.addEventListener("DOMContentLoaded", function () {
    "use strict";
    const fileInput = document.getElementById("jfu-fileupload");
    const progressContainer = document.getElementById("jfu-progress");
    if (!fileInput || !progressContainer) {
        return;
    }
    const overallBar = progressContainer.querySelector(".jfu-bar");
    const submitUrl = fileInput.dataset.url;
    // bytes loaded / total per active upload, used for the overall progress bar
    const uploads = new Set();

    function percent(loaded, total) {
        return total ? Math.floor(loaded / total * 100) : 100;
    }

    function updateOverallProgress() {
        let loaded = 0;
        let total = 0;
        for (const upload of uploads) {
            loaded += upload.loaded;
            total += upload.total;
        }
        overallBar.textContent = "  Overall Progress";
        overallBar.style.padding = "1em 0 1em 0";
        overallBar.style.width = `${percent(loaded, total)}%`;
    }

    function addIndexRow(response) {
        // if the upload succeeded add a row to the index table; not all cells are populated
        const tbody = document.querySelector("table.moin-index tbody");
        if (!tbody) {
            return;
        }
        const row = document.createElement("tr");
        row.className = "jfu-recent";

        const iconsCell = document.createElement("td");
        iconsCell.className = "moin-index-icons";
        const selectSpan = document.createElement("span");
        selectSpan.className = "moin-select-item";
        const checkbox = document.createElement("input");
        checkbox.className = "moin-item";
        checkbox.type = "checkbox";
        checkbox.value = response.url;
        selectSpan.appendChild(checkbox);
        const iconSpan = document.createElement("span");
        const icon = document.createElement("i");
        icon.className = "fa fa-upload";
        iconSpan.appendChild(icon);
        iconsCell.append(selectSpan, iconSpan);

        const nameCell = document.createElement("td");
        const link = document.createElement("a");
        link.href = response.url;
        link.textContent = response.url;
        nameCell.appendChild(link);

        const sizeCell = document.createElement("td");
        sizeCell.className = "moin-integer";
        sizeCell.textContent = response.size;

        const revCell = document.createElement("td");
        revCell.className = "moin-integer";
        revCell.textContent = "1";

        row.append(iconsCell, nameCell, sizeCell, revCell, document.createElement("td"), document.createElement("td"));
        tbody.insertAdjacentElement("afterbegin", row);

        // update item count in upper left of table
        const numRows = document.querySelector(".moin-num-rows");
        if (numRows) {
            numRows.textContent = tbody.querySelectorAll("tr").length;
        }
    }

    function uploadFile(file) {
        // show a progress bar for this file
        const progress = document.createElement("p");
        progress.className = "jfu-file";
        progress.textContent = "Uploading... ";
        const fileName = document.createElement("b");
        fileName.textContent = file.name;
        progress.appendChild(fileName);
        progressContainer.appendChild(progress);
        progressContainer.classList.remove("hidden");

        const upload = { loaded: 0, total: file.size };
        uploads.add(upload);
        updateOverallProgress();

        function finish(response) {
            upload.loaded = upload.total;
            updateOverallProgress();
            uploads.delete(upload);
            // show success/fail message for the uploaded file
            progress.textContent = response.message;
            // class is passed when upload fails, 403s are returned as 200 with error message
            if (response.css_class) {
                progress.classList.add(response.css_class);
            } else {
                progress.style.backgroundPositionX = "0%";
                addIndexRow(response);
            }
        }

        const formData = new FormData();
        formData.append(fileInput.name, file);
        // XMLHttpRequest instead of fetch, because fetch can not report upload progress
        const xhr = new XMLHttpRequest();
        xhr.open("POST", submitUrl);
        xhr.responseType = "json";
        xhr.upload.addEventListener("progress", function (e) {
            if (e.lengthComputable) {
                upload.loaded = e.loaded;
                upload.total = e.total;
                progress.style.backgroundPositionX = `${100 - percent(e.loaded, e.total)}%`;
                updateOverallProgress();
            }
        });
        xhr.addEventListener("load", function () {
            if (xhr.status === 200 && xhr.response && typeof xhr.response.message === "string") {
                finish(xhr.response);
            } else {
                finish({ message: `Upload failed: ${file.name} (HTTP ${xhr.status})`, css_class: "jfu-failed" });
            }
        });
        xhr.addEventListener("error", function () {
            finish({ message: `Upload failed: ${file.name} (network error)`, css_class: "jfu-failed" });
        });
        xhr.send(formData);
    }

    function uploadFiles(files) {
        for (const file of files) {
            uploadFile(file);
        }
    }

    fileInput.addEventListener("change", function () {
        uploadFiles(Array.from(fileInput.files));
        // allow selecting the same file(s) again
        fileInput.value = "";
    });

    // files dropped anywhere on the page get uploaded
    function hasFiles(e) {
        return e.dataTransfer && Array.from(e.dataTransfer.types).includes("Files");
    }
    document.addEventListener("dragover", function (e) {
        if (hasFiles(e)) {
            e.preventDefault();
            e.dataTransfer.dropEffect = "copy";
        }
    });
    document.addEventListener("drop", function (e) {
        if (hasFiles(e)) {
            e.preventDefault();
            uploadFiles(Array.from(e.dataTransfer.files));
        }
    });
});
