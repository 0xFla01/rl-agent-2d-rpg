extends Node

var _barrier : StaticBody2D

func _ready() -> void:
	await get_tree().process_frame
	await get_tree().process_frame

	if QuestManager.get_quest_index_by_title("Defeat the Dark Wizard") != -1:
		return

	_create_barrier()
	QuestManager.quest_updated.connect(_on_quest_updated)


func _on_quest_updated(q) -> void:
	if q.title == "Defeat the Dark Wizard":
		_remove_barrier()
		QuestManager.quest_updated.disconnect(_on_quest_updated)


func _create_barrier() -> void:
	_barrier = StaticBody2D.new()
	_barrier.collision_layer = 16
	_barrier.collision_mask = 0
	get_parent().add_child(_barrier)

	var shape_node := CollisionShape2D.new()
	var rect := RectangleShape2D.new()
	rect.size = Vector2(600, 20)
	shape_node.shape = rect
	_barrier.add_child(shape_node)
	_barrier.global_position = Vector2(224, -36)


func _remove_barrier() -> void:
	if is_instance_valid(_barrier):
		_barrier.queue_free()
	_barrier = null
