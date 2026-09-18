extends Node

## AI Controller — register as autoload "AIController".
## Toggle with F2. Reads user://ai_action.json at 20 Hz and injects
## synthetic input events so the Python RL agent can control the player.

const ACTION_FILE   := "user://ai_action.json"
const EPISODE_FILE  := "user://ai_episode.json"
const STATE_FILE    := "user://ai_state.json"
const READ_INTERVAL := 0.05   # 20 Hz

var enabled : bool = false
var episode : int  = 0
# Run5l_v2: offset cosmetic pentru HUD — ep counter intern poate fi 3000+ (pentru analiza
# unica vs 5k/5l), dar HUD afiseaza 1, 2, 3... pentru filmare/screenshot curat.
var _hud_ep_display_offset : int = 0

# Curriculum spawn — Run 5f: 20/30/30/20 cu A2/01 inclus (combat learning depth 4).
# Run5e a stagnat 644 ep cu doar 0.78% A2/01 reach (5 episoade, toate early < ep 150).
# A1/03 → A2/01 conversion = 1.8% — agent nu invata layout/exit nord A1/03.
# Solutia: spawn DIRECT in A2/01 (acelasi truc ca A1/03 in 5e).
var curriculum_enabled : bool = true
const CURRICULUM_SPAWNS : Array = [
	# Run9 FULL-GAME: spawn 100% camera 1 (Area01/02). Agentul joaca TOT jocul de la cap —
	# timer natural de la 0 (porneste cand vorbeste cu NPC), boomerang + buff-uri castigate natural.
	# FULL HP la intrarea in D01/01 (statuie) si D01/04 (boss) — vezi _heal_at_checkpoint().
	["res://Levels/Area01/02.tscn", 1.00],
]
# Pentru fiecare scena de curriculum spawn, "simulam" scena din care a venit AI
# ca filtrul nearest_exit sa NU pointeze inapoi (LT south la spawn = entry, nu exit real).
const CURRICULUM_PREV_SCENE : Dictionary = {
	"res://Levels/Area01/01.tscn": "res://Levels/Area01/02.tscn",
	"res://Levels/Area01/03.tscn": "res://Levels/Area01/01.tscn",
	"res://Levels/Area02/01.tscn": "res://Levels/Area01/03.tscn",
	"res://Levels/Area02/02.tscn": "res://Levels/Area02/01.tscn",  # Run5l: A2/02 spawn forteaza
	"res://Levels/Dungeon01/01.tscn": "res://Levels/Area01/04.tscn",  # statuie
	"res://Levels/Dungeon01/02.tscn": "res://Levels/Dungeon01/01.tscn",  # hub
	"res://Levels/Dungeon01/03.tscn": "res://Levels/Dungeon01/02.tscn",  # wave+cheie
	"res://Levels/Dungeon01/04.tscn": "res://Levels/Dungeon01/03.tscn",  # boss
}
var last_curriculum_scene : String = "res://Levels/Area01/02.tscn"

# Demo recording (F3) — capteaza inputurile umane + state-ul curent pentru BC pretraining
var demo_recording : bool = false
var _demo_file : FileAccess = null
var _demo_timer : float = 0.0
const DEMO_INTERVAL := 0.08          # sync cu state_exporter EXPORT_INTERVAL
const DEMO_DIR := "user://demos/"

var _read_timer      : float = 0.0
var _cur             : Dictionary = {}
var _prev            : Dictionary = {}
var _ui_accept_timer : float = 0.0
const UI_ACCEPT_INTERVAL := 0.3  # apasa Enter la fiecare 0.3s cand e in dialog/shop
var _door_interact_timer : float = 0.0
const DOOR_INTERACT_INTERVAL := 0.3   # Run8b: auto-interact la usa boss cand ai cheia

# Run5l_v8d: stall detection — daca Python NU scrie actiune noua > STALL_TIMEOUT,
# inseamna ca e blocat (PPO checkpoint save dureaza 1.5-3s la fiecare 10k steps).
# In timpul stall-ului, evitam ca AI sa continue ultima comanda (mers cu dash etc).
# Run5l_v8f: 2.0 → 1.5s + check direct pe file_age. Observat spike de 5.5s,
# 2s detection latency = 2s de dash necontrolat. 1.5s e peste precizia mtime 1s + margin 0.5s.
# Run6: 1.5 → 0.5s. Timestamp embedded ("t") permite detectie precisa sub-secunda,
# deci AI se opreste in ~0.5s in loc de 1.5-2.5s cand Python e blocat (checkpoint save).
const STALL_TIMEOUT := 0.5         # seconds (cale timestamp, precisa)
const STALL_TIMEOUT_MTIME := 1.5   # fallback pt actiuni fara "t" (mtime 1s precizie)
var _stalled : bool = false

