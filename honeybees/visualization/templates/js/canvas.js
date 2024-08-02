'use strict';

class ContinuousVisualization {
	constructor(width, height, map_width, margin_left, ctx) {
		this.width = width;
		this.height = height;
		this.map_height = height;
		this.map_width = map_width;
		this.margin_left = margin_left;
		var ctx = ctx;
		this.draw = function (objects) {
			for (var i in objects) {
				var p = objects[i];
				if (p.type == 'background options') {
					this.setBackgroundOptions(p);
				} else if (p.type == 'colorbar') {
					this.drawColorbar(p);
				} else if (p.type == 'legend') {
					this.drawLegend(p);
				} else if (p.type == 'shape') {
					if (p.shape == "circle")
						this.drawCircle(p);
					else if (p.shape == "polygon")
						this.drawPolygon(p);
					else if (p.shape == 'line')
						this.drawLine(p);
					else
						alert('shape type ' + p.shape + ' not recognized');
				} else {
					alert('type ' + p.type + ' not recognized')
				}
			};
		};
		this.map_coordinate = function(c, length, axis) {
			if (axis == 'x') {
				return c * length + this.margin_left;
			} else {
				return (1 - c) * length;
			}
		}
		this.map_coordinates = function (coords, length, axis) {
			return coords.map(function (c) {
				return this.map_coordinate(c, length, axis);
			}, this);
		};
		this.drawLine = function (p) {
			ctx.beginPath();
			for (var l = 0; l < p.lines.length; l++) {
				var cxs = this.map_coordinates(p.lines[l].xs, this.map_width, 'x');
				var cys = this.map_coordinates(p.lines[l].ys, this.map_height, 'y');
				ctx.moveTo(cxs[0], cys[0]);
				for (var i = 1; i < cxs.length; i++) {
					ctx.lineTo(cxs[i], cys[i]);
				}
			}
			ctx.strokeStyle = p.color;
			ctx.stroke();
		};
		this.drawPolygon = function (p) {
			ctx.beginPath();
			for (var r = 0; r < p.rings.length; r++) {
				var cxs = this.map_coordinates(p.rings[r].xs, this.map_width, 'x');
				var cys = this.map_coordinates(p.rings[r].ys, this.map_height, 'y');
				ctx.moveTo(cxs[0], cys[0]);
				for (var i = 1; i < cxs.length; i++) {
					ctx.lineTo(cxs[i], cys[i]);
				};
				ctx.closePath();
			}
			if (p.edge) {
				ctx.strokeStyle = p.color;
				ctx.stroke();
			}
			if (p.filled) {
				ctx.fillStyle = p.color;
				ctx.fill();
			}
		};
		this.drawCircle = function (p) {
			var cx = this.map_coordinate(p.x, this.map_width, 'x');
			var cy = this.map_coordinate(p.y, this.map_height, 'y');
			var r = p.radius;
			ctx.beginPath();
			ctx.arc(cx, cy, p.r, 0, Math.PI * 2, false);
			ctx.closePath();
			ctx.strokeStyle = p.color;
			ctx.stroke();
			if (p.filled) {
				ctx.fillStyle = p.color;
				ctx.fill();
			}
		};
		this.hex = function(x) {
			x = x.toString(16);
			return (x.length == 1) ? '0' + x : x;			
		}
		this.getColorbarColor = function(color1, color2, ratio) {
			var r = Math.ceil(parseInt(color1.substring(1,3), 16) * ratio + parseInt(color2.substring(1,3), 16) * (1-ratio));
			var g = Math.ceil(parseInt(color1.substring(3,5), 16) * ratio + parseInt(color2.substring(3,5), 16) * (1-ratio));
			var b = Math.ceil(parseInt(color1.substring(5,7), 16) * ratio + parseInt(color2.substring(5,7), 16) * (1-ratio));
			var a = Math.ceil(parseInt(color1.substring(7,9), 16) * ratio + parseInt(color2.substring(7,9), 16) * (1-ratio));
			var color = '#' + this.hex(r) + this.hex(g) + this.hex(b) + this.hex(a);
			return color
		}
		this.drawColorbar = function(colorbar) {
			if (colorbar.location == 'right') {

			} else {
				alert('Colorbar left not yet implemented')
			}
			var ColorbarYFloat = 0;
			for (var i = 0; i <= 255; i++) {
				var color = this.getColorbarColor(colorbar.color_min, colorbar.color_max, i / 256);
				ctx.fillStyle = color;
				
				var nextColorbarYFloat = ColorbarYFloat + this.map_height / 256;
				var ColorbarYInt = Math.floor(ColorbarYFloat);
				
				ctx.beginPath();
				ctx.fillRect(margin_left + this.map_width + 20, ColorbarYInt, 10, Math.floor(nextColorbarYFloat) - ColorbarYInt);
				
				ColorbarYFloat = nextColorbarYFloat;
			}
			ctx.textAlign = "end";
			ctx.font = 'italic 12pt Calibri';
			ctx.fillStyle = "black";
			ctx.fillText(colorbar.min, margin_left + this.map_width + 14, this.map_height - 4);
			ctx.fillText(colorbar.max, margin_left + this.map_width + 14, 12);
			ctx.font = 'italic 10pt Calibri';
			ctx.fillText(colorbar.unit, margin_left + this.map_width + 14, 28);
		};
		this.drawLegend = function(legend) {
			ctx.textBaseline = "middle";
			if (legend.location == 'left') {
				var x = 10;
				var textOffset = 10;
				ctx.textAlign = "start";
			} else {
				var x = this.width - 10;
				var textOffset = -10;
				ctx.textAlign = "end";
			};
			var y = 20;
			for (const [label, color] of Object.entries(legend.labels)) {
				ctx.beginPath();
				ctx.arc(x, y, 4, 0, Math.PI * 2, false);
				ctx.closePath();
				ctx.strokeStyle = color;
				ctx.stroke();
				ctx.fillStyle = color;
				ctx.fill();
				ctx.font = 'italic 12pt Calibri';
				ctx.fillStyle = "black";
				ctx.fillText(label, x + textOffset, y);
				y += 15;
			}
		}
		this.drawBackgroundFirst = function(objects) {
			var background = objects[0];
			var img = new Image();
			img.src = background.img;
			img.onload = function() {
				ctx.imageSmoothingEnabled = false; // Disable interpolation
				ctx.drawImage(img, 0, 0, background.xsize, background.ysize, margin_left, 0, this.map_width, this.map_height);
				this.draw(objects.slice(1))
			}.bind(this);
		};
		this.setBackgroundOptions = function(p) {
			$("#backgroundselector").empty();
			var backgroundselectorHtml;
			// var optionGroup;
			// var optionName;
			// var prevOptionGroup;
			var options = p.options;
			options.sort();
			for (var i = 0; i < options.length; i++) {
				var option = options[i];
				backgroundselectorHtml += '<option value="' + option
				if (p.currentselection == option) {
					backgroundselectorHtml += '" selected>'
				} else {
					backgroundselectorHtml += '">'
				};
				backgroundselectorHtml += option + '</option>';
			} 
			// for (var i = 0; i < options.length; i++) {
			// 	var option = options[i];
			// 	var splittedOption = option.split('.');
			// 	if (splittedOption.length == 1) {
			// 		optionGroup = "";
			// 		optionName = splittedOption[0];
			// 	} else if (splittedOption.length == 2) {
			// 		optionGroup = splittedOption[0];
			// 		optionName = splittedOption[1];
			// 	} else {
			// 		alert('Variable length too long:' + option);
			// 	}
			// 	if (i == 0) {
			// 		backgroundselectorHtml += '<optgroup label="' + optionGroup + '">';
			// 	} else if (prevOptionGroup != optionGroup) {
			// 		backgroundselectorHtml += '</optgroup><optgroup label="' + optionGroup + '">';
			// 	}
			// 	backgroundselectorHtml += '<option value="' + option
			// 	if (p.currentselection == option) {
			// 		backgroundselectorHtml += '" selected>'
			// 	} else {
			// 		backgroundselectorHtml += '">'
			// 	};
			// 	backgroundselectorHtml += optionName + '</option>';
			// 	prevOptionGroup = optionGroup;
			// };
			// if (options.length > 0) {
			// 	backgroundselectorHtml += "</optgroup>";
			// }
			$("#backgroundselector").append(backgroundselectorHtml);
		}
		this.resetCanvas = function () {
			ctx.clearRect(0, 0, width, height);
			ctx.beginPath();
		};
	}
}


