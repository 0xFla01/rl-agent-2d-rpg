extends Node

signal room_cleared

const TREASURE_CHEST = preload("res://Interactables/TreasureChest/treasure-chest.tscn")
const GOBLIN         = preload("res://Enemies/goblin/goblin.tscn")
const SKELETON       = preload("res://Enemies/skeleton/skeleton.tscn")
const LICH           = preload("res://Enemies/lich/lich.tscn")
const SLIME          = preload("res://Enemies/Slime/slime.tscn")
const ORC            = preload("res://Enemies/orc/orc.tscn")

@export var kill_target : int = 6   # Run5l_v5: 10→6 (wave1+wave2, scoatem wave3)

@export var chest_positions : Array[Vector2] = [
	Vector2(290, 990),
	Vector2(415, 990),
	Vector2(540, 990),
]

@export var north_exit_pos  : Vector2 = Vector2(540, -340)
@export var north_exit_size : Vector2 = Vector2(32, 96)
@export var south_exit_pos  : Vector2 = Vector2(272, 312)
@export var south_exit_size : Vector2 = Vector2(96, 16)
@export var left_entry_pos  : Vector2 = Vector2(-51, 63)
@export var left_entry_size : Vector2 = Vector2(16, 120)

@export var wave1_positions : Array[Vector2] = [
	# REVERT la pozitii originale 5f stable (2.97% A2/01 nat)
	Vector2(270, 330), Vector2(470, 350),  # [0] goblin scout, [1] rezerva
	Vector2(210, 440), Vector2(400, 460), Vector2(570, 420),  # [2] skel stanga, [3] rezerva, [4] skel dreapta
	Vector2(350, 490), Vector2(480, 510), Vector2(260, 550)   # rezerva
]
@export var wave2_positions : Array[Vector2] = [
	# Run5l_v5: REVERT la pozitii originale walkable (5f stable, 2.97% A2/01 nat)
	Vector2(210, 540), Vector2(600, 550),  # [0] LICH stanga (original walkable), [1] rezerva
	Vector2(310, 650), Vector2(490, 660),  # [2] rezerva, [3] SLIME centru-dr
	Vector2(350, 730), Vector2(450, 720),  # [4] GOBLIN centru (langa grapple post)
	Vector2(390, 680), Vector2(270, 600)   # rezerva
]
@export var wave3_positions : Array[Vector2] = [
	# Ancorate langa grapple posts confirmate: (210,984) si (463,937)
	# x: 240-530, y: 860-975 — zona deschisa spre exit sud
	Vector2(390, 870),                     # lich centru
	Vector2(240, 930), Vector2(520, 910),  # 2 skeletons (langa grapple 463,937)
	Vector2(300, 975), Vector2(470, 960),  # 2 slimes (langa grapple 210,984)
	Vector2(200, 860), Vector2(570, 870), Vector2(350, 820),
	Vector2(430, 850), Vector2(260, 890), Vector2(510, 950),
	Vector2(380, 990), Vector2(450, 870)   # rezerva
]

var chests              : Array           = []
var exit_barriers       : Array[StaticBody2D] = []
var blocked_transitions : Array[Area2D]   = []
var spawned_chests      : bool            = false
var any_chest_opened    : bool            = false
var _selected_buffs     : Array[Dictionary] = []
var initial_kill_count  : int             = 0

var current_wave        : int  = 0
var wave1_kill_target   : int  = 3
var wave2_spawn_timer   : float = 0.0
var wave2_spawned       : bool  = false  # Run5l_v5: WAVE 2 ACTIV
var wave3_spawned       : bool  = true   # Run5l_v5: WAVE 3 SCOS (kill_target total 6 = w1+w2)
var wave3_delay         : float = 12.0

var _kill_label         : Label = null
var _music_thread       : Thread = null

func _ready() -> void:
	add_to_group("kill_chest_managers")
	add_to_group("buff_chest_managers")
	_music_thread = Thread.new()
	_music_thread.start(_generate_music)
	await get_tree().process_frame
	initial_kill_count = PlayerManager.total_kill_count
	_create_kill_counter_ui()
	_block_exits()
	_start_wave(1)

