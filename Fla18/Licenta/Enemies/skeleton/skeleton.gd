class_name Skeleton extends Enemy

const DEATH_SFX := preload("res://Enemies/Slime/hit_00.wav")

@export var attack_damage: int = 2

var _death_audio : AudioStreamPlayer2D


func _ready() -> void:
	super._ready()
	_setup_animations()
	_death_audio = AudioStreamPlayer2D.new()
	_death_audio.stream = DEATH_SFX
	_death_audio.volume_db = -4.0
	add_child(_death_audio)
	enemy_destroyed.connect(_play_death_sfx)


func _play_death_sfx(_hurt_box: HurtBox) -> void:
	_death_audio.play()

func set_direction(_new_direction: Vector2) -> bool:
	var changed := super.set_direction(_new_direction)
	if cardinal_direction == Vector2.LEFT or cardinal_direction == Vector2.RIGHT:
		sprite.scale.x = 1 if cardinal_direction == Vector2.LEFT else -1
	return changed

func _setup_animations() -> void:
	var tex_idle   = load("res://Enemies/skeleton/Skeleton3_Idle.png")
	var tex_walk   = load("res://Enemies/skeleton/Skeleton3_Walk.png")
	var tex_attack = load("res://Enemies/skeleton/Skeleton3_Attack.png")
	var tex_stun   = load("res://Enemies/skeleton/Skeleton3_Hurt.png")
	var tex_death  = load("res://Enemies/skeleton/Skeleton3_Death.png")

	# [anim_name, texture, frame_count, fps, loop]
	var configs = [
		["idle",    tex_idle,   4, 5.0,  true],
		["walk",    tex_walk,   6, 8.0,  true],
		["chase",   tex_walk,   6, 8.0,  true],
		["stun",    tex_stun,   4, 8.0,  false],
		["destroy", tex_death,  6, 8.0,  false],
	]

	var dir_names: Array[String] = ["down", "up", "side"]
	var dir_rows:  Array[int]    = [0, 1, 2]

	var library = AnimationLibrary.new()

	for cfg in configs:
		var anim_name  : String  = cfg[0]
		var tex                  = cfg[1]
		var frame_count: int     = cfg[2]
		var fps        : float   = cfg[3]
		var do_loop    : bool    = cfg[4]

		for d in range(3):
			var full_name := anim_name + "_" + dir_names[d]
			var anim := Animation.new()
			anim.length = frame_count / fps
			if do_loop:
				anim.loop_mode = Animation.LOOP_LINEAR

			var t_hf := anim.add_track(Animation.TYPE_VALUE)
			anim.track_set_path(t_hf, "Sprite2D:hframes")
			anim.value_track_set_update_mode(t_hf, Animation.UPDATE_DISCRETE)
			anim.track_insert_key(t_hf, 0.0, frame_count)

			var t_vf := anim.add_track(Animation.TYPE_VALUE)
			anim.track_set_path(t_vf, "Sprite2D:vframes")
			anim.value_track_set_update_mode(t_vf, Animation.UPDATE_DISCRETE)
			anim.track_insert_key(t_vf, 0.0, 4)

			var t_tex := anim.add_track(Animation.TYPE_VALUE)
			anim.track_set_path(t_tex, "Sprite2D:texture")
			anim.value_track_set_update_mode(t_tex, Animation.UPDATE_DISCRETE)
			anim.track_insert_key(t_tex, 0.0, tex)

			var t_f := anim.add_track(Animation.TYPE_VALUE)
			anim.track_set_path(t_f, "Sprite2D:frame")
			anim.value_track_set_update_mode(t_f, Animation.UPDATE_DISCRETE)
			for f in range(frame_count):
				anim.track_insert_key(t_f, f / fps, dir_rows[d] * frame_count + f)

			library.add_animation(full_name, anim)

	if animation_player.has_animation_library(""):
		animation_player.remove_animation_library("")
	animation_player.add_animation_library("", library)
	animation_player.play("idle_down")