var _hud_layer       : CanvasLayer = null
var _hud_ep_lbl      : Label = null
var _hud_hp_lbl      : Label = null
var _hud_act_lbl     : Label = null
var _hud_demo_lbl    : Label = null
var _episode_counted : bool  = false
var _healed_d01_this_run  : bool = false   # Run9 full-game: heal o data la intrare D01/01 (statuie)
var _healed_boss_this_run : bool = false   # Run9 full-game: heal o data la intrare D01/04 (boss)


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	# Default time_scale = 1.0 (joc normal pentru om). F2 schimba la 4.0 pentru AI.
	Engine.time_scale = 1.0
	_load_episode()
	_build_hud()
	PlayerManager.run_completed.connect(func(_t): _episode_counted = true; _on_episode_end())
	PlayerManager.run_failed.connect(func(): _episode_counted = true; _on_episode_end())
	# Invuln scurt la fiecare schimbare de scena cand AI e enabled — acopera lag-ul intre
	# scene_loaded si primul action sent de Python (cand AI a transitionat in A1/01 natural
	# si goblinii il omoara inainte sa preia controlul).
	LevelManager.level_loaded.connect(_grant_entry_invuln)
	# Safety net buff kit: aplica kit-ul FIX pe ORICE incarcare a camerei statuii (vezi mai jos).
	LevelManager.level_loaded.connect(_reapply_statue_kit)
	# Run9 full-game: FULL HP la intrarea in camera statuii (D01/01) si la boss (D01/04).
	LevelManager.level_loaded.connect(_heal_at_checkpoint)


func _grant_entry_invuln() -> void:
	if not enabled:
		return
	await get_tree().process_frame
	var p := PlayerManager.player
	if p and is_instance_valid(p) and p.has_method("make_invulnerable"):
		p.make_invulnerable(1.5)


func _reapply_statue_kit() -> void:
	# Garanteaza kit-ul FIX (boomerang + kill_stack + momentum 45% + HP full + timer 22:03)
	# pe FIECARE spawn in camera statuii (Dungeon01/01) cat timp AI e activ — independent de
	# calea _new_run. Bug fix: la reset (pasi/timp epuizat) buff-urile (mai ales momentum) nu
	# se re-aplicau fiabil; aici prindem orice incarcare a scenei. Idempotent: daca momentum
	# e deja activ (kit deja aplicat in episodul curent), sarim ca sa NU resetam HP/timer.
	if not enabled:
		return
	await get_tree().process_frame   # asteapta scena noua + player reparented
	var scene := get_tree().current_scene
	if not scene:
		return
	# Run9: aplica kit-ul DOAR cand AI a SPAWNAT in camera dungeon (curriculum), nu cand ajunge
	# natural acolo din full-game — altfel i-ar reseta timer-ul natural + i-ar da kit gratis.
	if "Dungeon01/" in scene.scene_file_path and "Dungeon01/" in last_curriculum_scene and not PlayerManager.momentum_active:
		# Porneste questul (altfel reward-urile de progres nu fire-eaza) + aplica kit-ul
		# pt camera curenta D01 (statuie/hub/...).
		QuestManager.update_quest("Defeat the Dark Wizard", "", false)
		PlayerHud._give_ai_curriculum_kit(scene.scene_file_path)


func _heal_at_checkpoint() -> void:
	# Run9 (full-game): la PRIMA intrare in camera statuii (D01/01) si la boss (D01/04),
	# da-i FULL HP — un esec de combat din camerele dinainte sa nu condamne fight-ul de boss.
	# Flag-urile se reseteaza la inceputul fiecarui run (in get_curriculum_spawn).
	if not enabled:
		return
	await get_tree().process_frame
	var scene := get_tree().current_scene
	if not scene:
		return
	var sp := scene.scene_file_path
	if "Dungeon01/01" in sp and not _healed_d01_this_run:
		_healed_d01_this_run = true
		_full_heal()
	elif "Dungeon01/04" in sp and not _healed_boss_this_run:
		_healed_boss_this_run = true
		_full_heal()


func _full_heal() -> void:
	var p := PlayerManager.player
	if p and is_instance_valid(p):
		p.hp = p.max_hp
		if p.has_method("update_hp"):
			p.update_hp(0)