func _process(delta: float) -> void:
	var kills_in_room := PlayerManager.total_kill_count - initial_kill_count

	if is_instance_valid(_kill_label):
		_kill_label.text = "Kill %d/%d enemies" % [mini(kills_in_room, kill_target), kill_target]

	if not spawned_chests and kills_in_room >= kill_target:
		spawned_chests = true
		room_cleared.emit()
		if is_instance_valid(_kill_label):
			_kill_label.queue_free()
			_kill_label = null
		_kill_remaining_enemies()
		_spawn_chests()

	if current_wave == 1 and not wave2_spawned and kills_in_room >= wave1_kill_target:
		wave2_spawned = true
		_start_wave(2)

	if current_wave == 2 and not wave3_spawned:
		wave2_spawn_timer += delta
		if wave2_spawn_timer >= wave3_delay:
			wave3_spawned = true
			_start_wave(3)


func _kill_remaining_enemies() -> void:
	# Cand kill_target e atins, ucide automat inamicii ramasi (target deja indeplinit)
	var fake_hurt := HurtBox.new()
	fake_hurt.damage = 9999
	add_child(fake_hurt)
	for enemy in get_tree().get_nodes_in_group("enemies"):
		if is_instance_valid(enemy) and "hit_box" in enemy and is_instance_valid(enemy.hit_box):
			fake_hurt.global_position = enemy.global_position
			enemy.hit_box.take_damage(fake_hurt)
	fake_hurt.queue_free()

func _start_wave(wave: int) -> void:
	current_wave = wave
	match wave:
		1:
			# WAVE 1 — pe pod nord (3 enemies, pozitii safe 5f)
			# Forteaza AI sa coboare din spawn (-33, 70) prin pod ca sa lupte
			# Daca AI spawn-uieste direct in A2/01, vede enemies in observation → coboara
			_spawn_enemy(GOBLIN,   wave1_positions[0])  # scout (270, 330)
			_spawn_enemy(SKELETON, wave1_positions[2])  # flank stanga (210, 440)
			_spawn_enemy(SKELETON, wave1_positions[4])  # flank dreapta (570, 420)
		2:
			# WAVE 2 — Run5l_v8: SLIME → SKELETON (slime lent, AI nu il gasea)
			_spawn_enemy(LICH,     wave2_positions[0])  # caster stanga (210,540)
			_spawn_enemy(SKELETON, wave2_positions[3])  # skel inlocuit slime (490,660)
			_spawn_enemy(GOBLIN,   wave2_positions[4])  # speed centru (350,730)
		3:
			# WAVE 3 — climax / gardian chest: orc tank + skel + 2 goblin (4 enemies)
			# Orc langa chest (390,870) forteaza confruntare directa cu reward la vedere
			# Goblini rapizi flank → AI trebuie sa-i prinda inainte sa-l isoleze de chest
			# Total direct = 10 exact (3+3+4), kill_target = 10
			_spawn_enemy(ORC,      wave3_positions[0])  # tank centru-chest (390,870)
			_spawn_enemy(SKELETON, wave3_positions[1])  # SW (240,930)
			_spawn_enemy(GOBLIN,   wave3_positions[3])  # SW (300,975)
			_spawn_enemy(GOBLIN,   wave3_positions[4])  # SE (470,960)

func _spawn_enemy(scene: PackedScene, pos: Vector2) -> void:
	var enemy := scene.instantiate()
	enemy.position = pos
	get_parent().call_deferred("add_child", enemy)

func _create_kill_counter_ui() -> void:
	var canvas := CanvasLayer.new()
	canvas.layer = 5
	add_child(canvas)

	var label := Label.new()
	label.text = "Kill 0/%d enemies" % kill_target
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.vertical_alignment   = VERTICAL_ALIGNMENT_CENTER
	label.set_anchors_preset(Control.PRESET_TOP_WIDE)
	label.offset_top    = 8.0
	label.offset_bottom = 36.0
	label.offset_left   = 0.0
	label.offset_right  = 0.0
	label.add_theme_font_size_override("font_size", 16)
	label.add_theme_color_override("font_color", Color(1, 0.9, 0.3, 1))
	label.add_theme_color_override("font_outline_color", Color.BLACK)
	label.add_theme_constant_override("outline_size", 3)
	canvas.add_child(label)
	_kill_label = label

