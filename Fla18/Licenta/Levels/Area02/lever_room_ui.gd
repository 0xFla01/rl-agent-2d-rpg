extends CanvasLayer

@export var manager_path: NodePath

@onready var label: Label = $Label

var _total: int = 4


func _ready() -> void:
	label.add_theme_color_override("font_color", Color(1, 0.9, 0.3, 1))
	label.add_theme_color_override("font_outline_color", Color.BLACK)
	label.add_theme_constant_override("outline_size", 3)
	label.add_theme_font_size_override("font_size", 16)
	label.add_theme_stylebox_override("normal", StyleBoxEmpty.new())
	var manager := get_node(manager_path) as LeverRoomManager
	if manager:
		manager.lever_count_changed.connect(_on_count_changed)
		manager.all_levers_activated.connect(_on_all_done)
	_refresh(0)


func _on_count_changed(current: int, total: int) -> void:
	_total = total
	_refresh(current)


func _on_all_done() -> void:
	label.text = "All levers done!"
	await get_tree().create_timer(2.0).timeout
	queue_free()


func _refresh(current: int) -> void:
	label.text = "Levers: %d / %d" % [current, _total]