class Simple_Continuous_Module {
	constructor(canvas_width, canvas_height) {
		var margin_left = 0;
		// var canvas_width = margin_left + map_width + 30; // to include colorbar
		var map_width = canvas_width - 30;
		var backgroundSelector = '<select id="backgroundselector" size=1></select>';
		$("#elements").append(backgroundSelector);
		$('#backgroundselector').change(function(){
			controller.change_map_variable($(this).val());
		});
		var canvas_tag = "<canvas id='canvas' width='" + canvas_width + "' height='" + canvas_height + "' ";
		canvas_tag += "style='border:1px dotted'></canvas>";
		// Append it to body:
		var canvas = $(canvas_tag)[0];
		$("#elements").append(canvas);
		// Create the ctx and the drawing controller:
		var ctx = canvas.getContext("2d");
		ctx.imageSmoothingEnabled = false;
		var canvasDraw = new ContinuousVisualization(canvas_width, canvas_height, map_width, margin_left, ctx);
		this.render = function (data) {
			canvasDraw.resetCanvas();
			if (data.hasOwnProperty('size')) {
				this.resize(data['size'][0], data['size'][1]);
			};
			if (data.hasOwnProperty('draw')) {
				var draw = data.draw;
				if (draw.length > 0 && draw[0].type == 'background') {
					canvasDraw.drawBackgroundFirst(draw);
				} else {
					canvasDraw.draw(draw);
				}
			};
			if (data.hasOwnProperty('background')) {
				
			};
		};
		this.resize = function (width, height) {
			document.getElementById('canvas').height = height;
			document.getElementById('canvas').width = width;
			canvasDraw.width = width;
			canvasDraw.height = width;
			canvasDraw.map_height = height;
			canvasDraw.map_width = width - 30;
		}
		this.reset = function () {
			canvasDraw.resetCanvas();
		};
	}
}
