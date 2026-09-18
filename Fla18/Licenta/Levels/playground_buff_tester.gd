extends Node2D

const CHEST = preload("res://Interactables/TreasureChest/treasure-chest.tscn")

func _ready() -> void:
	await get_tree().process_frame
	var cols := 8
	var spacing := Vector2(90, 90)

	for i in BuffPool._pool.size():
		var buff : Dictionary = BuffPool._pool[i]
		var col := i % cols
		var row := i / cols
		var chest = CHEST.instantiate()
		chest.position = Vector2(col * spacing.x, row * spacing.y)
		add_child(chest)
		await get_tree().process_frame
		_add_label(chest, buff.name + "\n" + buff.desc)
		chest.chest_opened.connect(_apply_buff.bind(buff))


func _add_label(chest: Node, text: String) -> void:
	var label := Label.new()
	label.text = text
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.vertical_alignment = VERTICAL_ALIGNMENT_BOTTOM
	label.position = Vector2(-70, -110)
	label.size = Vector2(140, 96)
	label.autowrap_mode = TextServer.AUTOWRAP_WORD
	label.add_theme_font_size_override("font_size", 11)
	label.add_theme_color_override("font_color", Color(1, 0.92, 0.5, 1))
	label.add_theme_color_override("font_outline_color", Color.BLACK)
	label.add_theme_constant_override("outline_size", 2)
	chest.add_child(label)


func _apply_buff(buff: Dictionary) -> void:
	buff.apply.call()
	if buff.id not in PlayerManager.active_buff_ids:
		PlayerManager.active_buff_ids.append(buff.id)
	if PlayerManager.player:
		PlayerManager.player.update_damage_values()
