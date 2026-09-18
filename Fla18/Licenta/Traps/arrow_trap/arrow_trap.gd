# Arrow Trap - Trage sageti la intervale regulate
# Se poate configura directia (stanga/dreapta) si intervalul de tragere
class_name ArrowTrap extends Node2D

## Directia in care zboara sagetile (Vector2.LEFT sau Vector2.RIGHT)
@export var fire_direction : Vector2 = Vector2.RIGHT
## Cat de des trage (secunde)
@export var fire_interval : float = 2.0
## Viteza sagetii
@export var arrow_speed : float = 250.0
## Damage-ul sagetii
@export var arrow_damage : int = 2
## Cat timp asteapta inainte de primul foc
@export var initial_delay : float = 0.5

@onready var fire_timer: Timer = $FireTimer
@onready var arrow_spawn: Marker2D = $ArrowSpawn
@onready var animator: AnimatedSprite2D = $AnimatedSprite2D

# Preload arrow scene
const TRAP_ARROW_SCENE = preload("res://Traps/arrow_trap/trap_arrow.tscn")


func _ready() -> void:
	add_to_group("traps")

	# Flip vizual daca merge spre stanga
	if fire_direction == Vector2.LEFT:
		scale.x = -1.0

	# Run5e: in curriculum mode, A1/03 trap arrows sunt dezactivate (agent invata layout fara dmg).
	var ai_ctrl := get_node_or_null("/root/GlobalAIController")
	var current_scene := get_tree().current_scene
	if ai_ctrl != null and ai_ctrl.enabled and ai_ctrl.curriculum_enabled \
			and current_scene != null and current_scene.scene_file_path == "res://Levels/Area01/03.tscn":
		return  # nu pornim FireTimer — agentul poate explora liber

	fire_timer.wait_time = fire_interval
	fire_timer.timeout.connect(_fire_arrow)

	# Delay initial
	await get_tree().create_timer(initial_delay).timeout
	fire_timer.start()
	_fire_arrow()


func _fire_arrow() -> void:
	if not TRAP_ARROW_SCENE:
		return
	
	# Joaca animatia de "shoot" daca exista
	if animator and animator.sprite_frames and animator.sprite_frames.has_animation("shoot"):
		animator.play("shoot")
	
	var arrow = TRAP_ARROW_SCENE.instantiate()
	get_parent().add_child(arrow)
	arrow.global_position = arrow_spawn.global_position
	arrow.damage = arrow_damage
	arrow.speed = arrow_speed
	arrow.direction = fire_direction
	arrow.start()
