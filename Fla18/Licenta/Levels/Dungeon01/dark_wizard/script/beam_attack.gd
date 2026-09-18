class_name BeamAttack extends Node2D

@export var use_timer : bool = false
@export var time_between_attacks : float = 3

@onready var animation_player: AnimationPlayer = $AnimationPlayer

var _attack_id := 0
var is_firing : bool = false   # Run8b: export obs — agentul vede beamul cand e activ


func _ready() -> void:
	add_to_group("boss_beams")
	if use_timer == true:
		attack_delay()


func cancel_attack() -> void:
	_attack_id += 1
	is_firing = false
	animation_player.stop()


func attack( speed : float = 1.0 ) -> void:
	_attack_id += 1
	var my_id := _attack_id
	is_firing = true
	animation_player.speed_scale = speed
	animation_player.play( "attack" )
	await animation_player.animation_finished
	if my_id != _attack_id:
		return
	is_firing = false
	animation_player.speed_scale = 1.0
	animation_player.play( "default" )
	if use_timer == true:
		attack_delay()


func attack_delay() -> void:
	await get_tree().create_timer( time_between_attacks ).timeout
	attack()
