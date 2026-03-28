import { __vitePreload } from "../_virtual/preload-helper.js";
function __variableDynamicImportRuntime0__(path) {
  switch (path) {
    case "./locale/en.js":
      return __vitePreload(() => import("./locale/en.js"), true ? [] : void 0, import.meta.url);
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
const name = "panning";
const loadExtensionTranslation = async function(svgEditor) {
  let translationModule;
  const lang = svgEditor.configObj.pref("lang");
  try {
    translationModule = await __variableDynamicImportRuntime0__(`./locale/${lang}.js`);
  } catch (_error) {
    console.warn(`Missing translation (${lang}) for ${name} - using 'en'`);
    translationModule = await __vitePreload(() => import("./locale/en.js"), true ? [] : void 0, import.meta.url);
  }
  svgEditor.i18next.addResourceBundle(lang, name, translationModule.default);
};
const extPanning = {
  name,
  async init() {
    const svgEditor = this;
    await loadExtensionTranslation(svgEditor);
    const {
      svgCanvas
    } = svgEditor;
    const { $id, $click } = svgCanvas;
    const insertAfter = (referenceNode, newNode) => {
      referenceNode.parentNode.insertBefore(newNode, referenceNode.nextSibling);
    };
    return {
      name: svgEditor.i18next.t(`${name}:name`),
      callback() {
        const btitle = `${svgEditor.i18next.t(`${name}:buttons.0.title`)} ${svgEditor.i18next.t(`${name}:buttons.0.key`)}`;
        const buttonTemplate = document.createElement("template");
        buttonTemplate.innerHTML = `
        <se-button id="ext-panning" title="${btitle}" src="panning.svg"></se-button>
        `;
        insertAfter($id("tool_zoom"), buttonTemplate.content.cloneNode(true));
        $click($id("ext-panning"), () => {
          if (this.leftPanel.updateLeftPanel("ext-panning")) {
            svgCanvas.setMode("ext-panning");
          }
        });
      },
      mouseDown() {
        if (svgCanvas.getMode() === "ext-panning") {
          svgEditor.setPanning(true);
          return {
            started: true
          };
        }
        return void 0;
      },
      mouseUp() {
        if (svgCanvas.getMode() === "ext-panning") {
          svgEditor.setPanning(false);
          return {
            keep: false,
            element: null
          };
        }
        return void 0;
      }
    };
  }
};
export {
  extPanning as default
};
//# sourceMappingURL=ext-panning.js.map
