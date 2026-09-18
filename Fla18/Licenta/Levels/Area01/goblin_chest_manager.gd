extends Node

signal room_cleared

var goblins_remaining : int = 0
var chests : Array = []
var exit_barriers : Array[StaticBody2D] = []
var blocked_transitions : Array[Area2D] = []

func _ready() -> void:
	add_to_group("kill_chest_managers")
	add_to_group("item_chest_managers")
	var parent = get_parent()

	var chest_names = ["Treasure-chest", "Treasure-chest2", "Treasure-chest3", "Treasure-chest4"]
	for cname in chest_names:
		if parent.has_node(cname):
			var chest = parent.get_node(cname)
			_set_chest_active(chest, false)
			chests.append(chest)

	var goblin_names = ["Goblin", "Goblin2", "Goblin3", "Goblin4"]
	for gname in goblin_names:
		if parent.has_node(gname):
			var goblin = parent.get_node(gname)
			if goblin.has_signal("enemy_destroyed"):
				goblin.enemy_destroyed.connect(_on_goblin_destroyed)
				goblins_remaining += 1

	_block_exits()

func _set_chest_active(chest, active: bool) -> void:
	chest.visible = active
	for child in chest.get_children():
		if child is StaticBody2D:
			child.set_deferred("collision_layer", 16 if active else 0)
		elif child is Area2D:
			child.set_deferred("monitoring", active)

func _block_exits() -> void:
	var parent = get_parent()
	var transition_names = ["LevelTransition", "LevelTransition2"]

	# Dezactiveaza imediat ca sa nu se poata iesi in fereastra de 3 frames
	for tname in transition_names:
		if parent.has_node(tname):
			var t = parent.get_node(tname)
			if t is Area2D:
				t.monitoring = false
				blocked_transitions.append(t)

	await get_tree().physics_frame
	await get_tree().physics_frame
	await get_tree().physics_frame

	_create_barrier(Vector2(240, -8), Vector2(96, 16))
	_create_barrier(Vector2(232, 319), Vector2(144, 8))

func _create_barrier(pos: Vector2, sz: Vector2) -> void:
	var barrier = StaticBody2D.new()
	barrier.collision_layer = 16
	barrier.collision_mask = 0
	barrier.position = pos

	var shape = CollisionShape2D.new()
	var rect = RectangleShape2D.new()
	rect.size = sz
	shape.shape = rect
	barrier.add_child(shape)

	get_parent().add_child(barrier)
	exit_barriers.append(barrier)

func _unblock_exits() -> void:
	# Deblocam doar iesirea nord (LevelTransition2 → Area01/03)
	if blocked_transitions.size() > 1 and is_instance_valid(blocked_transitions[1]):
		blocked_transitions[1].set_deferred("monitoring", true)
	# Stergem doar bariera nord; bariera sud ramane ca sa previna iesirea din harta
	if exit_barriers.size() > 0 and is_instance_valid(exit_barriers[0]):
		exit_barriers[0].queue_free()

func _on_goblin_destroyed(_hurt_box) -> void:
	goblins_remaining -= 1
	if goblins_remaining <= 0:
		_reveal_chests()

func _play_chest_fanfare() -> void:
	var rate   := 22050
	var ndur   := 0.28
	var notes  : Array[float] = [523.0, 659.0, 784.0, 1047.0]
	var n      := int(rate * ndur * notes.size())
	var samples := PackedFloat32Array()
	samples.resize(n)
	for i in n:
		var t   := float(i) / rate
		var ni  := mini(int(t / ndur), notes.size() - 1)
		var nt  := fmod(t, ndur) / ndur
		var env := exp(-nt * 5.5)
		var f   := notes[ni]
		var s   := sin(TAU * f       * t) * 0.50 * env
		s += sin(TAU * f * 2.0 * t) * 0.18 * env
		s += sin(TAU * f * 3.0 * t) * 0.06 * env
		samples[i] = clamp(s, -1.0, 1.0)
	var stream := AudioStreamWAV.new()
	stream.mix_rate = rate
	stream.stereo   = false
	stream.format   = 1
	var data := PackedByteArray()
	data.resize(n * 2)
	for i in n:
		var v := int(clamp(samples[i] * 32767.0, -32768.0, 32767.0))
		data[i * 2]     = v & 0xFF
		data[i * 2 + 1] = (v >> 8) & 0xFF
	stream.data = data
	var player := AudioStreamPlayer.new()
	add_child(player)
	player.stream = stream
	player.play()
	player.finished.connect(player.queue_free)

func _reveal_chests() -> void:
	room_cleared.emit()
	_play_chest_fanfare()
	for chest in chests:
		_set_chest_active(chest, true)
		_add_item_label(chest)
		if chest.has_signal("chest_opened"):
			chest.chest_opened.connect(_on_chest_opened.bind(chest))


# Pentru AI: returneaza pozitiile + ce abilitate are fiecare chest
# ability_id: 0=arrow, 1=boomerang, 2=grapple, -1=unknown
func get_item_chest_data() -> Array:
	if goblins_remaining > 0:
		return []  # chest-urile nu sunt inca revealed
	var result := []
	for chest in chests:
		if not is_instance_valid(chest) or not chest.visible:
			continue
		var ability_id := -1
		if chest.item_data:
			var item_name : String = chest.item_data.resource_path.get_file().to_lower()
			if "arrow" in item_name:
				ability_id = 0
			elif "boomerang" in item_name:
				ability_id = 1
			elif "grapple" in item_name:
				ability_id = 2
		result.append({
			"ability_id": ability_id,
			"x": chest.global_position.x,
			"y": chest.global_position.y,
		})
	return result

func _add_item_label(chest) -> void:
	if not chest.item_data:
		return

	var panel_width = 80
	var panel_height = 16

	var label = Label.new()
	label.name = "ItemNameLabel"
	label.text = chest.item_data.name
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	label.position = Vector2(-panel_width / 2.0, -42)
	label.size = Vector2(panel_width, panel_height)
	label.add_theme_font_size_override("font_size", 12)
	label.add_theme_color_override("font_color", Color(1, 0.95, 0.6, 1))
	label.add_theme_color_override("font_outline_color", Color.BLACK)
	label.add_theme_constant_override("outline_size", 4)
	chest.add_child(label)

signal item_picked

func _on_chest_opened(opened_chest) -> void:
	item_picked.emit()
	_unblock_exits()
	for chest in chests:
		if chest != opened_chest and is_instance_valid(chest):
			chest.queue_free()
