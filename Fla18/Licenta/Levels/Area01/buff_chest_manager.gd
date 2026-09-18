extends Node

const TREASURE_CHEST = preload("res://Interactables/TreasureChest/treasure-chest.tscn")

@export var chest_positions : Array[Vector2] = [
	Vector2(170, -550),
	Vector2(290, -550),
	Vector2(410, -550),
]

@export var trigger_position : Vector2 = Vector2(297, -490)
@export var trigger_size : Vector2 = Vector2(600, 32)

@export var north_exit_pos : Vector2 = Vector2(540, -340)
@export var north_exit_size : Vector2 = Vector2(32, 96)
@export var south_exit_pos : Vector2 = Vector2(272, 312)
@export var south_exit_size : Vector2 = Vector2(96, 16)

var chests : Array = []
var exit_barriers : Array[StaticBody2D] = []
var blocked_transitions : Array[Area2D] = []
var triggered : bool = false
var any_chest_opened : bool = false
var _selected_buffs : Array[Dictionary] = []

func _ready() -> void:
	add_to_group("buff_chest_managers")
	await get_tree().process_frame
	_block_exits()
	_make_traps_player_only()


func get_chest_data() -> Array:
	if not triggered or any_chest_opened or chests.is_empty():
		return []
	var result := []
	for i in chests.size():
		if not is_instance_valid(chests[i]):
			continue
		result.append({
			"buff_id": _selected_buffs[i].id if i < _selected_buffs.size() else "",
			"x": chests[i].global_position.x,
			"y": chests[i].global_position.y,
		})
	return result


func _make_traps_player_only() -> void:
	for child in get_parent().get_children():
		if child is SpikeTrap:
			child.force_static()
		elif child is SawTrap:
			var hb := child.get_node_or_null("HurtBox") as Area2D
			if hb:
				hb.collision_mask = 2

func _process(_delta: float) -> void:
	if triggered:
		return
	if not PlayerManager.player or not is_instance_valid(PlayerManager.player):
		return
	# Trigger when the player walks north past the trigger line (y decreases going north)
	if PlayerManager.player.global_position.y <= trigger_position.y:
		triggered = true
		_kill_all_enemies_in_scene()
		_spawn_chests()


func _kill_all_enemies_in_scene() -> void:
	var fake_hurt := HurtBox.new()
	fake_hurt.damage = 9999
	add_child(fake_hurt)
	for enemy in get_tree().get_nodes_in_group("enemies"):
		if is_instance_valid(enemy) and "hit_box" in enemy and is_instance_valid(enemy.hit_box):
			fake_hurt.global_position = enemy.global_position
			enemy.hit_box.take_damage(fake_hurt)
	fake_hurt.queue_free()

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

func _spawn_chests() -> void:
	_play_chest_fanfare()
	_selected_buffs = BuffPool.get_random_buffs(3)

	for i in range(_selected_buffs.size()):
		var chest = TREASURE_CHEST.instantiate()
		chest.name = "BuffChest" + str(i + 1)
		chest.position = chest_positions[i]
		get_parent().add_child(chest)
		chests.append(chest)

		await get_tree().process_frame
		_add_buff_label(chest, _selected_buffs[i].desc)

		chest.chest_opened.connect(_on_buff_chest_opened.bind(i, chest))

func _add_buff_label(chest, description: String) -> void:
	# Original dimensiuni, doar fix la line_spacing (era -2, suprapunea liniile)
	var panel_width  := 140
	var panel_height := 48

	var label := Label.new()
	label.name = "BuffLabel"
	label.text = description
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	label.position = Vector2(-panel_width / 2.0, -64)
	label.size = Vector2(panel_width, panel_height)
	label.autowrap_mode = TextServer.AUTOWRAP_WORD
	label.add_theme_font_size_override("font_size", 14)
	label.add_theme_color_override("font_color", Color(1, 0.92, 0.5, 1))
	label.add_theme_color_override("font_outline_color", Color.BLACK)
	label.add_theme_constant_override("outline_size", 2)
	label.add_theme_constant_override("line_spacing", 0)
	chest.add_child(label)

func _on_buff_chest_opened(buff_index: int, opened_chest) -> void:
	if any_chest_opened:
		return
	any_chest_opened = true
	
	_apply_buff(buff_index)
	_unblock_exits()
	
	for chest in chests:
		if chest != opened_chest and is_instance_valid(chest):
			chest.queue_free()

func _apply_buff(buff_index: int) -> void:
	var buff : Dictionary = _selected_buffs[buff_index]
	buff.apply.call()
	PlayerManager.active_buff_ids.append(buff.id)
	if PlayerManager.player:
		PlayerManager.player.update_damage_values()

func _block_exits() -> void:
	var parent = get_parent()
	var transition_names = ["LevelTransition", "LevelTransition2", "LevelTransition3"]
	
	for tname in transition_names:
		if parent.has_node(tname):
			var t = parent.get_node(tname)
			if t is Area2D:
				t.set_deferred("monitoring", false)
				blocked_transitions.append(t)
	
	_create_barrier(north_exit_pos, north_exit_size)
	_create_barrier(south_exit_pos, south_exit_size)

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
	for t in blocked_transitions:
		if is_instance_valid(t):
			t.set_deferred("monitoring", true)
	for b in exit_barriers:
		if is_instance_valid(b):
			b.queue_free()
