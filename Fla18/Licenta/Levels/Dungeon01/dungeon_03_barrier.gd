extends Node

## Blocheaza intrarea in Dungeon01/03 dupa ce playerul intra.
## Bariera se sterge cand cheia este ridicata (ItemDropper.drop_collected).

var _barrier : StaticBody2D = null

func _ready() -> void:
	await get_tree().physics_frame
	await get_tree().physics_frame

	var parent = get_parent()

	# Dezactiveaza tranzitia de intrare imediat
	if parent.has_node("LevelTransition"):
		var t = parent.get_node("LevelTransition")
		if t is Area2D:
			t.monitoring = false

	# Creeaza bariera fizica la intrare (x~16, langa tranzitia de la x=0)
	_create_barrier()

	# Conecteaza semnalul de ridicare a cheii
	for dropper in get_tree().get_nodes_in_group("item_droppers"):
		if is_instance_valid(dropper) and not dropper.drop_collected.is_connected(_on_key_collected):
			dropper.drop_collected.connect(_on_key_collected)


func _create_barrier() -> void:
	_barrier = StaticBody2D.new()
	_barrier.collision_layer = 16
	_barrier.collision_mask = 0
	_barrier.position = Vector2(-16, 64)

	var shape_node := CollisionShape2D.new()
	var rect := RectangleShape2D.new()
	rect.size = Vector2(48, 80)
	shape_node.shape = rect
	_barrier.add_child(shape_node)

	get_parent().add_child(_barrier)


func _on_key_collected() -> void:
	# Sterge bariera fizica
	if is_instance_valid(_barrier):
		_barrier.queue_free()
	_barrier = null

	# Permite tranzitia inapoi la 02 (altfel anti-backtrack o blocheaza)
	LevelManager.previous_scene_path = ""

	# Re-activeaza tranzitia de iesire
	var parent = get_parent()
	if parent.has_node("LevelTransition"):
		var t = parent.get_node("LevelTransition")
		if t is Area2D:
			t.set_deferred("monitoring", true)
