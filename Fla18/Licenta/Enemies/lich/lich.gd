class_name Lich extends Enemy

const PROJECTILE = preload("res://Enemies/lich/lich_projectile.tscn")
const SKELETON   = preload("res://Enemies/skeleton/skeleton.tscn")

@export var shoot_cooldown: float  = 4.5
@export var shoot_range:    float  = 300.0
@export var spawn_interval: float  = 5.0
@export var spawn_count:    int    = 1

var _shoot_timer:      float  = 0.0
var _spawn_timer:      float  = 0.0
var _is_acting:        bool   = false
var _pending_spawn:    bool   = false
var _active_projectile: Node2D = null
var _hurt_cooldown:    float  = 0.0    # cat timp e > 0, lich nu poate ataca (hit = reset)

const DEATH_SFX := preload("res://Enemies/Slime/hit_00.wav")

var _sfx_shoot: AudioStreamPlayer2D
var _sfx_spawn: AudioStreamPlayer2D
var _sfx_death: AudioStreamPlayer2D

func _ready() -> void:
	super._ready()
	_setup_animations()
	animation_player.animation_finished.connect(_on_animation_finished)
	enemy_destroyed.connect(_on_lich_destroyed)
	# Fix pushback: la damage, reset _is_acting ca physics_process sa nu zero-uiasca
	# velocitatea de knockback setata de enemy_state_stun.
	enemy_damaged.connect(_on_lich_damaged)
	_sfx_shoot = _make_sfx_player(_build_shoot_stream())
	_sfx_spawn = _make_sfx_player(_build_spawn_stream())
	_sfx_death = AudioStreamPlayer2D.new()
	_sfx_death.stream = DEATH_SFX
	_sfx_death.volume_db = -4.0
	add_child(_sfx_death)

func _on_lich_destroyed(_hurt_box) -> void:
	_sfx_death.play()
	if is_instance_valid(_active_projectile):
		_active_projectile.queue_free()
		_active_projectile = null

func _on_lich_damaged(_hurt_box) -> void:
	# Reset complet la fiecare hit: lich nu mai termina actiunea curenta + cooldown-urile
	# o iau de la 0 (nu mai apuca sa traga sau sa spawneze imediat dupa stun).
	_is_acting = false
	_pending_spawn = false
	_shoot_timer = 0.0
	_spawn_timer = 0.0
	# Hurt cooldown: cat timp player-ul il bate constant (sub 0.6s intre hituri),
	# lich nu apuca sa atace. Fiecare hit reseteaza cooldown-ul.
	_hurt_cooldown = 0.6
	# Daca avea un proiectil pe drum si inca nu a iesit de lich, sterge-l.
	if is_instance_valid(_active_projectile):
		_active_projectile.queue_free()
		_active_projectile = null

func set_direction(_new_direction: Vector2) -> bool:
	var changed := super.set_direction(_new_direction)
	if cardinal_direction == Vector2.LEFT or cardinal_direction == Vector2.RIGHT:
		sprite.scale.x = 1 if cardinal_direction == Vector2.LEFT else -1
	return changed

func update_animation(state: String) -> void:
	if _is_acting and (state == "chase" or state == "walk" or state == "idle"):
		return
	super.update_animation(state)

func _on_animation_finished(anim_name: String) -> void:
	if not anim_name.begins_with("attack"):
		return
	_is_acting = false
	if _pending_spawn and hp > 0:
		_pending_spawn = false
		_do_spawn()
	if hp > 0:
		update_animation("chase")

func _physics_process(_delta: float) -> void:
	if _is_acting:
		velocity = Vector2.ZERO
	move_and_slide()

func _process(delta: float) -> void:
	super._process(delta)
	if hp <= 0:
		return
	if not player or player.hp <= 0:
		return
	if _is_acting:
		return
	# Hurt cooldown — daca player-ul tocmai a dat un hit, lich nu poate ataca
	if _hurt_cooldown > 0.0:
		_hurt_cooldown -= delta
		return
	_shoot_timer += delta
	_spawn_timer  += delta
	if _shoot_timer >= shoot_cooldown:
		_try_shoot()
	elif _spawn_timer >= spawn_interval:
		_start_spawn()

