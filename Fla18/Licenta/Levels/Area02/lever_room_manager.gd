class_name LeverRoomManager extends Node

const TREASURE_CHEST = preload("res://Interactables/TreasureChest/treasure-chest.tscn")

signal all_levers_activated
signal lever_count_changed(current: int, total: int)
signal exit_unlocked

@export var chest_positions : Array[Vector2] = [
	Vector2(240, 480),
	Vector2(336, 480),
	Vector2(432, 480),
]

var _activated_count: int = 0
var _lever_nodes: Array[Lever] = []
var _chests : Array = []
var _selected_buffs : Array[Dictionary] = []
var _any_chest_opened : bool = false
var _chests_spawned : bool = false


func _ready() -> void:
	add_to_group("lever_managers")
	add_to_group("buff_chest_managers")
	await get_tree().create_timer(0.1).timeout
	var parent := get_parent()
	if not parent:
		return
	for child in parent.get_children():
		if child is Lever:
			_lever_nodes.append(child)
			child.lever_activated.connect(_on_lever_activated)
		elif child is SpikeTrap:
			child.force_static()
		elif child is SawTrap:
			var hb := child.get_node_or_null("HurtBox") as Area2D
			if hb:
				hb.collision_mask = 2


func _on_lever_activated() -> void:
	_activated_count += 1
	lever_count_changed.emit(_activated_count, _lever_nodes.size())
	if _activated_count >= _lever_nodes.size() and not _chests_spawned:
		_chests_spawned = true   # guard: charge attack poate activa 2+ levere in acelasi frame
		all_levers_activated.emit()
		_kill_all_enemies_in_scene()
		_disable_all_traps()
		_spawn_chests()


func _spawn_chests() -> void:
	if not _chests.is_empty():
		return
	_selected_buffs = BuffPool.get_random_buffs(3)
	var parent := get_parent()
	if not parent:
		return
	for i in range(_selected_buffs.size()):
		var chest = TREASURE_CHEST.instantiate()
		chest.name = "LeverChest" + str(i + 1)
		chest.position = chest_positions[i]
		parent.add_child(chest)
		_chests.append(chest)
		await get_tree().process_frame
		_add_buff_label(chest, _selected_buffs[i].desc)
		chest.chest_opened.connect(_on_buff_chest_opened.bind(i, chest))


func _add_buff_label(chest, description: String) -> void:
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
	if _any_chest_opened:
		return
	_any_chest_opened = true
	var buff : Dictionary = _selected_buffs[buff_index]
	buff.apply.call()
	PlayerManager.active_buff_ids.append(buff.id)
	if PlayerManager.player:
		PlayerManager.player.update_damage_values()
	for chest in _chests:
		if chest != opened_chest and is_instance_valid(chest):
			chest.queue_free()
	exit_unlocked.emit()


func get_chest_data() -> Array:
	if not _chests_spawned or _any_chest_opened or _chests.is_empty():
		return []
	var result := []
	for i in _chests.size():
		if not is_instance_valid(_chests[i]):
			continue
		result.append({
			"buff_id": _selected_buffs[i].id if i < _selected_buffs.size() else "",
			"x": _chests[i].global_position.x,
			"y": _chests[i].global_position.y,
		})
	return result


func _disable_all_traps() -> void:
	# Dezactiveaza spike, arrow si saw traps cand toate leverele sunt activate
	for trap in get_tree().get_nodes_in_group("traps"):
		if not is_instance_valid(trap):
			continue
		if "is_active" in trap:
			trap.is_active = false
		trap.set_process(false)
		trap.set_physics_process(false)
		# Opreste orice Timer copil (ex: FireTimer din ArrowTrap continua sa traga
		# chiar daca set_process e false, fiindca Timer-ul are mecanism propriu)
		for c in trap.get_children():
			if c is Timer:
				c.stop()
				c.set_paused(true)
			elif c is Area2D:
				c.set_deferred("monitoring", false)
				c.set_deferred("monitorable", false)
	# Sterge sagetile inca in zbor (din arrow_trap)
	for arrow in get_tree().get_nodes_in_group("trap_arrows"):
		if is_instance_valid(arrow):
			arrow.queue_free()


func _kill_all_enemies_in_scene() -> void:
	var fake_hurt := HurtBox.new()
	fake_hurt.damage = 9999
	add_child(fake_hurt)
	for enemy in get_tree().get_nodes_in_group("enemies"):
		if is_instance_valid(enemy) and "hit_box" in enemy and is_instance_valid(enemy.hit_box):
			fake_hurt.global_position = enemy.global_position
			enemy.hit_box.take_damage(fake_hurt)
	fake_hurt.queue_free()
