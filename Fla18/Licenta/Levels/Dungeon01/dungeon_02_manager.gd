extends Node

## Blocheaza intrarea in Dungeon01/03 daca playerul are deja cheia.

func _ready() -> void:
	await get_tree().process_frame

	var key_item = load("res://Items/key_dungeon.tres")
	if not key_item:
		return
	var qty := PlayerManager.INVENTORY_DATA.get_item_held_quantity(key_item)
	if qty <= 0:
		return

	# Playerul are cheia — blocheaza LevelTransition2 (spre 03)
	var parent = get_parent()
	if parent.has_node("LevelTransition2"):
		var t = parent.get_node("LevelTransition2")
		if t is Area2D:
			t.monitoring = false

	_create_barrier()


func _create_barrier() -> void:
	var barrier := StaticBody2D.new()
	barrier.collision_layer = 16
	barrier.collision_mask = 0
	barrier.position = Vector2(528, 64)

	var shape_node := CollisionShape2D.new()
	var rect := RectangleShape2D.new()
	rect.size = Vector2(48, 64)
	shape_node.shape = rect
	barrier.add_child(shape_node)

	get_parent().add_child(barrier)
