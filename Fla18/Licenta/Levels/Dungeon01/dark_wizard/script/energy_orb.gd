class_name EnergyOrb extends Node2D


@export var speed : float = 200

@export var shoot_audio : AudioStream
@export var hit_audio : AudioStream


var direction : Vector2 = Vector2.DOWN
var custom_direction : Vector2 = Vector2.ZERO
var homing : bool = false
var homing_duration : float = 0.0

@onready var hurt_box: HurtBox = $HurtBox
@onready var audio_stream_player_2d: AudioStreamPlayer2D = $AudioStreamPlayer2D



func _ready() -> void:
	add_to_group("boss_projectiles")
	hurt_box.did_damage.connect( hit_player )
	play_audio( shoot_audio )
	get_tree().create_timer( 5 ).timeout.connect( destroy )
	if custom_direction != Vector2.ZERO:
		direction = custom_direction
	else:
		direction = global_position.direction_to( PlayerManager.player.global_position )
	flicker()
	pass


func _process( delta: float ) -> void:
	if homing and homing_duration > 0.0 and PlayerManager.player:
		var target := global_position.direction_to( PlayerManager.player.global_position )
		direction = direction.lerp( target, 4.5 * delta ).normalized()
		homing_duration -= delta
	position += direction * speed * delta



func flicker() -> void:
	modulate.a = randf() * 0.7 + 0.3
	await get_tree().create_timer( 0.05 ).timeout
	flicker()
	pass


func hit_player() -> void:
	if PlayerManager.player and PlayerManager.player.invulnerable:
		return
	play_audio( hit_audio )
	hurt_box.set_deferred( "monitoring", false )


func play_audio( _a : AudioStream ) -> void:
	audio_stream_player_2d.stream = _a
	audio_stream_player_2d.play()


func destroy() -> void:
	queue_free()