func _debug_spawn_statue_room() -> void:
	# F4 (recording/debug, DOAR cu AI off): pune playerul UMAN direct in camera statuii
	# cu kit-ul complet (boomerang + kill_stack + momentum 45% + HP full + timer 22:03),
	# ca sa inregistrezi demo-uri (F3) fara sa joci tot drumul. Repetabil — apesi F4 si esti
	# iar la inceput in camera statuii, gata de un nou solve.
	PlayerManager.reset_run()
	QuestManager.update_quest("Defeat the Dark Wizard", "", false)
	LevelManager.load_new_level("res://Levels/Dungeon01/01.tscn", "", Vector2.ZERO, true)
	await LevelManager.level_loaded
	PlayerHud._give_ai_curriculum_kit("res://Levels/Dungeon01/01.tscn")


func _input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		if event.physical_keycode == KEY_F2:
			enabled = not enabled
			_hud_layer.visible = enabled
			Engine.time_scale = 4.0 if enabled else 1.0
			if enabled:
				_write_blank_action()
				_reapply_statue_kit()   # daca pornim AI direct in camera statuii (F5)
			else:
				_release_all()
		elif event.physical_keycode == KEY_F3:
			_toggle_demo_recording()
		elif event.physical_keycode == KEY_F4 and not enabled:
			_debug_spawn_statue_room()
	if enabled and not (event is InputEventKey and event.physical_keycode == KEY_F2):
		if not (event is InputEventAction):
			get_viewport().set_input_as_handled()


func _process(delta: float) -> void:
	# Demo recording (cand AI e OFF si F3 a pornit recording-ul)
	if demo_recording and not enabled:
		_demo_timer += delta
		if _demo_timer >= DEMO_INTERVAL:
			_demo_timer = 0.0
			_log_demo_step()

	if not enabled:
		return
	_read_timer += delta
	if _read_timer >= READ_INTERVAL:
		_read_timer = 0.0
		_read_action()
	_apply_action()
	_auto_ui_accept(delta)
	_auto_open_door(delta)
	_update_hud()


# ── Demo recording (F3) ───────────────────────────────────────────────────────

func _toggle_demo_recording() -> void:
	if demo_recording:
		if _demo_file:
			_demo_file.close()
			_demo_file = null
		demo_recording = false
		if _hud_demo_lbl:
			_hud_demo_lbl.visible = false
		print("[DEMO] Recording STOPPED")
	else:
		var d := DirAccess.open("user://")
		if d and not d.dir_exists("demos"):
			d.make_dir("demos")
		var path := DEMO_DIR + "session_%d.jsonl" % int(Time.get_unix_time_from_system())
		_demo_file = FileAccess.open(path, FileAccess.WRITE)
		if _demo_file:
			demo_recording = true
			_demo_timer = 0.0
			if _hud_demo_lbl:
				_hud_demo_lbl.visible = true
			print("[DEMO] Recording STARTED: " + path)
		else:
			print("[DEMO] FAILED to open file: " + path)


func _log_demo_step() -> void:
	if not _demo_file:
		return

	# Citeste state-ul curent (scris de exporter la fiecare 0.08s — sync perfect)
	var state_data : Dictionary = {}
	if FileAccess.file_exists(STATE_FILE):
		var f := FileAccess.open(STATE_FILE, FileAccess.READ)
		if f:
			var text := f.get_as_text()
			f.close()
			var parsed = JSON.parse_string(text)
			if parsed is Dictionary:
				state_data = parsed

	# Capteaza inputurile umane curente (acelasi action map ca AI)
	var move_x := 0.0
	var move_y := 0.0
	if Input.is_action_pressed("left"):  move_x -= 1.0
	if Input.is_action_pressed("right"): move_x += 1.0
	if Input.is_action_pressed("up"):    move_y -= 1.0
	if Input.is_action_pressed("down"):  move_y += 1.0

	var action := {
		"move_x":         move_x,
		"move_y":         move_y,
		"attack":         Input.is_action_pressed("attack"),
		"dash":           Input.is_action_pressed("dash"),
		"ability":        Input.is_action_pressed("ability"),
		"interact":       Input.is_action_pressed("interact"),
		"switch_ability": Input.is_action_pressed("switch_ability"),
	}

	var line := {
		"t":      Time.get_unix_time_from_system(),
		"state":  state_data,
		"action": action,
	}
	_demo_file.store_line(JSON.stringify(line))


