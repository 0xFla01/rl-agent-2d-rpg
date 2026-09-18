class_name LeverDoor extends Node2D

@onready var anim_player: AnimationPlayer = $AnimationPlayer
@onready var audio: AudioStreamPlayer2D = $AudioStreamPlayer2D

func _ready() -> void:
	anim_player.play("closed")
	var manager := get_parent().get_node_or_null("LeverRoomManager") as LeverRoomManager
	if manager:
		manager.exit_unlocked.connect(_on_exit_unlocked)

func _on_exit_unlocked() -> void:
	anim_player.play("open_door")
	audio.play()
