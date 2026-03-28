let _loaded = false;
const _callbacks = [];
const _isTouch = window.ontouchstart !== void 0;
const dragmove = function(target, handler, parent, onStart, onEnd, onDrag) {
  if (!_loaded) {
    document.addEventListener(_isTouch ? "touchmove" : "mousemove", function(e) {
      let c = e;
      if (e.touches) {
        c = e.touches[0];
      }
      for (let i = 0; i < _callbacks.length; i++) {
        _callbacks[i](c.clientX, c.clientY);
      }
    });
  }
  _loaded = true;
  let isMoving = false;
  let hasStarted = false;
  let startX = 0;
  let startY = 0;
  let lastX = 0;
  let lastY = 0;
  handler.addEventListener(_isTouch ? "touchstart" : "mousedown", function(e) {
    e.stopPropagation();
    e.preventDefault();
    if (target.dataset.dragEnabled === "false") {
      return;
    }
    let c = e;
    if (e.touches) {
      c = e.touches[0];
    }
    isMoving = true;
    startX = target.offsetLeft - c.clientX;
    startY = target.offsetTop - c.clientY;
  });
  document.addEventListener(_isTouch ? "touchend" : "mouseup", function() {
    if (onEnd && hasStarted) {
      onEnd(target, parent, parseInt(target.style.left), parseInt(target.style.top));
    }
    isMoving = false;
    hasStarted = false;
  });
  document.addEventListener(_isTouch ? "touchmove" : "mousemove", function() {
    if (onDrag && hasStarted) {
      onDrag(target, parseInt(target.style.left), parseInt(target.style.top));
    }
  });
  _callbacks.push(function move(x, y) {
    if (!isMoving) {
      return;
    }
    if (!hasStarted) {
      hasStarted = true;
      if (onStart) {
        onStart(target, lastX, lastY);
      }
    }
    lastX = x + startX;
    lastY = y + startY;
    if (target.dataset.dragBoundary === "true") {
      if (lastX < 1 || lastX >= window.innerWidth - target.offsetWidth) {
        return;
      }
      if (lastY < 1 || lastY >= window.innerHeight - target.offsetHeight) {
        return;
      }
    }
    target.style.left = lastX + "px";
    target.style.top = lastY + "px";
  });
};
export {
  dragmove as default,
  dragmove
};
//# sourceMappingURL=dragmove.js.map