func _auto_ui_accept(delta: float) -> void:
	if DialogSystem.is_active or ShopMenu.is_active:
		_ui_accept_timer += delta
		if _ui_accept_timer >= UI_ACCEPT_INTERVAL:
			_ui_accept_timer = 0.0
			_press("ui_accept")
	else:
		_ui_accept_timer = 0.0


func _auto_open_door(delta: float) -> void:
	# Run8b: auto-interact la usa boss (locked_door) cand AI e langa ea cu cheia. Usa cere
	# INTERACT (nu se deschide la contact), iar AI invata greu sa apese fix acolo → o deschidem.
	_door_interact_timer += delta
	if _door_interact_timer < DOOR_INTERACT_INTERVAL:
		return
	_door_interact_timer = 0.0
	var pl := PlayerManager.player
	if not pl or not is_instance_valid(pl):
		return
	for door in get_tree().get_nodes_in_group("locked_doors"):
		if not is_instance_valid(door):
			continue
		if "is_open" in door and door.is_open:
			continue
		if door.global_position.distance_to(pl.global_position) > 44.0:
			continue
		if "key_item" in door and door.key_item \
				and PlayerManager.INVENTORY_DATA.get_item_held_quantity(door.key_item) > 0:
			PlayerManager.interact()   # emite interact_pressed → open_door (daca e in interact_area)
			return


# ── action I/O ────────────────────────────────────────────────────────────────

func _read_action() -> void:
	if not FileAccess.file_exists(ACTION_FILE):
		return
	var f := FileAccess.open(ACTION_FILE, FileAccess.READ)
	if not f:
		return
	var data = JSON.parse_string(f.get_as_text())
	f.close()
	# Run6 fix stuck-command: stall detection prin TIMESTAMP embedded ("t" scris de Python),
	# precis sub-secunda. Inlocuieste mtime (1s precizie pe Windows, nesigur cu os.replace atomic),
	# care lasa AI sa fuga cu o comanda apasata 1.5-2.5s in timpul salvarii PPO (checkpoint).
	# Fallback pe mtime daca actiunea nu are "t" (compatibil cu actiuni vechi).
	var now_unix : float = Time.get_unix_time_from_system()
	if data is Dictionary and data.has("t"):
		_stalled = (now_unix - float(data["t"])) > STALL_TIMEOUT
	else:
		_stalled = (now_unix - float(FileAccess.get_modified_time(ACTION_FILE))) > STALL_TIMEOUT_MTIME
	if data is Dictionary and data != _cur:
		_prev = _cur.duplicate()
		_cur  = data


func _apply_action() -> void:
	var reset_now  := bool(_cur.get("reset", false))
	var reset_prev := bool(_prev.get("reset", false))
	if reset_now and not reset_prev:
		_prev = _cur.duplicate()
		_release_all()
		var reason := str(_cur.get("reset_reason", "truncated_global"))
		_log_truncation(reason)
		if not _episode_counted:
			_on_episode_end()
		_episode_counted = false
		PlayerHud._new_run()
		return

	# Run5l_v8d: cand Python e blocat (PPO checkpoint save), force idle pentru movement+dash.
	# Pastram interact/ability state ca sa nu intrerupem dialoguri sau ability charge.
	if _stalled:
		_set_axis("left",  "right", 0.0)
		_set_axis("up",    "down",  0.0)
		_sync_btn("attack",         false)
		_sync_btn("dash",           false)
		_sync_btn("ability",        false)
		_sync_btn("interact",       bool(_cur.get("interact",       false)))
		_sync_btn("switch_ability", false)
	else:
		_set_axis("left",  "right", float(_cur.get("move_x", 0.0)))
		_set_axis("up",    "down",  float(_cur.get("move_y", 0.0)))
		_sync_btn("attack",         bool(_cur.get("attack",         false)))
		_sync_btn("dash",           bool(_cur.get("dash",           false)))
		_sync_btn("interact",       bool(_cur.get("interact",       false)))
		_sync_btn("ability",        bool(_cur.get("ability",        false)))
		_sync_btn("switch_ability", bool(_cur.get("switch_ability", false)))
	_prev = _cur.duplicate()


func _set_axis(neg: String, pos: String, v: float) -> void:
	if v < -0.1:
		_press(neg, -v); _release(pos)
	elif v > 0.1:
		_press(pos,  v); _release(neg)
	else:
		_release(neg); _release(pos)


