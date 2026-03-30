// Copyright: 2026 by MoinMoin project
// License: GNU GPL v2 (or any later version), see LICENSE.txt for details.
//
// svgedit extension for interfacing with the Moin2 wiki.
//
// The content of this file is in parts derived from:
// <https://github.com/SVG-Edit/svgedit/blob/master/src/editor/extensions/ext-opensave/ext-opensave.js>

import { __vitePreload } from "../_virtual/preload-helper.js";

const name = 'moin2';

function __variableDynamicImportRuntime0__(path) {
  switch (path) {
    case "./locale/en.js":
      return __vitePreload(() => import("./locale/en.js"), true ? [] : void 0, import.meta.url);
    case "./locale/fr.js":
      return __vitePreload(() => import("./locale/fr.js"), true ? [] : void 0, import.meta.url);
    case "./locale/sv.js":
      return __vitePreload(() => import("./locale/sv.js"), true ? [] : void 0, import.meta.url);
    case "./locale/tr.js":
      return __vitePreload(() => import("./locale/tr.js"), true ? [] : void 0, import.meta.url);
    case "./locale/uk.js":
      return __vitePreload(() => import("./locale/uk.js"), true ? [] : void 0, import.meta.url);
    case "./locale/zh-CN.js":
      return __vitePreload(() => import("./locale/zh-CN.js"), true ? [] : void 0, import.meta.url);
    default:
      return new Promise(function(resolve, reject) {
        (typeof queueMicrotask === "function" ? queueMicrotask : setTimeout)(
          reject.bind(null, new Error("Unknown variable dynamic import: " + path))
        );
      });
  }
}

const loadExtensionTranslation = async function(svgEditor) {
  let translationModule;
  const lang = svgEditor.configObj.pref("lang");
  try {
    translationModule = await __variableDynamicImportRuntime0__(`./locale/${lang}.js`);
  } catch (_error) {
    console.warn(`Missing translation (${lang}) for ${name} - using 'en'`);
    translationModule = await __vitePreload(() => import("./locale/en.js"), true ? [] : void 0, import.meta.url);
  }
  svgEditor.i18next.addResourceBundle(lang, "translation", translationModule.default, true, true);
};

const extMoin2 = {
  name,
  async init (_S) {
    const svgEditor = this;
    const { svgCanvas } = svgEditor;
    const { $id, $click } = svgCanvas;

    await loadExtensionTranslation(svgEditor);

    const saveSvn = async function(type) {
        const item_name = this.$container.getAttribute("data-fullname");
        console.log(`moin2 save: item name is ${item_name}`);
        svgCanvas.clearSelection();
        const svg_content = '<?xml version="1.0"?>\n' + svgCanvas.svgCanvasToString();
        const svg_data = svgCanvas.encode64(svg_content);
        const _results = await svgCanvas.rasterExport("PNG", 1.0, 'Exported Image', {avoidEvent: true});
        const png_data = _results.datauri;
        //
        const form = document.createElement("form");
        form.method = "POST";
        form.action = `/+modify/${item_name}?itemtype=default&contenttype=application/x-svgdraw&template=`;
        //
        var input = document.createElement('INPUT');
        input.type = "hidden";
        input.name = "filename"
        input.value = "drawing.svg"
        form.appendChild(input);
        //
        input = document.createElement('INPUT');
        input.type = "hidden";
        input.name = "filepath"
        input.value = svg_data
        form.appendChild(input);
        //
        input = document.createElement('INPUT');
        input.type = "hidden";
        input.name = "png_data"
        input.value = png_data
        form.appendChild(input);
        //
        input = document.createElement('INPUT');
        input.type = "hidden";
        input.name = "contenttype"
        input.value = "application/x-svgdraw"
        form.appendChild(input);
        //
        document.body.appendChild(form);
        // prevent leave dialog
        this.setConfig({no_save_warning: true});
        form.submit();
        form.remove();
    };

    return {
      name,
      eventBased: true,
      callback () {
        console.log('moin2 init');
        const buttonTemplate = `
        <se-menu-item id="tool_clear" label="moin2.new_doc" shortcut="N" src="new.svg"></se-menu-item>`;
        svgCanvas.insertChildAtIndex($id("main_button"), buttonTemplate, 0);
        const saveButtonTemplate = '<se-menu-item id="tool_save" label="moin2.save_doc" shortcut="S" src="saveImg.svg"></se-menu-item>';
        svgCanvas.insertChildAtIndex($id("main_button"), saveButtonTemplate, 2);
        $click($id("tool_save"), saveSvn.bind(this, "save"));
      }
    }
  }
};

export default extMoin2;