func _try_shoot() -> void:
	if not is_instance_valid(player):
		return
	if is_instance_valid(_active_projectile):
		return
	var dist := global_position.distance_to(player.global_position)
	if dist > shoot_range:
		return
	_shoot_timer = 0.0
	_is_acting = true
	_sfx_shoot.play()
	update_animation("attack")
	if is_instance_valid(_active_projectile):
		_active_projectile.queue_free()
	var dir := (player.global_position - global_position).normalized()
	var proj: Node2D = PROJECTILE.instantiate()
	proj.direction = dir
	proj.global_position = global_position
	_active_projectile = proj
	get_parent().add_child(proj)

func _start_spawn() -> void:
	_spawn_timer = 0.0
	_is_acting = true
	_pending_spawn = true
	update_animation("attack")

func _do_spawn() -> void:
	_sfx_spawn.play()
	for i in range(spawn_count):
		var sk: CharacterBody2D = SKELETON.instantiate()
		sk.position = global_position + Vector2(randf_range(-40, 40), randf_range(-40, 40))
		get_parent().call_deferred("add_child", sk)

func _make_sfx_player(stream: AudioStreamWAV) -> AudioStreamPlayer2D:
	var p := AudioStreamPlayer2D.new()
	p.stream = stream
	p.bus = &"SFX"
	p.max_distance = 600.0
	add_child(p)
	return p

func _build_wav(samples: PackedFloat32Array, rate: int) -> AudioStreamWAV:
	var stream := AudioStreamWAV.new()
	stream.mix_rate = rate
	stream.stereo = false
	stream.format = 1
	var data := PackedByteArray()
	data.resize(samples.size() * 2)
	for i in samples.size():
		var v := int(clamp(samples[i] * 32767.0, -32768.0, 32767.0))
		data[i * 2]     = v & 0xFF
		data[i * 2 + 1] = (v >> 8) & 0xFF
	stream.data = data
	return stream

func _build_shoot_stream() -> AudioStreamWAV:
	var rate := 22050
	var n    := int(rate * 0.4)
	var s    := PackedFloat32Array()
	s.resize(n)
	for i in n:
		var t  := float(i) / rate
		var p  := float(i) / n
		var hz := lerpf(520.0, 110.0, pow(p, 0.4))
		var w  := sin(TAU * hz * t) * 0.7 + sin(TAU * hz * 2.1 * t) * 0.2
		w += (randf() * 2.0 - 1.0) * 0.12
		s[i] = w * exp(-p * 6.0)
	return _build_wav(s, rate)

func _build_spawn_stream() -> AudioStreamWAV:
	var rate := 22050
	var n    := int(rate * 1.1)
	var s    := PackedFloat32Array()
	s.resize(n)
	for i in n:
		var t  := float(i) / rate
		var p  := float(i) / n
		var w  := sin(TAU * 55.0 * t) * 0.5
		w += sin(TAU * 110.0 * t) * 0.25
		w += sin(TAU * 82.5 * t)  * 0.2
		w += sin(TAU * lerpf(250.0, 80.0, p) * t) * 0.15
		var env := minf(p * 6.0, 1.0) * (1.0 - maxf((p - 0.65) * 2.86, 0.0))
		s[i] = w * env * 0.75
	return _build_wav(s, rate)

func _setup_animations() -> void:
	var tex_idle   = load("res://Enemies/lich/Lich1_Idle.png")
	var tex_walk   = load("res://Enemies/lich/Lich1_Walk.png")
	var tex_attack = load("res://Enemies/lich/Lich1_Attack.png")
	var tex_stun   = load("res://Enemies/lich/Lich1_Hurt.png")
	var tex_death  = load("res://Enemies/lich/Lich1_Death.png")

	# attack: 8 frames over 1.5 seconds
	var attack_fps: float = 8.0 / 1.5

	var configs = [
		["idle",    tex_idle,   4,  5.0,        true],
		["walk",    tex_walk,   6,  8.0,        true],
		["chase",   tex_walk,   6,  8.0,        true],
		["attack",  tex_attack, 8,  attack_fps, false],
		["stun",    tex_stun,   4,  8.0,        false],
		["destroy", tex_death, 10,  8.0,        false],
	]

	var dir_names: Array[String] = ["down", "up", "side"]
	var dir_rows:  Array[int]    = [0, 1, 2]
	var library   = AnimationLibrary.new()

	for cfg in configs:
		var anim_name  : String = cfg[0]
		var tex                 = cfg[1]
		var frame_count: int    = cfg[2]
		var fps        : float  = cfg[3]
		var do_loop    : bool   = cfg[4]

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