func _sync_btn(action: String, pressed: bool) -> void:
	var was := bool(_prev.get(action, false))
	if pressed and not was:
		_press(action)
		if action == "interact":
			_press("ui_accept")  # Enter pt dialog/shop
			# Bypass input pipeline — call direct (in Godot 4.6 InputEventAction
			# pe parse_input_event nu propaga consistent la _unhandled_input).
			if PlayerManager.has_method("interact"):
				PlayerManager.interact()
			# FALLBACK BRUTE: scaneaza scene tree pentru DialogInteractions in
			# raza player-ului si trigger direct (in caz ca area_entered nu a fost
			# emis sau conectarea s-a pierdut).
			_try_trigger_nearby_interactables()
	elif not pressed and was:
		_release(action)
		if action == "interact":
			_release("ui_accept")


func _try_trigger_nearby_interactables() -> void:
	var p := PlayerManager.player
	if not p or not is_instance_valid(p):
		return
	# Scaneaza toate NPCurile + chest-urile in raza 60px si fire player_interact.
	for npc in get_tree().get_nodes_in_group("npcs"):
		if not is_instance_valid(npc):
			continue
		if npc.global_position.distance_to(p.global_position) > 60.0:
			continue
		for c in npc.get_children():
			if c is DialogInteraction and c.enabled and c.dialog_items.size() > 0:
				c.player_interact()
				return  # un singur trigger per apel


func _press(action: String, strength: float = 1.0) -> void:
	var ev := InputEventAction.new()
	ev.action   = action
	ev.pressed  = true
	ev.strength = strength
	Input.parse_input_event(ev)


func _release(action: String) -> void:
	var ev := InputEventAction.new()
	ev.action   = action
	ev.pressed  = false
	ev.strength = 0.0
	Input.parse_input_event(ev)


func _release_all() -> void:
	for a in ["left","right","up","down","attack","dash","interact","ability","switch_ability"]:
		_release(a)


func _write_blank_action() -> void:
	var f := FileAccess.open(ACTION_FILE, FileAccess.WRITE)
	if f:
		f.store_string(JSON.stringify({
			"move_x": 0.0, "move_y": 0.0,
			"attack": false, "dash": false,
			"interact": false, "ability": false,
			"switch_ability": false, "reset": false
		}))
		f.close()


# ── episode counter ───────────────────────────────────────────────────────────

func _log_truncation(reason: String) -> void:
	var scene := get_tree().current_scene
	var p := PlayerManager.player
	var entry := {
		"event"        : "episode_end",
		"timestamp"    : Time.get_unix_time_from_system(),
		"outcome"      : reason,
		"time"         : PlayerHud.quest_time,
		"reward_total" : -50.0 if reason == "truncated_room" else 0.0,
		"kills"        : PlayerManager.total_kill_count,
		"damage_taken" : PlayerManager.damage_taken_this_run,
		"scene_path"   : scene.scene_file_path if scene else "",
		"death_x"      : p.global_position.x if p and is_instance_valid(p) else 0.0,
		"death_y"      : p.global_position.y if p and is_instance_valid(p) else 0.0,
		"rooms_visited": [],
	}
	var EVENTS_FILE := "user://ai_events.jsonl"
	var file := FileAccess.open(EVENTS_FILE, FileAccess.READ_WRITE)
	if not file:
		file = FileAccess.open(EVENTS_FILE, FileAccess.WRITE)
	if file:
		file.seek_end()
		file.store_line(JSON.stringify(entry))
		file.close()


func _on_episode_end() -> void:
	episode += 1
	_save_episode()


func _load_episode() -> void:
	if not FileAccess.file_exists(EPISODE_FILE):
		return
	var f := FileAccess.open(EPISODE_FILE, FileAccess.READ)
	if not f:
		return
	var d = JSON.parse_string(f.get_as_text())
	f.close()
	if d is Dictionary and d.has("episode"):
		episode = int(d["episode"])
		# Setam offset astfel incat HUD sa afiseze 1, 2, 3...
		# (run-ul actual incepe la episode + 1, HUD afiseaza 1 la prima rulare)
		_hud_ep_display_offset = episode


func _save_episode() -> void:
	var f := FileAccess.open(EPISODE_FILE, FileAccess.WRITE)
	if f:
		f.store_string(JSON.stringify({"episode": episode}))
		f.close()


# ── Curriculum spawn ──────────────────────────────────────────────────────────

