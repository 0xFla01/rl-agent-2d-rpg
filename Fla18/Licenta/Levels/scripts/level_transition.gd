@tool
class_name LevelTransition extends Area2D

signal entered_from_here

enum SIDE { LEFT, RIGHT, TOP, BOTTOM }

@export_file( "*.tscn" ) var level
@export var target_transition_area : String = "LevelTransition"
@export var center_player : bool = false

@export_category("Collision Area Settings")

@export_range( 1, 12, 1, "or_greater") var size : int = 2 :
	set( _v ):
		size = _v
		_update_area()

@export var side: SIDE = SIDE.LEFT :
	set( _v ):
		side = _v
		_update_area()

@export var snap_to_grid : bool = false :
	set ( _v ):
		_snap_to_grid()

@onready var collision_shape: CollisionShape2D = $CollisionShape2D




func _ready() -> void:
	_update_area()
	if Engine.is_editor_hint():
		return
	add_to_group("level_transitions")
	monitoring = false
	_place_player()
	
	await LevelManager.level_loaded
	
	# Some extra physics frame awaits will avoid issues related to frame rate
	# & physics process frame rate not syncing up... we had a bug where no matter
	# what we did the collision would still sometimes happen at the players
	# OLD position after loading on PC's running the game at 120 or 144fps
	await get_tree().physics_frame
	await get_tree().physics_frame
	
	monitoring = true
	body_entered.connect( _player_entered )



func _physics_process(_delta: float) -> void:
	if not monitoring:
		return
	var p = PlayerManager.get("player")
	if not p or not is_instance_valid(p):
		return
	if overlaps_body(p):
		_player_entered(p)


func _player_entered( _p : Node2D ) -> void:
	if LevelManager.previous_scene_path != "" and level == LevelManager.previous_scene_path:
		return
	LevelManager.load_new_level( level, target_transition_area, get_offset() )


func _place_player() -> void:
	if name != LevelManager.target_transition:
		return
	PlayerManager.set_player_position( global_position + LevelManager.position_offset )
	# Reset velocity + force Idle: la viteza mare (dash + time_scale 3-4x) momentum-ul
	# mostenit ducea playerul prin transitionul urmator inainte ca el sa apuce sa se
	# stabilizeze (skip Area01/04 cand vine din Area02/02). Dash state seteaza velocity
	# la fiecare frame, deci doar velocity=0 nu ajunge — trebuie schimbat state-ul.
	var p = PlayerManager.get("player")
	if p and is_instance_valid(p):
		p.velocity = Vector2.ZERO
		if "state_machine" in p and p.state_machine and p.state_machine.has_node("Idle"):
			p.state_machine.change_state(p.state_machine.get_node("Idle"))
	entered_from_here.emit()


func get_offset() -> Vector2:
	var offset : Vector2 = Vector2.ZERO
	var player_pos = PlayerManager.player.global_position
	
	if side == SIDE.LEFT or side == SIDE.RIGHT:
		if center_player == true:
			offset.y = 0
		else:
			offset.y = player_pos.y - global_position.y
		offset.x = 16
		if side == SIDE.LEFT:
			offset.x *= -1
	else:
		if center_player == true:
			offset.x = 0
		else:
			offset.x = player_pos.x - global_position.x
		offset.y = 16
		if side == SIDE.TOP:
			offset.y *= -1

	return offset



func _update_area() -> void:
	var new_rect : Vector2 = Vector2( 32, 32 )
	var new_position : Vector2 = Vector2.ZERO
	
	if side == SIDE.TOP:
		new_rect.x *= size
		new_position.y -= 16
	elif side == SIDE.BOTTOM:
		new_rect.x *= size
		new_position.y += 16
	elif side == SIDE.LEFT:
		new_rect.y *= size
		new_position.x -= 16
	elif side == SIDE.RIGHT:
		new_rect.y *= size
		new_position.x += 16
	
	if collision_shape == null:
		collision_shape = get_node("CollisionShape2D")
	
	collision_shape.shape.size = new_rect
	collision_shape.position = new_position


func _snap_to_grid() -> void:
	position.x = round( position.x / 16 ) * 16
	position.y = round( position.y / 16 ) * 16