func _play_chest_fanfare() -> void:
	var rate   := 22050
	var ndur   := 0.28
	var notes  : Array[float] = [523.0, 659.0, 784.0, 1047.0]
	var n      := int(rate * ndur * notes.size())
	var samples := PackedFloat32Array()
	samples.resize(n)
	for i in n:
		var t   := float(i) / rate
		var ni  := mini(int(t / ndur), notes.size() - 1)
		var nt  := fmod(t, ndur) / ndur
		var env := exp(-nt * 5.5)
		var f   := notes[ni]
		var s   := sin(TAU * f       * t) * 0.50 * env
		s += sin(TAU * f * 2.0 * t) * 0.18 * env
		s += sin(TAU * f * 3.0 * t) * 0.06 * env
		samples[i] = clamp(s, -1.0, 1.0)
	var stream := AudioStreamWAV.new()
	stream.mix_rate = rate
	stream.stereo   = false
	stream.format   = 1
	var data := PackedByteArray()
	data.resize(n * 2)
	for i in n:
		var v := int(clamp(samples[i] * 32767.0, -32768.0, 32767.0))
		data[i * 2]     = v & 0xFF
		data[i * 2 + 1] = (v >> 8) & 0xFF
	stream.data = data
	var player := AudioStreamPlayer.new()
	add_child(player)
	player.stream = stream
	player.play()
	player.finished.connect(player.queue_free)

func _spawn_chests() -> void:
	_play_chest_fanfare()
	_selected_buffs = BuffPool.get_random_buffs(3)

	for i in range(_selected_buffs.size()):
		var chest = TREASURE_CHEST.instantiate()
		chest.name = "PowerChest" + str(i + 1)
		chest.position = chest_positions[i]
		get_parent().add_child(chest)
		chests.append(chest)
		await get_tree().process_frame
		_add_buff_label(chest, _selected_buffs[i].desc)
		chest.chest_opened.connect(_on_chest_opened.bind(i, chest))

func _add_buff_label(chest, description: String) -> void:
	# Identic cu A1/03 original — panel mic, font 14, fara background
	var panel_width  := 140
	var panel_height := 48
	var label        := Label.new()
	label.name       = "BuffLabel"
	label.text       = description
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.vertical_alignment   = VERTICAL_ALIGNMENT_CENTER
	label.position   = Vector2(-panel_width / 2.0, -64)
	label.size       = Vector2(panel_width, panel_height)
	label.autowrap_mode = TextServer.AUTOWRAP_WORD
	label.add_theme_font_size_override("font_size", 14)
	label.add_theme_color_override("font_color", Color(1, 0.92, 0.5, 1))
	label.add_theme_color_override("font_outline_color", Color.BLACK)
	label.add_theme_constant_override("outline_size", 2)
	label.add_theme_constant_override("line_spacing", 0)
	chest.add_child(label)

func _on_chest_opened(buff_index: int, opened_chest) -> void:
	if any_chest_opened:
		return
	any_chest_opened = true
	_apply_buff(buff_index)
	_unblock_exits()
	for chest in chests:
		if chest != opened_chest and is_instance_valid(chest):
			chest.queue_free()

func get_chest_data() -> Array:
	if not spawned_chests or any_chest_opened or chests.is_empty():
		return []
	var result := []
	for i in chests.size():
		if not is_instance_valid(chests[i]):
			continue
		result.append({
			"buff_id": _selected_buffs[i].id if i < _selected_buffs.size() else "",
			"x": chests[i].global_position.x,
			"y": chests[i].global_position.y,
		})
	return result

func _apply_buff(buff_index: int) -> void:
	var buff : Dictionary = _selected_buffs[buff_index]
	buff.apply.call()
	PlayerManager.active_buff_ids.append(buff.id)
	if PlayerManager.player:
		PlayerManager.player.update_damage_values()

func _block_exits() -> void:
	var parent := get_parent()
	var transition_names := [
		"LevelTransition", "LevelTransition2", "LevelTransition3",
		"LevelTransitionSouth", "LevelTransitionSouth2", "LevelTransitionNorth"
	]
	for tname in transition_names:
		if parent.has_node(tname):
			var t := parent.get_node(tname)
			if t is Area2D:
				t.set_deferred("monitoring", false)
				blocked_transitions.append(t)
	_create_barrier(north_exit_pos, north_exit_size)
	_create_barrier(south_exit_pos, south_exit_size)

func _create_barrier(pos: Vector2, sz: Vector2, layer: int = 16) -> void:
	var barrier := StaticBody2D.new()
	barrier.collision_layer = layer
	barrier.collision_mask  = 0
	barrier.position        = pos
	var shape := CollisionShape2D.new()
	var rect  := RectangleShape2D.new()
	rect.size = sz
	shape.shape = rect
	barrier.add_child(shape)
	get_parent().add_child(barrier)
	exit_barriers.append(barrier)