func get_curriculum_spawn() -> String:
	# Returneaza scene_path pentru spawn-ul AI in episodul curent.
	# Default = A1/02 (natural). Daca curriculum_enabled = true, sansa configurata.
	_healed_d01_this_run  = false   # Run9: reset heal-uri checkpoint la inceputul fiecarui run
	_healed_boss_this_run = false
	if not enabled or not curriculum_enabled:
		last_curriculum_scene = "res://Levels/Area01/02.tscn"
		return last_curriculum_scene
	# Baseline mode override — random_baseline.py creeaza user://baseline_mode.flag
	# pentru a forta spawn natural (fara curriculum) si a obtine baseline curat.
	if FileAccess.file_exists("user://baseline_mode.flag"):
		last_curriculum_scene = "res://Levels/Area01/02.tscn"
		return last_curriculum_scene
	var roll := randf()
	var cumulative := 0.0
	for entry in CURRICULUM_SPAWNS:
		cumulative += float(entry[1])
		if roll < cumulative:
			last_curriculum_scene = String(entry[0])
			return last_curriculum_scene
	last_curriculum_scene = "res://Levels/Area01/02.tscn"
	return last_curriculum_scene


# ── HUD ───────────────────────────────────────────────────────────────────────

func _build_hud() -> void:
	_hud_layer         = CanvasLayer.new()
	_hud_layer.layer   = 128
	_hud_layer.visible = false
	add_child(_hud_layer)

	var vbox := VBoxContainer.new()
	vbox.set_anchors_preset(Control.PRESET_TOP_LEFT)
	vbox.offset_left   = 10
	vbox.offset_top    = 8
	vbox.offset_right  = 206
	vbox.offset_bottom = 88
	vbox.add_theme_constant_override("separation", 3)
	_hud_layer.add_child(vbox)

	var mode_lbl := _lbl("◉ AI MODE   [F2 = off]", Color(1.0, 0.3, 0.3, 1), 13)
	_hud_ep_lbl  = _lbl("Episode: 0",              Color(1.0, 1.0, 0.4, 1), 12)
	_hud_hp_lbl  = _lbl("HP: —   Kills: —",        Color(0.7, 1.0, 0.7, 1), 12)
	_hud_act_lbl = _lbl("→ idle",                  Color(0.85,0.85,0.85,1), 11)
	vbox.add_child(mode_lbl)
	vbox.add_child(_hud_ep_lbl)
	vbox.add_child(_hud_hp_lbl)
	vbox.add_child(_hud_act_lbl)

	# Demo recording label — layer separat, mereu vizibil cand demo_recording=true
	var demo_layer := CanvasLayer.new()
	demo_layer.layer = 128
	add_child(demo_layer)
	_hud_demo_lbl = _lbl("● DEMO REC [F3]", Color(1.0, 0.2, 0.2, 1), 14)
	_hud_demo_lbl.set_anchors_preset(Control.PRESET_TOP_RIGHT)
	_hud_demo_lbl.offset_left   = -160
	_hud_demo_lbl.offset_top    = 8
	_hud_demo_lbl.offset_right  = -10
	_hud_demo_lbl.offset_bottom = 32
	_hud_demo_lbl.visible = false
	demo_layer.add_child(_hud_demo_lbl)


func _lbl(text: String, color: Color, size: int) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_color_override("font_color",         color)
	l.add_theme_color_override("font_outline_color", Color.BLACK)
	l.add_theme_constant_override("outline_size",    2)
	l.add_theme_font_size_override("font_size",      size)
	return l


func _update_hud() -> void:
	if not _hud_ep_lbl:
		return
	# Run9: contorizeaza RUN-urile din sesiunea curenta de la 0 (era hardcodat "4" pt filmare).
	# _hud_ep_display_offset = valoarea episode la pornirea sesiunii → afiseaza 0,1,2,... live.
	_hud_ep_lbl.text = "Episode: %d" % (episode - _hud_ep_display_offset)

	var p := PlayerManager.player
	if p:
		_hud_hp_lbl.text = "HP: %d/%d   Kills: %d" % [p.hp, p.max_hp, PlayerManager.total_kill_count]

	var parts : Array[String] = []
	var mx := float(_cur.get("move_x", 0.0))
	var my := float(_cur.get("move_y", 0.0))
	if absf(mx) > 0.1 or absf(my) > 0.1:
		parts.append("move(%.1f,%.1f)" % [mx, my])
	for btn in ["attack", "dash", "interact", "ability"]:
		if bool(_cur.get(btn, false)):
			parts.append(btn)
	_hud_act_lbl.text = "→ " + (", ".join(parts) if parts.size() > 0 else "idle")
