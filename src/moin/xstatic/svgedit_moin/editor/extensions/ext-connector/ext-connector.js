import { __vitePreload } from "../_virtual/preload-helper.js";
function __variableDynamicImportRuntime0__(path) {
  switch (path) {
    case "./locale/en.js":
      return __vitePreload(() => import("./locale/en.js"), true ? [] : void 0, import.meta.url);
    case "./locale/fr.js":
      return __vitePreload(() => import("./locale/fr.js"), true ? [] : void 0, import.meta.url);
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
const name = "connector";
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
const extConnector = {
  name,
  async init(S) {
    const svgEditor = this;
    const { svgCanvas } = svgEditor;
    const { getElement, $id, $click, addSVGElementsFromJson } = svgCanvas;
    const { svgroot, selectorManager } = S;
    const seNs = svgCanvas.getEditorNS();
    await loadExtensionTranslation(svgEditor);
    let startX;
    let startY;
    let curLine;
    let startElem;
    let endElem;
    let started = false;
    let connections = [];
    const originalGroupSelectedElements = svgCanvas.groupSelectedElements;
    svgCanvas.groupSelectedElements = function(...args) {
      svgCanvas.removeFromSelection(document.querySelectorAll('[id^="conn_"]'));
      return originalGroupSelectedElements.apply(this, args);
    };
    const originalMoveSelectedElements = svgCanvas.moveSelectedElements;
    svgCanvas.moveSelectedElements = function(...args) {
      const cmd = originalMoveSelectedElements.apply(this, args);
      updateConnectors(svgCanvas.getSelectedElements());
      return cmd;
    };
    const getBBintersect = (x, y, bb, offset) => {
      if (offset) {
        bb = { ...bb };
        bb.width += offset;
        bb.height += offset;
        bb.x -= offset / 2;
        bb.y -= offset / 2;
      }
      const midX = bb.x + bb.width / 2;
      const midY = bb.y + bb.height / 2;
      const lenX = x - midX;
      const lenY = y - midY;
      const slope = Math.abs(lenY / lenX);
      let ratio;
      if (slope < bb.height / bb.width) {
        ratio = bb.width / 2 / Math.abs(lenX);
      } else {
        ratio = lenY ? bb.height / 2 / Math.abs(lenY) : 0;
      }
      return {
        x: midX + lenX * ratio,
        y: midY + lenY * ratio
      };
    };
    const getOffset = (side, line) => {
      const hasMarker = line.getAttribute("marker-" + side);
      const size = line.getAttribute("stroke-width") * 5;
      return hasMarker ? size : 0;
    };
    const showPanel = (on) => {
      let connRules = $id("connector_rules");
      if (!connRules) {
        connRules = document.createElement("style");
        connRules.setAttribute("id", "connector_rules");
        document.getElementsByTagName("head")[0].appendChild(connRules);
      }
      connRules.textContent = !on ? "" : "#tool_clone, #tool_topath, #tool_angle, #xy_panel { display: none !important; }";
      if ($id("connector_rules")) {
        $id("connector_rules").style.display = on ? "block" : "none";
      }
    };
    const setPoint = (elem, pos, x, y, setMid) => {
      const pts = elem.points;
      const pt = svgroot.createSVGPoint();
      pt.x = x;
      pt.y = y;
      if (pos === "end") {
        pos = pts.numberOfItems - 1;
      }
      pts.replaceItem(pt, pos);
      if (setMid) {
        const ptStart = pts.getItem(0);
        const ptEnd = pts.getItem(pts.numberOfItems - 1);
        setPoint(elem, 1, (ptEnd.x + ptStart.x) / 2, (ptEnd.y + ptStart.y) / 2);
      }
    };
    const updatePoints = (line, conn, bb, altBB, pre, altPre) => {
      const srcX = altBB.x + altBB.width / 2;
      const srcY = altBB.y + altBB.height / 2;
      const pt = getBBintersect(srcX, srcY, bb, getOffset(pre, line));
      setPoint(line, conn.is_start ? 0 : "end", pt.x, pt.y, true);
      const pt2 = getBBintersect(pt.x, pt.y, altBB, getOffset(altPre, line));
      setPoint(line, conn.is_start ? "end" : 0, pt2.x, pt2.y, true);
    };
    const updateLine = (diffX, diffY) => {
      const dataStorage = svgCanvas.getDataStorage();
      for (const conn of connections) {
        const {
          connector: line,
          is_start: isStart,
          start_x: startX2,
          start_y: startY2
        } = conn;
        const pre = isStart ? "start" : "end";
        const altPre = isStart ? "end" : "start";
        const bb = { ...dataStorage.get(line, `${pre}_bb`) };
        bb.x = startX2 + diffX;
        bb.y = startY2 + diffY;
        dataStorage.put(line, `${pre}_bb`, bb);
        const altBB = dataStorage.get(line, `${altPre}_bb`);
        updatePoints(line, conn, bb, altBB, pre, altPre);
      }
    };
    const findConnectors = (elems = []) => {
      const dataStorage = svgCanvas.getDataStorage();
      const connectors = document.querySelectorAll('[id^="conn_"]');
      connections = [];
      for (const connector of connectors) {
        let addThis = false;
        const parts = [];
        for (const [i, pos] of ["start", "end"].entries()) {
          let part = dataStorage.get(connector, `c_${pos}`);
          if (!part) {
            part = document.getElementById(
              connector.attributes["se:connector"].value.split(" ")[i]
            );
            dataStorage.put(connector, `c_${pos}`, part.id);
            dataStorage.put(
              connector,
              `${pos}_bb`,
              svgCanvas.getStrokedBBox([part])
            );
          } else {
            part = document.getElementById(part);
          }
          parts.push(part);
        }
        for (let i = 0; i < 2; i++) {
          const cElem = parts[i];
          const parents = svgCanvas.getParents(cElem?.parentNode);
          for (const el of parents) {
            if (elems.includes(el)) {
              addThis = true;
              break;
            }
          }
          if (!cElem || !cElem.parentNode) {
            connector.remove();
            continue;
          }
          if (elems.includes(cElem) || addThis) {
            const bb = svgCanvas.getStrokedBBox([cElem]);
            connections.push({
              elem: cElem,
              connector,
              is_start: i === 0,
              start_x: bb.x,
              start_y: bb.y
            });
          }
        }
      }
    };
    const updateConnectors = (elems) => {
      const dataStorage = svgCanvas.getDataStorage();
      findConnectors(elems);
      if (connections.length) {
        for (const conn of connections) {
          const {
            elem,
            connector: line,
            is_start: isStart,
            start_x: startX2,
            start_y: startY2
          } = conn;
          const pre = isStart ? "start" : "end";
          const bb = svgCanvas.getStrokedBBox([elem]);
          bb.x = startX2;
          bb.y = startY2;
          dataStorage.put(line, `${pre}_bb`, bb);
          const altPre = isStart ? "end" : "start";
          const bb2 = dataStorage.get(line, `${altPre}_bb`);
          const srcX = bb2?.x + bb2?.width / 2;
          const srcY = bb2?.y + bb2?.height / 2;
          const pt = getBBintersect(srcX, srcY, bb, getOffset(pre, line));
          setPoint(line, isStart ? 0 : "end", pt.x, pt.y, true);
          const pt2 = getBBintersect(
            pt.x,
            pt.y,
            dataStorage.get(line, `${altPre}_bb`),
            getOffset(altPre, line)
          );
          setPoint(line, isStart ? "end" : 0, pt2.x, pt2.y, true);
        }
      }
    };
    const reset = () => {
      const dataStorage = svgCanvas.getDataStorage();
      const svgContent = svgCanvas.getSvgContent();
      const elements = svgContent.querySelectorAll("*");
      elements.forEach((element) => {
        const conn = element.getAttributeNS(seNs, "connector");
        if (conn) {
          const connData = conn.split(" ");
          const sbb = svgCanvas.getStrokedBBox([getElement(connData[0])]);
          const ebb = svgCanvas.getStrokedBBox([getElement(connData[1])]);
          dataStorage.put(element, "c_start", connData[0]);
          dataStorage.put(element, "c_end", connData[1]);
          dataStorage.put(element, "start_bb", sbb);
          dataStorage.put(element, "end_bb", ebb);
          svgCanvas.getEditorNS(true);
        }
      });
    };
    reset();
    return {
      name: svgEditor.i18next.t(`${name}:name`),
      callback() {
        const buttonTemplate = document.createElement("template");
        const title = `${name}:buttons.0.title`;
        buttonTemplate.innerHTML = `
         <se-button id="tool_connect" title="${title}" src="conn.svg"></se-button>
         `;
        $id("tools_left").append(buttonTemplate.content.cloneNode(true));
        $click($id("tool_connect"), () => {
          if (this.leftPanel.updateLeftPanel("tool_connect")) {
            svgCanvas.setMode("connector");
          }
        });
      },
      mouseDown(opts) {
        const dataStorage = svgCanvas.getDataStorage();
        const svgContent = svgCanvas.getSvgContent();
        const { event: e, start_x: startX2, start_y: startY2 } = opts;
        const mode = svgCanvas.getMode();
        const {
          curConfig: { initStroke }
        } = svgEditor.configObj;
        if (mode === "connector") {
          if (started) return void 0;
          const mouseTarget = e.target;
          const parents = svgCanvas.getParents(mouseTarget.parentNode);
          if (parents.includes(svgContent)) {
            const fo = svgCanvas.getClosest(
              mouseTarget.parentNode,
              "foreignObject"
            );
            startElem = fo || mouseTarget;
            const bb = svgCanvas.getStrokedBBox([startElem]);
            const x = bb.x + bb.width / 2;
            const y = bb.y + bb.height / 2;
            started = true;
            curLine = addSVGElementsFromJson({
              element: "polyline",
              attr: {
                id: "conn_" + svgCanvas.getNextId(),
                points: `${x},${y} ${x},${y} ${startX2},${startY2}`,
                stroke: `#${initStroke.color}`,
                "stroke-width": !startElem.stroke_width || startElem.stroke_width === 0 ? initStroke.width : startElem.stroke_width,
                fill: "none",
                opacity: initStroke.opacity,
                style: "pointer-events:none"
              }
            });
            dataStorage.put(curLine, "start_bb", bb);
          }
          return {
            started: true
          };
        }
        if (mode === "select") {
          findConnectors(opts.selectedElements);
        }
        return void 0;
      },
      mouseMove(opts) {
        if (connections.length === 0) return;
        const dataStorage = svgCanvas.getDataStorage();
        const zoom = svgCanvas.getZoom();
        const x = opts.mouse_x / zoom;
        const y = opts.mouse_y / zoom;
        if (!startX || !startY) return;
        const diffX = x - startX;
        const diffY = y - startY;
        const mode = svgCanvas.getMode();
        if (mode === "connector" && started) {
          const pt = getBBintersect(
            x,
            y,
            dataStorage.get(curLine, "start_bb"),
            getOffset("start", curLine)
          );
          startX = pt.x;
          startY = pt.y;
          setPoint(curLine, 0, pt.x, pt.y, true);
          setPoint(curLine, "end", x, y, true);
        } else if (mode === "select") {
          for (const elem of svgCanvas.getSelectedElements()) {
            if (elem && dataStorage.has(elem, "c_start")) {
              svgCanvas.removeFromSelection([elem]);
              elem.transform.baseVal.clear();
            }
          }
          if (connections.length) {
            updateLine(diffX, diffY);
          }
        }
      },
      mouseUp(opts) {
        const dataStorage = svgCanvas.getDataStorage();
        const svgContent = svgCanvas.getSvgContent();
        const { event: e } = opts;
        let mouseTarget = e.target;
        if (svgCanvas.getMode() !== "connector") return void 0;
        const fo = svgCanvas.getClosest(mouseTarget.parentNode, "foreignObject");
        if (fo) mouseTarget = fo;
        const parents = svgCanvas.getParents(mouseTarget.parentNode);
        const isInSvgContent = parents.includes(svgContent);
        if (mouseTarget === startElem) {
          started = true;
          return {
            keep: true,
            element: null,
            started
          };
        }
        if (!isInSvgContent) {
          curLine?.remove();
          started = false;
          return {
            keep: false,
            element: null,
            started
          };
        }
        endElem = mouseTarget;
        const startId = startElem?.id || "";
        const endId = endElem?.id || "";
        const connStr = `${startId} ${endId}`;
        const altStr = `${endId} ${startId}`;
        const dupe = Array.from(
          document.querySelectorAll('[id^="conn_"]')
        ).filter(
          (conn) => conn.getAttributeNS(seNs, "connector") === connStr || conn.getAttributeNS(seNs, "connector") === altStr
        );
        if (dupe.length) {
          curLine.remove();
          return {
            keep: false,
            element: null,
            started: false
          };
        }
        const bb = svgCanvas.getStrokedBBox([endElem]);
        const pt = getBBintersect(
          startX,
          startY,
          bb,
          getOffset("start", curLine)
        );
        setPoint(curLine, "end", pt.x, pt.y, true);
        dataStorage.put(curLine, "c_start", startId);
        dataStorage.put(curLine, "c_end", endId);
        dataStorage.put(curLine, "end_bb", bb);
        curLine.setAttributeNS(seNs, "se:connector", connStr);
        curLine.setAttribute("opacity", 1);
        svgCanvas.addToSelection([curLine]);
        svgCanvas.moveToBottomSelectedElement();
        selectorManager.requestSelector(curLine).showGrips(false);
        started = false;
        return {
          keep: true,
          element: curLine,
          started
        };
      },
      selectedChanged(opts) {
        const dataStorage = svgCanvas.getDataStorage();
        const svgContent = svgCanvas.getSvgContent();
        if (!svgContent.querySelectorAll('[id^="conn_"]').length) return;
        if (svgCanvas.getMode() === "connector") {
          svgCanvas.setMode("select");
        }
        const { elems: selElems } = opts;
        for (const elem of selElems) {
          if (elem && dataStorage.has(elem, "c_start")) {
            selectorManager.requestSelector(elem).showGrips(false);
            showPanel(opts.selectedElement && !opts.multiselected);
          } else {
            showPanel(false);
          }
        }
        updateConnectors(svgCanvas.getSelectedElements());
      },
      elementChanged(opts) {
        const dataStorage = svgCanvas.getDataStorage();
        let [elem] = opts.elems;
        if (!elem) return;
        if (elem.tagName === "svg" && elem.id === "svgcontent") {
          reset();
        }
        const { markerStart, markerMid, markerEnd } = elem.attributes;
        if (markerStart || markerMid || markerEnd) {
          curLine = elem;
          dataStorage.put(elem, "start_off", Boolean(markerStart));
          dataStorage.put(elem, "end_off", Boolean(markerEnd));
          if (elem.tagName === "line" && markerMid) {
            const { x1, x2, y1, y2, id } = elem.attributes;
            const midPt = `${(Number(x1.value) + Number(x2.value)) / 2},${(Number(y1.value) + Number(y2.value)) / 2}`;
            const pline = addSVGElementsFromJson({
              element: "polyline",
              attr: {
                points: `${x1.value},${y1.value} ${midPt} ${x2.value},${y2.value}`,
                stroke: elem.getAttribute("stroke"),
                "stroke-width": elem.getAttribute("stroke-width"),
                "marker-mid": markerMid.value,
                fill: "none",
                opacity: elem.getAttribute("opacity") || 1
              }
            });
            elem.insertAdjacentElement("afterend", pline);
            elem.remove();
            svgCanvas.clearSelection();
            pline.id = id.value;
            svgCanvas.addToSelection([pline]);
            elem = pline;
          }
        }
        if (elem?.id.startsWith("conn_")) {
          const start = getElement(dataStorage.get(elem, "c_start"));
          updateConnectors([start]);
        } else {
          updateConnectors(svgCanvas.getSelectedElements());
        }
      },
      IDsUpdated(input) {
        const remove = [];
        input.elems.forEach(function(elem) {
          if ("se:connector" in elem.attr) {
            elem.attr["se:connector"] = elem.attr["se:connector"].split(" ").map(function(oldID) {
              return input.changes[oldID];
            }).join(" ");
            if (!/. ./.test(elem.attr["se:connector"])) {
              remove.push(elem.attr.id);
            }
          }
        });
        return { remove };
      },
      toolButtonStateUpdate(opts) {
        const button = document.getElementById("tool_connect");
        if (opts.nostroke && button.pressed === true) {
          svgEditor.clickSelect();
        }
        button.disabled = opts.nostroke;
      }
    };
  }
};
export {
  extConnector as default
};
//# sourceMappingURL=ext-connector.js.map
