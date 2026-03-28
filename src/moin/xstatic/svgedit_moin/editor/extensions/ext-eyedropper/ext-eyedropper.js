import { __vitePreload } from "../_virtual/preload-helper.js";
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
const name = "eyedropper";
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
const extEyedropper = {
  name,
  async init() {
    const svgEditor = this;
    const { svgCanvas } = svgEditor;
    await loadExtensionTranslation(svgEditor);
    const { ChangeElementCommand } = svgCanvas.history;
    const addToHistory = (cmd) => {
      svgCanvas.undoMgr.addCommandToHistory(cmd);
    };
    const currentStyle = {};
    const { $id, $click } = svgCanvas;
    const helperCursor = document.createElement("div");
    helperCursor.style.width = "14px";
    helperCursor.style.height = "14px";
    helperCursor.style.position = "absolute";
    svgEditor.workarea.appendChild(helperCursor);
    const styleHelper = () => {
      const mode = svgCanvas.getMode();
      if (mode === name) {
        helperCursor.style.display = "block";
        const strokeWidthNum = Number(currentStyle.strokeWidth);
        const borderStyle = currentStyle.strokeDashArray === "none" || !currentStyle.strokeDashArray ? "solid" : "dotted";
        helperCursor.style.background = currentStyle.fillPaint ?? "transparent";
        helperCursor.style.opacity = currentStyle.opacity ?? 1;
        helperCursor.style.border = strokeWidthNum > 0 && currentStyle.strokePaint ? `2px ${borderStyle} ${currentStyle.strokePaint}` : "none";
      }
    };
    const resetCurrentStyle = () => {
      const keys = Object.keys(currentStyle);
      keys.forEach((key) => delete currentStyle[key]);
    };
    const cancelHandler = () => {
      if (Object.keys(currentStyle).length > 0) {
        resetCurrentStyle();
        styleHelper();
      } else {
        svgEditor.leftPanel.clickSelect();
      }
    };
    const getStyle = (opts) => {
      let elem = null;
      if (!opts.multiselected && opts.elems[0] && !["svg", "g", "use"].includes(opts.elems[0].nodeName)) {
        elem = opts.elems[0];
        currentStyle.fillPaint = elem.getAttribute("fill") || "black";
        currentStyle.fillOpacity = elem.getAttribute("fill-opacity") || 1;
        currentStyle.strokePaint = elem.getAttribute("stroke");
        currentStyle.strokeOpacity = elem.getAttribute("stroke-opacity") || 1;
        currentStyle.strokeWidth = elem.getAttribute("stroke-width");
        currentStyle.strokeDashArray = elem.getAttribute("stroke-dasharray");
        currentStyle.strokeLinecap = elem.getAttribute("stroke-linecap");
        currentStyle.strokeLinejoin = elem.getAttribute("stroke-linejoin");
        currentStyle.opacity = elem.getAttribute("opacity") || 1;
      }
    };
    return {
      name: svgEditor.i18next.t(`${name}:name`),
      callback() {
        const title = `${name}:buttons.0.title`;
        const key = "ctrl+I";
        const buttonTemplate = `
        <se-button id="tool_eyedropper" title="${title}" src="eye_dropper.svg" shortcut=${key}></se-button>
        `;
        svgCanvas.insertChildAtIndex($id("tools_left"), buttonTemplate, 12);
        $click($id("tool_eyedropper"), () => {
          if (this.leftPanel.updateLeftPanel("tool_eyedropper")) {
            svgCanvas.setMode(name);
          }
        });
        document.addEventListener("modeChange", (e) => {
          if (svgCanvas.getMode() === name) {
            styleHelper();
          } else {
            helperCursor.style.display = "none";
          }
          if (svgCanvas.getSelectedElements().length === 0) {
            resetCurrentStyle();
          }
        });
        svgEditor.workarea.addEventListener("mousemove", (e) => {
          const x = e.clientX;
          const y = e.clientY;
          if (svgCanvas.getMode() === name) {
            helperCursor.style.top = y + "px";
            helperCursor.style.left = x + 12 + "px";
            styleHelper();
          }
        });
        svgEditor.workarea.addEventListener("mouseleave", (e) => {
          helperCursor.style.display = "none";
        });
        document.addEventListener("keydown", (e) => {
          if (e.key === "Escape" && svgCanvas.getMode() === name) {
            cancelHandler();
          }
        });
      },
      // if we have selected an element, grab its paint and enable the eye dropper button
      selectedChanged: getStyle,
      mouseDown(opts) {
        const mode = svgCanvas.getMode();
        if (mode === name) {
          const e = opts.event;
          const { target } = e;
          if (!["svg", "g", "use"].includes(target.nodeName)) {
            const changes = {};
            if (Object.keys(currentStyle).length > 0) {
              const change = function(elem, attrname, newvalue) {
                changes[attrname] = elem.getAttribute(attrname);
                elem.setAttribute(attrname, newvalue);
              };
              if (currentStyle.fillPaint) {
                change(target, "fill", currentStyle.fillPaint);
              }
              if (currentStyle.fillOpacity) {
                change(target, "fill-opacity", currentStyle.fillOpacity);
              }
              if (currentStyle.strokePaint) {
                change(target, "stroke", currentStyle.strokePaint);
              }
              if (currentStyle.strokeOpacity) {
                change(target, "stroke-opacity", currentStyle.strokeOpacity);
              }
              if (currentStyle.strokeWidth) {
                change(target, "stroke-width", currentStyle.strokeWidth);
              }
              if (currentStyle.opacity) {
                change(target, "opacity", currentStyle.opacity);
              }
              if (currentStyle.strokeLinecap) {
                change(target, "stroke-linecap", currentStyle.strokeLinecap);
              }
              if (currentStyle.strokeLinejoin) {
                change(target, "stroke-linejoin", currentStyle.strokeLinejoin);
              }
              if (currentStyle.strokeDashArray) {
                change(target, "stroke-dasharray", currentStyle.strokeDashArray);
              } else {
                target.removeAttribute("stroke-dasharray");
              }
              addToHistory(new ChangeElementCommand(target, changes));
            } else {
              getStyle({ elems: [target] });
            }
          }
        }
      }
    };
  }
};
export {
  extEyedropper as default
};
//# sourceMappingURL=ext-eyedropper.js.map