func _unblock_exits() -> void:
	for t in blocked_transitions:
		if is_instance_valid(t):
			t.set_deferred("monitoring", true)
	for b in exit_barriers:
		if is_instance_valid(b):
			b.queue_free()

func _exit_tree() -> void:
	if _music_thread and _music_thread.is_started():
		_music_thread.wait_to_finish()

# ── Undead zone music ──────────────────────────────────────────────────────────

func _generate_music() -> void:
	var stream := _build_undead_track()
	call_deferred("_start_music", stream)

func _start_music(stream: AudioStreamWAV) -> void:
	if is_instance_valid(self):
		AudioManager.play_music(stream)
	_music_thread.wait_to_finish()

func _build_undead_track() -> AudioStreamWAV:
	# 10-second seamless loop — A natural minor, dark ambient
	# Toate frecventele de baza sunt multipli de 0.1 Hz → cicluri exacte in 10s
	var rate    := 22050
	var dur     := 10.0
	var n       := int(rate * dur)
	var samples := PackedFloat32Array()
	samples.resize(n)

	# Melodia — A minor descendent + urcuș: A3 G3 F3 E3 D3 C3 D3 E3
	# Envelope percusiv (exp decay) → ajunge la ~0 la fiecare beat → loop seamless
	var notes  : Array[float] = [220.0, 196.0, 174.6, 164.8, 146.8, 130.8, 146.8, 164.8]
	var nb     := notes.size()           # 8 note
	var blen   := dur / nb               # 1.25s per nota

	for i in n:
		var t  := float(i) / rate
		var s  := 0.0

		# Layer 1 — Drone de baza: A1(55Hz) + armonici + respiratie lenta
		var breath := 0.82 + 0.18 * sin(TAU * 0.1 * t)   # 1 ciclu / 10s
		s += sin(TAU * 55.0  * t) * 0.28 * breath
		s += sin(TAU * 110.0 * t) * 0.12 * breath
		s += sin(TAU * 82.5  * t) * 0.08 * breath
		s += sin(TAU * 27.5  * t) * 0.05 * breath

		# Layer 2 — Cor spectral: 3 frecvente apropiate → efect de "batai" eerie
		# 220 ± 0.4 Hz → 4 batai pe 10s, perfect ciclic
		var swell := 0.5 + 0.5 * sin(TAU * 0.2 * t)      # 2 cicluri / 10s
		s += sin(TAU * 219.6 * t) * 0.09 * swell
		s += sin(TAU * 220.0 * t) * 0.10 * swell
		s += sin(TAU * 220.4 * t) * 0.09 * swell
		s += sin(TAU * 330.0 * t) * 0.04 * swell          # quinta de sus

		# Layer 3 — Melodie: bell-like (atac rapid, decay exponential)
		var bi   := int(t / blen) % nb
		var bt   := fmod(t, blen) / blen                   # 0..1 in beat curent
		var menv := exp(-bt * 3.8)                         # la bt=1: ~0.02, aproape 0
		s += sin(TAU * notes[bi]       * t) * 0.11 * menv
		s += sin(TAU * notes[bi] * 2.0 * t) * 0.04 * menv  # octava — sunet de clopot

		# Layer 4 — Batai de inima: puls la 2.5s (4 pulsuri / 10s, ciclic exact)
		var ht   := fmod(t, 2.5) / 2.5
		if ht < 0.10:
			var henv := pow(1.0 - ht / 0.10, 2.0)
			s += sin(TAU * 50.0 * t) * henv * 0.16
			s += sin(TAU * 75.0 * t) * henv * 0.06

		# Layer 5 — Shimmer inalt: prezenta discreta, aproape subliminala
		var sh := 0.5 + 0.5 * sin(TAU * 0.1 * t)
		s += sin(TAU * 880.0 * t) * 0.012 * sh

		samples[i] = clamp(s, -1.0, 1.0)

	# Pack → 16-bit PCM
	var stream := AudioStreamWAV.new()
	stream.mix_rate  = rate
	stream.stereo    = false
	stream.format    = 1   # FORMAT_16_BIT
	stream.loop_mode = 1   # LOOP_FORWARD — loop perfect de la 0 la n-1
	stream.loop_begin = 0
	stream.loop_end   = n - 1
	var data := PackedByteArray()
	data.resize(n * 2)
	for i in n:
		var v := int(clamp(samples[i] * 32767.0, -32768.0, 32767.0))
		data[i * 2]     = v & 0xFF
		data[i * 2 + 1] = (v >> 8) & 0xFF
	stream.data = data
	return stream
