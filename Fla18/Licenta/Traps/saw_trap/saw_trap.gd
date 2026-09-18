class_name SawTrap extends Node2D

@export var travel_distance : float = 80.0
@export var move_speed : float = 60.0
@export var horizontal : bool = true
@export var damage : int = 2
@export var damage_interval : float = 0.5

var _start_pos : Vector2
var _direction : float = 1.0

@onready var hurt_box: HurtBox = $HurtBox
@onready var sprite: AnimatedSprite2D = $AnimatedSprite2D
@onready var pulse_timer: Timer = $PulseTimer


func _ready() -> void:
	add_to_group("traps")
	_start_pos = position
	hurt_box.damage = damage
	
	pulse_timer.wait_time = damage_interval
	pulse_timer.timeout.connect(_reset_hurt_box)
	pulse_timer.start()
	
	hurt_box.did_damage.connect(_on_did_damage)
	
	if sprite and sprite.sprite_frames and sprite.sprite_frames.has_animation("spin"):
		sprite.play("spin")


func _physics_process(delta: float) -> void:
	if travel_distance <= 0:
		return
	
	var axis_pos : float = position.x if horizontal else position.y
	var start_axis : float = _start_pos.x if horizontal else _start_pos.y
	var dist : float = axis_pos - start_axis
	
	if dist >= travel_distance:
		_direction = -1.0
	elif dist <= 0.0:
		_direction = 1.0
	
	if horizontal:
		position.x += _direction * move_speed * delta
	else:
		position.y += _direction * move_speed * delta


func _on_did_damage() -> void:
	hurt_box.monitoring = false


func _reset_hurt_box() -> void:
	hurt_box.monitoring = true
