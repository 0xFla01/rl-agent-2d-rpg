extends Node2D

const SPIKE_SCENE := preload("res://Traps/spike_trap/spike_trap.tscn")

@export var from_x: float = 32.0
@export var to_x: float = 608.0
@export var row_y: float = 0.0

func _ready() -> void:
	var x := from_x
	while x <= to_x + 0.5:
		var spike := SPIKE_SCENE.instantiate()
		spike.position = Vector2(x, row_y)
		spike.static_mode = true
		add_child(spike)
		x += 16.0
