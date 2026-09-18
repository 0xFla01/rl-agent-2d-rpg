class_name Enemy extends CharacterBody2D

signal direction_changed( new_direction : Vector2 )
signal enemy_damaged( hurt_box : HurtBox )
signal enemy_destroyed( hurt_box : HurtBox )

const DIR_4 = [ Vector2.RIGHT, Vector2.DOWN, Vector2.LEFT, Vector2.UP ]

@export var hp : int = 3
@export var xp_reward : int = 1

var cardinal_direction : Vector2 = Vector2.DOWN
var direction : Vector2 = Vector2.ZERO
var player : Player
var invulnerable : bool = false

@onready var animation_player : AnimationPlayer = $AnimationPlayer
@onready var sprite : Sprite2D = $Sprite2D
@onready var hit_box : HitBox = $HitBox
@onready var state_machine : EnemyStateMachine = $EnemyStateMachine


# Called when the node enters the scene tree for the first time.
func _ready():
	state_machine.initialize( self )
	player = PlayerManager.player
	hit_box.damaged.connect( _take_damage )
	add_to_group("enemies")
	# Run5l: in A2/02 (boss room) — enemies "dorm" pana cand AI intra in vision range.
	var scene := get_tree().current_scene
	var scene_path := scene.scene_file_path if scene else ""
	if "Area02/02" in scene_path:
		for s in state_machine.states:
			if s is EnemyStateIdle:
				(s as EnemyStateIdle).state_duration_min = 999.0
				(s as EnemyStateIdle).state_duration_max = 999.0
	# Run5l_v8: in A2/01 — vision area MARE (5x scale) — enemies vin direct la player
	# Asta forteaza combat rapid, AI nu mai trebuie sa caute enemies
	if "Area02/01" in scene_path:
		var vision := get_node_or_null("VisionArea") as Area2D
		if vision:
			vision.scale = Vector2(5, 5)
	pass


# Called every frame. 'delta' is the elapsed time since the previous frame.
func _process(_delta):
	pass


func _physics_process(_delta):
	move_and_slide()


func set_direction( _new_direction : Vector2 ) -> bool:
	direction = _new_direction
	if direction == Vector2.ZERO:
		return false
	
	var to_player : Vector2 = direction
	if player and is_instance_valid(player):
		to_player = (player.global_position - global_position).normalized()
	
	var new_dir : Vector2
	if abs(to_player.x) > abs(to_player.y):
		new_dir = Vector2.RIGHT if to_player.x > 0 else Vector2.LEFT
	else:
		new_dir = Vector2.DOWN if to_player.y > 0 else Vector2.UP
	
	if new_dir == cardinal_direction:
		return false
	
	cardinal_direction = new_dir
	direction_changed.emit( new_dir )
	sprite.scale.x = -1 if cardinal_direction == Vector2.LEFT else 1
	return true


func update_animation( state : String ) -> void:
	animation_player.play( state + "_" + anim_direction() )
	pass


func anim_direction() -> String:
	if cardinal_direction == Vector2.DOWN:
		return "down"
	elif cardinal_direction == Vector2.UP:
		return "up"
	else:
		return "side"



func _take_damage( hurt_box : HurtBox ) -> void:
	if invulnerable == true:
		return
	hp -= hurt_box.damage
	PlayerManager.shake_camera()
	EffectManager.damage_text( hurt_box.damage, global_position + Vector2(0,-36) )
	if hp > 0:
		enemy_damaged.emit( hurt_box )
	else:
		enemy_destroyed.emit( hurt_box )
