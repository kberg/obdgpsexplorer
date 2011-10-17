var Interaction = {
};

Interaction.down = function(event, g, context) {
  context.initializeMouseDown(event, g, context);
  if (event.altKey || event.shiftKey) {
    Dygraph.startZoom(event, g, context);
  } else {
    Dygraph.startPan(event, g, context);
  }
}

Interaction.move = function(event, g, context) {
  if (context.isPanning) {
    Dygraph.movePan(event, g, context);
  } else if (context.isZooming) {
    Dygraph.moveZoom(event, g, context);
  }
}

Interaction.up = function(event, g, context) {
  if (context.isPanning) {
    Dygraph.endPan(event, g, context);
  } else if (context.isZooming) {
    Dygraph.endZoom(event, g, context);
  }
}

// Take the offset of a mouse event on the dygraph canvas and
// convert it to a pair of percentages from the bottom left. 
// (Not top left, bottom is where the lower value is.)
Interaction.offsetToPercentage = function(g, offsetX, offsetY) {
  // This is calculating the pixel offset of the leftmost date.
  var xOffset = g.toDomCoords(g.xAxisRange()[0], null)[0];
  var yar0 = g.yAxisRange(0);

  // This is calculating the pixel of the higest value. (Top pixel)
  var yOffset = g.toDomCoords(null, yar0[1])[1];

  // x y w and h are relative to the corner of the drawing area,
  // so that the upper corner of the drawing area is (0, 0).
  var x = offsetX - xOffset;
  var y = offsetY - yOffset;

  // This is computing the rightmost pixel, effectively defining the
  // width.
  var w = g.toDomCoords(g.xAxisRange()[1], null)[0] - xOffset;

  // This is computing the lowest pixel, effectively defining the height.
  var h = g.toDomCoords(null, yar0[0])[1] - yOffset;

  // Percentage from the left.
  var xPct = w == 0 ? 0 : (x / w);
  // Percentage from the top.
  var yPct = h == 0 ? 0 : (y / h);

  // The (1-) part below changes it from "% distance down from the top"
  // to "% distance up from the bottom".
  return [xPct, (1-yPct)];
}

Interaction.dblClick = function(event, g, context) {
  // Reducing by 20% makes it 80% the original size, which means
  // to restore to original size it must grow by 25%
  var percentages = Interaction.offsetToPercentage(g, event.offsetX, event.offsetY);
  var xPct = percentages[0];
  var yPct = percentages[1];

  if (event.ctrlKey) {
    zoom(g, -.25, xPct, yPct);
  } else {
    zoom(g, +.2, xPct, yPct);
  }
}

// Adjusts [x, y] toward each other by zoomInPercentage%
// Split it so the left/bottom axis gets xBias/yBias of that change and
// tight/top gets (1-xBias)/(1-yBias) of that change.
//
// If a bias is missing it splits it down the middle.
Interaction.zoom = function(g, zoomInPercentage, xBias, yBias) {
  xBias = xBias || 0.5;
  yBias = yBias || 0.5;
  function adjustAxis(axis, zoomInPercentage, bias) {
    var delta = axis[1] - axis[0];
    var increment = delta * zoomInPercentage;
    var foo = [increment * bias, increment * (1-bias)];
    return [ axis[0] + foo[0], axis[1] - foo[1] ];
  }
  var yAxes = g.yAxisRanges();
  var newYAxes = [];
  for (var i = 0; i < yAxes.length; i++) {
    newYAxes[i] = adjustAxis(yAxes[i], zoomInPercentage, yBias);
  }

  g.updateOptions({
    dateWindow: adjustAxis(g.xAxisRange(), zoomInPercentage, xBias),
    valueRange: newYAxes[0]
    });
}

Interaction.restorePositioning = function(g) {
  g.updateOptions({
    dateWindow: null,
    valueRange: null
  });
}
