import { __vitePreload } from "../_virtual/preload-helper.js";
function __variableDynamicImportRuntime0__(path) {
  switch (path) {
    case "./locale/en.js":
      return __vitePreload(() => import("./locale/en.js"), true ? [] : void 0, import.meta.url);
    case "./locale/fr.js":
      return __vitePreload(() => import("./locale/fr.js"), true ? [] : void 0, import.meta.url);
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
const name = "helloworld";
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
const extHelloworld = {
  name,
  async init({ _importLocale }) {
    const svgEditor = this;
    await loadExtensionTranslation(svgEditor);
    const { svgCanvas } = svgEditor;
    const { $id, $click } = svgCanvas;
    return {
      name: svgEditor.i18next.t(`${name}:name`),
      callback() {
        const buttonTemplate = document.createElement("template");
        const title = `${name}:buttons.0.title`;
        buttonTemplate.innerHTML = `
        <se-button id="hello_world" title="${title}" src="hello_world.svg"></se-button>
        `;
        $id("tools_left").append(buttonTemplate.content.cloneNode(true));
        $click($id("hello_world"), () => {
          svgCanvas.setMode("hello_world");
        });
      },
      // This is triggered when the main mouse button is pressed down
      // on the editor canvas (not the tool panels)
      mouseDown() {
        if (svgCanvas.getMode() === "hello_world") {
          return { started: true };
        }
        return void 0;
      },
      // This is triggered from anywhere, but "started" must have been set
      // to true (see above). Note that "opts" is an object with event info
      mouseUp(opts) {
        if (svgCanvas.getMode() === "hello_world") {
          const zoom = svgCanvas.getZoom();
          const x = opts.mouse_x / zoom;
          const y = opts.mouse_y / zoom;
          const text = svgEditor.i18next.t(`${name}:text`, { x, y });
          alert(text);
        }
      }
    };
  }
};
export {
  extHelloworld as default
};
//# sourceMappingURL=ext-helloworld.js.map
