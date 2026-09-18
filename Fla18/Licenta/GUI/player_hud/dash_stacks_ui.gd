extends Control

const STACK_RADIUS : float = 4.5
const STACK_SPACING : float = 12.0
const FILL_COLOR : Color = Color(1, 0.85, 0.25, 1)
const EMPTY_COLOR : Color = Color(0.3, 0.25, 0.1, 0.6)
const OUTLINE_COLOR : Color = Color(0, 0, 0, 1)

func _process(_delta: float) -> void:
	queue_redraw()

func _draw() -> void:
	var center_y : float = size.y / 2.0
	for i in range(PlayerManager.dash_stacks_max):
		var center : Vector2 = Vector2(STACK_RADIUS + 1 + i * STACK_SPACING, center_y)
		draw_circle(center, STACK_RADIUS + 1, OUTLINE_COLOR)
		if i < PlayerManager.dash_stacks:
			draw_circle(center, STACK_RADIUS, FILL_COLOR)
		else:
			draw_circle(center, STACK_RADIUS, EMPTY_COLOR)
