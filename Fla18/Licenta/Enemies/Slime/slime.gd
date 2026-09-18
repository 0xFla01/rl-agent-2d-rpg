class_name Slime extends Enemy

func set_direction(_new_direction: Vector2) -> bool:
	direction = _new_direction
	if direction == Vector2.ZERO:
		return false

	var new_dir: Vector2
	if abs(_new_direction.x) > abs(_new_direction.y):
		new_dir = Vector2.RIGHT if _new_direction.x > 0 else Vector2.LEFT
	else:
		new_dir = Vector2.DOWN if _new_direction.y > 0 else Vector2.UP

	if new_dir == cardinal_direction:
		return false

	cardinal_direction = new_dir
	direction_changed.emit(new_dir)
	sprite.scale.x = -1 if cardinal_direction == Vector2.LEFT else 1
	return true
