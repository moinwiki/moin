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
const name = "grid";
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
const extGrid = {
  name,
  async init() {
    const svgEditor = this;
    await loadExtensionTranslation(svgEditor);
    const { svgCanvas } = svgEditor;
    const { $id, $click, NS } = svgCanvas;
    const svgdoc = $id("svgcanvas").ownerDocument;
    const { assignAttributes } = svgCanvas;
    const hcanvas = document.createElement("canvas");
    const canvBG = $id("canvasBackground");
    const units = svgCanvas.getTypeMap();
    const intervals = [0.01, 0.1, 1, 10, 100, 1e3];
    let showGrid = svgEditor.configObj.curConfig.showGrid || false;
    hcanvas.style.display = "none";
    svgEditor.$svgEditor.appendChild(hcanvas);
    const canvasGrid = svgdoc.createElementNS(NS.SVG, "svg");
    assignAttributes(canvasGrid, {
      id: "canvasGrid",
      width: "100%",
      height: "100%",
      x: 0,
      y: 0,
      overflow: "visible",
      display: "none"
    });
    canvBG.appendChild(canvasGrid);
    const gridDefs = svgdoc.createElementNS(NS.SVG, "defs");
    const gridPattern = svgdoc.createElementNS(NS.SVG, "pattern");
    assignAttributes(gridPattern, {
      id: "gridpattern",
      patternUnits: "userSpaceOnUse",
      x: 0,
      // -(value.strokeWidth / 2), // position for strokewidth
      y: 0,
      // -(value.strokeWidth / 2), // position for strokewidth
      width: 100,
      height: 100
    });
    const gridimg = svgdoc.createElementNS(NS.SVG, "image");
    assignAttributes(gridimg, {
      x: 0,
      y: 0,
      width: 100,
      height: 100
    });
    gridPattern.append(gridimg);
    gridDefs.append(gridPattern);
    $id("canvasGrid").appendChild(gridDefs);
    const gridBox = svgdoc.createElementNS(NS.SVG, "rect");
    assignAttributes(gridBox, {
      width: "100%",
      height: "100%",
      x: 0,
      y: 0,
      "stroke-width": 0,
      stroke: "none",
      fill: "url(#gridpattern)",
      style: "pointer-events: none; display:visible;"
    });
    $id("canvasGrid").appendChild(gridBox);
    const updateGrid = (zoom) => {
      const unit = units[svgEditor.configObj.curConfig.baseUnit];
      const uMulti = unit * zoom;
      const rawM = 100 / uMulti;
      let multi = 1;
      intervals.some((num) => {
        multi = num;
        return rawM <= num;
      });
      const bigInt = multi * uMulti;
      hcanvas.width = bigInt;
      hcanvas.height = bigInt;
      const ctx = hcanvas.getContext("2d");
      const curD = 0.5;
      const part = bigInt / 10;
      ctx.globalAlpha = 0.2;
      ctx.strokeStyle = svgEditor.configObj.curConfig.gridColor;
      for (let i = 1; i < 10; i++) {
        const subD = Math.round(part * i) + 0.5;
        const lineNum = 0;
        ctx.moveTo(subD, bigInt);
        ctx.lineTo(subD, lineNum);
        ctx.moveTo(bigInt, subD);
        ctx.lineTo(lineNum, subD);
      }
      ctx.stroke();
      ctx.beginPath();
      ctx.globalAlpha = 0.5;
      ctx.moveTo(curD, bigInt);
      ctx.lineTo(curD, 0);
      ctx.moveTo(bigInt, curD);
      ctx.lineTo(0, curD);
      ctx.stroke();
      const datauri = hcanvas.toDataURL("image/png");
      gridimg.setAttribute("width", bigInt);
      gridimg.setAttribute("height", bigInt);
      gridimg.parentNode.setAttribute("width", bigInt);
      gridimg.parentNode.setAttribute("height", bigInt);
      svgCanvas.setHref(gridimg, datauri);
    };
    const gridUpdate = () => {
      if (showGrid) {
        updateGrid(svgCanvas.getZoom());
      }
      $id("canvasGrid").style.display = showGrid ? "block" : "none";
      $id("view_grid").pressed = showGrid;
    };
    return {
      name: svgEditor.i18next.t(`${name}:name`),
      zoomChanged(zoom) {
        if (showGrid) {
          updateGrid(zoom);
        }
      },
      callback() {
        const buttonTemplate = document.createElement("template");
        const title = `${name}:buttons.0.title`;
        buttonTemplate.innerHTML = `
          <se-button id="view_grid" title="${title}" src="grid.svg"></se-button>
        `;
        $id("editor_panel").append(buttonTemplate.content.cloneNode(true));
        $click($id("view_grid"), () => {
          svgEditor.configObj.curConfig.showGrid = showGrid = !showGrid;
          gridUpdate();
        });
        if (showGrid) {
          gridUpdate();
        }
      }
    };
  }
};
export {
  extGrid as default
};
//# sourceMappingURL=ext-grid.js.map
