class_name SpikeTrap extends Node2D

@export var damage : int = 2
@export var active_duration : float = 1.2
@export var inactive_duration : float = 1.5
@export var initial_delay : float = 0.0
@export var static_mode : bool = false

var is_active : bool = false

@onready var hurt_box: HurtBox = $HurtBox
@onready var sprite: Sprite2D = $Sprite2D
@onready var active_timer: Timer = $ActiveTimer
@onready var inactive_timer: Timer = $InactiveTimer


func _ready() -> void:
	add_to_group("traps")
	hurt_box.damage = damage
	if static_mode:
		_set_visual_state(true)
		hurt_box.monitoring = true
		return

	hurt_box.monitoring = false
	active_timer.wait_time = active_duration
	inactive_timer.wait_time = inactive_duration
	active_timer.timeout.connect(_deactivate)
	inactive_timer.timeout.connect(_activate)
	_set_visual_state(false)
	await get_tree().create_timer(initial_delay).timeout
	inactive_timer.start()


func _activate() -> void:
	is_active = true
	hurt_box.monitoring = true
	_set_visual_state(true)
	active_timer.start()


func _deactivate() -> void:
	is_active = false
	hurt_box.monitoring = false
	_set_visual_state(false)
	inactive_timer.start()


func _set_visual_state(active: bool) -> void:
	if sprite:
		sprite.visible = active


func force_static() -> void:
	active_timer.stop()
	inactive_timer.stop()
	is_active = true
	hurt_box.monitoring = true
	hurt_box.collision_mask = 2
	_set_visual_state(true)
