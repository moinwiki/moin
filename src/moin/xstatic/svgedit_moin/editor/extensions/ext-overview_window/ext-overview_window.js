import dragmove from "./dragmove/dragmove.js";
//#region src/editor/extensions/ext-overview_window/ext-overview_window.js
/**
* @file ext-overview_window.js
*
* @license MIT
*
* @copyright 2013 James Sacksteder
*
*/
var ext_overview_window_default = {
	name: "overview_window",
	init({ _$ }) {
		const svgEditor = this;
		const { svgCanvas, svgeditPolicy } = svgEditor;
		const { $id, $click } = svgCanvas;
		const overviewWindowGlobals = {};
		const propsWindowHtml = svgeditPolicy.createHTML("<div id=\"overview_window_content_pane\"><div id=\"overview_window_content\"><div><svg id=\"overviewMiniView\" width=\"132\" height=\"100\" x=\"0\" y=\"0\" viewBox=\"0 0 4800 3600\" xmlns=\"http://www.w3.org/2000/svg\" xmlns:xlink=\"http://www.w3.org/1999/xlink\"><use x=\"0\" y=\"0\" href=\"#svgroot\"> </use></svg><div id=\"overview_window_view_box\"></div></div></div></div>");
		$id("sidepanel_content").insertAdjacentHTML("beforeend", propsWindowHtml);
		const updateViewBox = () => {
			const { workarea } = svgEditor;
			const portHeight = parseFloat(getComputedStyle(workarea, null).height.replace("px", ""));
			const portWidth = parseFloat(getComputedStyle(workarea, null).width.replace("px", ""));
			const portX = workarea.scrollLeft;
			const portY = workarea.scrollTop;
			const windowWidth = parseFloat(getComputedStyle($id("svgcanvas"), null).width.replace("px", ""));
			const windowHeight = parseFloat(getComputedStyle($id("svgcanvas"), null).height.replace("px", ""));
			const overviewWidth = parseFloat(getComputedStyle($id("overviewMiniView"), null).width.replace("px", ""));
			const overviewHeight = parseFloat(getComputedStyle($id("overviewMiniView"), null).height.replace("px", ""));
			const viewBoxX = portX / windowWidth * overviewWidth;
			const viewBoxY = portY / windowHeight * overviewHeight;
			const viewBoxWidth = portWidth / windowWidth * overviewWidth;
			const viewBoxHeight = portHeight / windowHeight * overviewHeight;
			$id("overview_window_view_box").style.minWidth = viewBoxWidth + "px";
			$id("overview_window_view_box").style.minHeight = viewBoxHeight + "px";
			$id("overview_window_view_box").style.top = viewBoxY + "px";
			$id("overview_window_view_box").style.left = viewBoxX + "px";
		};
		$id("workarea").addEventListener("scroll", () => {
			if (!overviewWindowGlobals.viewBoxDragging) updateViewBox();
		});
		$id("workarea").addEventListener("resize", updateViewBox);
		updateViewBox();
		const updateViewDimensions = function() {
			const viewWidth = parseFloat(getComputedStyle($id("svgroot"), null).width.replace("px", ""));
			const viewHeight = parseFloat(getComputedStyle($id("svgroot"), null).height.replace("px", ""));
			const svgWidthOld = parseFloat(getComputedStyle($id("overviewMiniView"), null).width.replace("px", ""));
			const svgHeightNew = viewHeight / viewWidth * svgWidthOld;
			$id("overviewMiniView").setAttribute("viewBox", "640 480 " + viewWidth + " " + viewHeight);
			$id("overviewMiniView").setAttribute("height", svgHeightNew);
			updateViewBox();
		};
		updateViewDimensions();
		overviewWindowGlobals.viewBoxDragging = false;
		const updateViewPortFromViewBox = function() {
			const windowWidth = parseFloat(getComputedStyle($id("svgcanvas"), null).width.replace("px", ""));
			const windowHeight = parseFloat(getComputedStyle($id("svgcanvas"), null).height.replace("px", ""));
			const overviewWidth = parseFloat(getComputedStyle($id("overviewMiniView"), null).width.replace("px", ""));
			const overviewHeight = parseFloat(getComputedStyle($id("overviewMiniView"), null).height.replace("px", ""));
			const viewBoxX = parseFloat(getComputedStyle($id("overview_window_view_box"), null).getPropertyValue("left").replace("px", ""));
			const viewBoxY = parseFloat(getComputedStyle($id("overview_window_view_box"), null).getPropertyValue("top").replace("px", ""));
			const portX = viewBoxX / overviewWidth * windowWidth;
			const portY = viewBoxY / overviewHeight * windowHeight;
			$id("workarea").scrollLeft = portX;
			$id("workarea").scrollTop = portY;
		};
		const onStart = () => {
			overviewWindowGlobals.viewBoxDragging = true;
			updateViewPortFromViewBox();
		};
		const onEnd = (el, parent, _x, _y) => {
			if (el.offsetLeft + el.offsetWidth > parseFloat(getComputedStyle(parent, null).width.replace("px", ""))) el.style.left = parseFloat(getComputedStyle(parent, null).width.replace("px", "")) - el.offsetWidth + "px";
			else if (el.offsetLeft < 0) el.style.left = "0px";
			if (el.offsetTop + el.offsetHeight > parseFloat(getComputedStyle(parent, null).height.replace("px", ""))) el.style.top = parseFloat(getComputedStyle(parent, null).height.replace("px", "")) - el.offsetHeight + "px";
			else if (el.offsetTop < 0) el.style.top = "0px";
			overviewWindowGlobals.viewBoxDragging = false;
			updateViewPortFromViewBox();
		};
		const onDrag = function() {
			updateViewPortFromViewBox();
		};
		const dragElem = document.querySelector("#overview_window_view_box");
		dragmove(dragElem, dragElem, document.querySelector("#overviewMiniView"), onStart, onEnd, onDrag);
		$click($id("overviewMiniView"), (evt) => {
			const mouseX = evt.offsetX || evt.originalEvent.layerX;
			const mouseY = evt.offsetY || evt.originalEvent.layerY;
			const overviewWidth = parseFloat(getComputedStyle($id("overviewMiniView"), null).width.replace("px", ""));
			const overviewHeight = parseFloat(getComputedStyle($id("overviewMiniView"), null).height.replace("px", ""));
			const viewBoxWidth = parseFloat(getComputedStyle($id("overview_window_view_box"), null).getPropertyValue("min-width").replace("px", ""));
			const viewBoxHeight = parseFloat(getComputedStyle($id("overview_window_view_box"), null).getPropertyValue("min-height").replace("px", ""));
			let viewBoxX = mouseX - .5 * viewBoxWidth;
			let viewBoxY = mouseY - .5 * viewBoxHeight;
			if (viewBoxX < 0) viewBoxX = 0;
			if (viewBoxY < 0) viewBoxY = 0;
			if (viewBoxX + viewBoxWidth > overviewWidth) viewBoxX = overviewWidth - viewBoxWidth;
			if (viewBoxY + viewBoxHeight > overviewHeight) viewBoxY = overviewHeight - viewBoxHeight;
			$id("overview_window_view_box").style.top = viewBoxY + "px";
			$id("overview_window_view_box").style.left = viewBoxX + "px";
			updateViewPortFromViewBox();
		});
		return {
			name: "overview window",
			canvasUpdated: updateViewDimensions,
			workareaResized: updateViewBox
		};
	}
};
//#endregion
export { ext_overview_window_default as default };

//# sourceMappingURL=ext-overview_window.js.map