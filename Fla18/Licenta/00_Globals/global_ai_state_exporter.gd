extends Node

## Exports game state to user://ai_state.json every EXPORT_INTERVAL seconds.
## An external Python/RL script can poll this file to read the current game state.
## State file path on Windows: %APPDATA%\Godot\app_userdata\<project_name>\ai_state.json
##
## Reward design (time-based, lower time = higher reward):
##   - Per step while run is active: reward = -EXPORT_INTERVAL  (~-0.25/step)
##   - Win  (boss dead):             reward = +1000  + time_bonus + hp_bonus
##   - Fail (player dead):           reward = -500   + done = true

const STATE_FILE      := "user://ai_state.json"
const EVENTS_FILE     := "user://ai_events.jsonl"
const EXPORT_INTERVAL := 0.08

var _timer          : float = 0.0
var _gem_item       : ItemData
var _pending_reward : float = 0.0
var _done           : bool  = false

# Tracking per-episode (resetat la inceput de run)
var _rooms_visited      : Array[String] = []
var _prev_scene_path    : String = ""
var _prev_buff_ids      : Array  = []
var _boss_reached       : bool   = false
var _prev_boss_phase    : int    = -1     # Run5l_v3: tracker pentru reward per phase trecuta
var _prev_boss_hp       : int    = -1     # Run8b: tracker pt reward DENS damage boss
var _prev_boss_approach_pos : Vector2 = Vector2.ZERO   # Run8b: pull spre boss (miscare agent)
var _prev_cov_approach_pos  : Vector2 = Vector2.ZERO   # Run8b: pull spre zona safe (coverage attack)
var _prev_kill_count    : int    = 0
var _min_boss_hp_this_run : int  = -1   # -1 = nu a ajuns la boss
var _prev_exit_dist        : float  = -1.0
var _prev_door_dist        : float  = -1.0   # Run8b: dist la usa boss (pull cand ai cheia)
var _prev_npc_dist         : float  = -1.0
var _prev_enemy_dist       : float  = -1.0
var _prev_player_pos       : Vector2 = Vector2.ZERO
var _still_steps           : int     = 0
var _prev_total_enemy_hp   : int     = -1
var _prev_player_hp        : int     = -1
var _trigger_line_crossed  : bool    = false
# Run5f: waypoints A2/01 (sud, spawn y=70 → exit y=1105, pod ingust pe la mijloc)
var _waypoint_a2_y300_passed  : bool = false  # 25% sud progres
var _waypoint_a2_y600_passed  : bool = false  # 50% sud — intrare pod
var _waypoint_a2_y900_passed  : bool = false  # 75% sud — iesire pod
var _waypoint_a2_y1050_passed : bool = false  # 95% sud — aproape exit
var _prev_south_y             : float = -INF  # tracker progres continuu sud A2/01
var _prev_a201_pos            : Vector2 = Vector2.ZERO  # Run5h: anti-exploit survival bonus
var _prev_a202_pos            : Vector2 = Vector2.ZERO  # Run5l: survival bonus A2/02
var _prev_a202_exit_dist      : float   = -1.0          # Run5l_v8d: A2/02 exit magnet post-puzzle
var _prev_lever_dist          : float   = -1.0          # Run5l: proximity reward lever
var _prev_statue_dist         : float   = -1.0          # Run5l_v3: proximity AI→statue (D01/01)
var _prev_statue_to_plate     : float   = -1.0          # Run5l_v3: statue→plate distance
var _prev_statue_pos          : Vector2 = Vector2.ZERO  # Run5l_v3: tracker statue position
var _statue_push_active       : bool    = false         # Run8: AI lipit de statuie (skip camping penalty)
var _prev_pushspot_dist       : float   = -1.0          # Run8b: dist la pozitia de impins (in spatele statuii)
var _shop_purchase_step       : int = -1  # Run5k: tracker pentru exit shop reward
var _step_counter             : int = 0   # Run5k: contor pasi global pentru shop exit timing
var _shop_exit_rewarded       : bool = false  # Run5k: evita double reward exit shop
var _prev_chest_dist       : float   = -1.0
var _prev_north_y          : float   = INF   # cea mai inalta pozitie (y minim) in Area01/03
# NOU run 4d: waypoints A1/03 + post-clear/post-buff lingering penalty + partial clear
var _waypoint_y0_passed    : bool    = false   # B6: trecut y<=0 in A1/03
var _waypoint_y200_passed  : bool    = false   # B6: trecut y<=-200 in A1/03
var _waypoint_y350_passed  : bool    = false   # B6b: trecut y<=-350 in A1/03 (gap intre y=-200 si y=-490)
var _partial_clear_rewarded: bool    = false   # alt-C2: bonus la 50% kills_in_room
var _room_cleared_in_scene : String  = ""     # B9: scena unde s-a curatat ultima data
var _buff_picked_in_scene  : String  = ""     # B8: scena unde s-a luat buff ultima data


func _ready() -> void:
	_gem_item = load("res://Items/gem.tres")
	PlayerManager.run_completed.connect( func(t): _on_win(t) )
	PlayerManager.run_failed.connect(    func():  _on_fail() )
	QuestManager.quest_updated.connect(  func(q):
		if q.title == "Defeat the Dark Wizard" and not q.is_complete:
			_reset_episode_tracking()
			_pending_reward += 100.0   # BOOST 50 → 100 — reward MARE pentru luat quest
			var spawn_scene := ""
			if AIController.enabled:
				spawn_scene = AIController.last_curriculum_scene
			_log_event("run_started", {"spawn_scene": spawn_scene})
	)
	LevelManager.level_loaded.connect(_on_level_loaded)
	ShopMenu.purchase_made.connect(_on_shop_purchase)


func _on_level_loaded() -> void:
	await get_tree().process_frame
	# Pressure plate (puzzle statuie Dungeon01/01)
	for node in get_tree().get_nodes_in_group("pressure_plates"):
		if not node.activated.is_connected(_on_pressure_plate_activated):
			node.activated.connect(_on_pressure_plate_activated)
	# Lever managers (camera levere Area02/02)
	for node in get_tree().get_nodes_in_group("lever_managers"):
		if not node.lever_count_changed.is_connected(_on_lever_activated):
			node.lever_count_changed.connect(_on_lever_activated)
	# Kill chest managers (Area01/01 x4, Area02/01 x15)
	for node in get_tree().get_nodes_in_group("kill_chest_managers"):
		if not node.room_cleared.is_connected(_on_room_cleared):
			node.room_cleared.connect(_on_room_cleared)
		if node.has_signal("item_picked") and not node.item_picked.is_connected(_on_ability_item_picked):
			node.item_picked.connect(_on_ability_item_picked)
	# Usa incuiata cu cheie (boss door Dungeon01/03→04)
	for node in get_tree().get_nodes_in_group("locked_doors"):
		if not node.door_opened.is_connected(_on_boss_door_opened):
			node.door_opened.connect(_on_boss_door_opened)
	# Item dropper (cheia din Dungeon01/03 dupa wave-uri)
	for node in get_tree().get_nodes_in_group("item_droppers"):
		if not node.drop_collected.is_connected(_on_key_collected):
			node.drop_collected.connect(_on_key_collected)
	# Shopkeeper
	for node in get_tree().get_nodes_in_group("shopkeepers"):
		if not node.shop_entered.is_connected(_on_shop_entered):
			node.shop_entered.connect(_on_shop_entered)


func _on_pressure_plate_activated() -> void:
	# Run8 (filmare D01): puzzle-ul statuii e GATE-ul intregului dungeon (deschide BarredDoor →
	# exit nord spre D01/02). Cu spawn 100% in D01/01, asta E faza principala, nu prematura.
	# 40 era prea mic (puzzle_solved=1 in tot istoricul) → boost la 500 ca semnal terminal puternic.
	_pending_reward += 500.0
	_log_event("puzzle_solved", {"type": "pressure_plate"})


func _on_lever_activated(current: int, total: int) -> void:
	# Run5l: lever reward boost — gradient progresiv pentru a invata interactiunea
	# Lever 1: +75, Lever 2: +125, Lever 3: +200, Lever 4 (puzzle complet): +500 bonus.
	# Total max: 75 + 125 + 200 + 300 + 500 = 1200 reward pentru a activa toate leverele.
	var per_lever_reward := 75.0 + float(current - 1) * 50.0  # 75, 125, 175, 225...
	_pending_reward += per_lever_reward
	if current >= total and total > 0:
		_pending_reward += 500.0  # bonus puzzle solved
		_log_event("levers_all_activated", {"total": total, "bonus": 500})
		# Run5l_v8d: seteaza _room_cleared_in_scene pentru A2/02 dupa toate leverele.
		# Asta activeaza chest magnet BOOST (delta 0.2, lipit 1.5) spre chest-urile noi spawned.
		# Fara asta, AI primea doar magnet slab (0.05/0.5) si nu gasea chest-urile.
		var scene := get_tree().current_scene
		_room_cleared_in_scene = scene.scene_file_path if scene else ""
	_log_event("lever_activated", {"current": current, "total": total, "reward": per_lever_reward})


func _on_room_cleared() -> void:
	# Run5k: room_cleared boost 50 → 300 (era prea mic vs combat reward)
	# In A2/01 (kill_target=10) acest reward semnaleaza "ai terminat wave, mergi la exit"
	_pending_reward += 300.0
	var p := PlayerManager.player
	if p and is_instance_valid(p) and p.hp > 0:
		_pending_reward += float(p.hp) * 5.0
	var scene := get_tree().current_scene
	_room_cleared_in_scene = scene.scene_file_path if scene else ""
	_log_event("room_cleared", {})


func _on_boss_door_opened() -> void:
	# Run5l_v4: REVERT 1500 → 100 (catastrophic forgetting Q4 — boosts dungeon distrageau policy)
	_pending_reward += 100.0
	# Run8b: dupa ce usa s-a deschis, marcheaza milestone → boost pull spre exit (spre D01/04)
	var scene := get_tree().current_scene
	_room_cleared_in_scene = scene.scene_file_path if scene else ""
	_log_event("boss_door_opened", {})


func _on_key_collected() -> void:
	# Run5l_v4: REVERT 500 → 60
	_pending_reward += 60.0
	_log_event("key_collected", {})


func _on_shop_entered() -> void:
	_pending_reward += 20.0
	_log_event("shop_entered", {})


func _on_shop_purchase(item_name: String) -> void:
	_pending_reward += 100.0   # Run5j: +25 → +100 (recompensa cumparatura)
	_log_event("shop_purchase", {"item_name": item_name})
	# Run5k: marca step-ul cumparaturii pentru a recompensa exit rapid
	_shop_purchase_step = _step_counter
	_shop_exit_rewarded = false


func _on_ability_item_picked() -> void:
	_pending_reward += 30.0
	_log_event("ability_item_picked", {})


func _process(delta: float) -> void:
	# Penalitate de timp cat ruleaza run-ul
	if PlayerHud.quest_timer_active:
		_pending_reward -= delta

	_timer += delta
	if _timer >= EXPORT_INTERVAL:
		_timer = 0.0
		_track_scene_change()
		_track_buff_picks()
		_export_state()


# ── tracking scene si buffs ────────────────────────────────────────────────────

const _ROOM_ENTRY_REWARDS : Dictionary = {
	"res://Levels/Area01/01.tscn":      25.0,   # camera goblini (spawn frecvent, reward mic)
	"res://Levels/Area01/03.tscn":     200.0,   # Run5e: 30→200 — agent ajunge aici < 2% din ep
	"res://Levels/Area02/01.tscn":     500.0,   # Run5e: 35→500 — agent NU mai ajunge aici deloc
	"res://Levels/Area02/02.tscn":    3000.0,   # Run5g: 1000→3000 — lever room (reward MARE pt tranzitie pod completa)
	"res://Levels/Area01/04.tscn":     400.0,   # Run5e: 25→400 — dungeon entry
	"res://Levels/Dungeon01/02.tscn":  800.0,   # Run5e: 20→800 — hub
	"res://Levels/Dungeon01/03.tscn": 1500.0,   # Run5e: 25→1500 — wave manager (cheia)
	"res://Levels/Dungeon01/04.tscn": 3000.0,   # Run5e: 50→3000 — boss room
}

func _track_scene_change() -> void:
	var scene := get_tree().current_scene
	if not scene:
		return
	var path : String = scene.scene_file_path
	if path == "" or path == _prev_scene_path:
		return
	_prev_scene_path = path
	# Reward la prima vizita a camerelor cheie
	if not _rooms_visited.has(path):
		_rooms_visited.append(path)
		# Run5l FIX: skip entry reward daca scena curenta e cea de spawn curriculum
		# (altfel curriculum A1/03/A2/02 ar da reward 200/3000 gratis la fiecare ep cu spawn forced).
		var is_curriculum_spawn := AIController.enabled \
			and AIController.curriculum_enabled \
			and path == AIController.last_curriculum_scene \
			and _rooms_visited.size() == 1
		if _ROOM_ENTRY_REWARDS.has(path) and not is_curriculum_spawn:
			_pending_reward += _ROOM_ENTRY_REWARDS[path]
			_log_event("milestone_room", {"scene_path": path, "reward": _ROOM_ENTRY_REWARDS[path]})
	if "Dungeon01/04" in path:
		_boss_reached = true
	_log_event("room_entered", {"scene_path": path})


func _track_buff_picks() -> void:
	var cur_buffs : Array = PlayerManager.active_buff_ids.duplicate()
	var scene := get_tree().current_scene
	var scene_path : String = scene.scene_file_path if scene else ""
	for buff_id in cur_buffs:
		if not _prev_buff_ids.has(buff_id):
			var buff_reward := 60.0
			# Run5l_v7c: PRIO bloodlust (+1 HP/kill) — ajuta supravietuire camera A2/01 + dungeon
			if buff_id == "bloodlust":
				buff_reward += 300.0   # total +360 vs +60 default = 6x reward, AI prefera
			_pending_reward += buff_reward
			_buff_picked_in_scene = scene_path
			_log_event("buff_picked", {
				"buff_id"    : buff_id,
				"scene_path" : scene_path,
				"timer"      : PlayerHud.quest_time,
				"reward"     : buff_reward,
			})
	_prev_buff_ids = cur_buffs


func _reset_episode_tracking() -> void:
	_rooms_visited        = []
	_prev_scene_path      = ""
	_prev_buff_ids        = []
	_boss_reached         = false
	_prev_boss_phase      = -1
	_prev_boss_hp         = -1
	_prev_boss_approach_pos = Vector2.ZERO
	_prev_cov_approach_pos = Vector2.ZERO
	_prev_kill_count      = PlayerManager.total_kill_count
	_min_boss_hp_this_run = -1
	_prev_exit_dist        = -1.0
	_prev_door_dist        = -1.0
	_prev_npc_dist         = -1.0
	_prev_enemy_dist       = -1.0
	_prev_player_pos       = Vector2.ZERO
	_still_steps           = 0
	_prev_total_enemy_hp   = -1
	_prev_player_hp        = -1
	_trigger_line_crossed  = false
	_prev_chest_dist       = -1.0
	_prev_north_y          = INF
	# NOU run 4d: reset flags noi
	_waypoint_y0_passed    = false
	_waypoint_y200_passed  = false
	_waypoint_y350_passed  = false
	_waypoint_a2_y300_passed  = false
	_waypoint_a2_y600_passed  = false
	_waypoint_a2_y900_passed  = false
	_waypoint_a2_y1050_passed = false
	_prev_south_y             = -INF
	_prev_a201_pos            = Vector2.ZERO  # Run5h: reset anti-exploit tracker la ep nou
	_prev_a202_pos            = Vector2.ZERO  # Run5l
	_prev_a202_exit_dist      = -1.0          # Run5l_v8d
	_prev_lever_dist          = -1.0          # Run5l
	_prev_statue_dist         = -1.0          # Run5l_v3
	_prev_statue_to_plate     = -1.0          # Run5l_v3
	_prev_statue_pos          = Vector2.ZERO  # Run5l_v3
	_partial_clear_rewarded = false
	_room_cleared_in_scene = ""
	_buff_picked_in_scene  = ""


# ── win / fail ─────────────────────────────────────────────────────────────────

func _on_win(time: float) -> void:
	var p := PlayerManager.player
	var hp_bonus := float(p.hp) if p and is_instance_valid(p) else 0.0
	var time_bonus := 0.0
	if   time < 180.0:  time_bonus = 500.0   # sub 3 min
	elif time < 300.0:  time_bonus = 300.0   # 3-5 min
	elif time < 480.0:  time_bonus = 150.0   # 5-8 min
	elif time < 720.0:  time_bonus =  50.0   # 8-12 min
	# Run5l_v4: REVERT win 5000 → 1000 (semnal prea departe, distraseaza policy)
	_pending_reward += 1000.0 + time_bonus + hp_bonus
	_done = true
	_export_state()
	_log_episode("win", time)
	_pending_reward = 0.0
	_done = false


func _on_fail() -> void:
	_pending_reward -= 100.0
	_done = true
	_export_state()
	_log_episode("fail", PlayerHud.quest_time)
	_pending_reward = 0.0
	_done = false


# ── export state (pentru Python env) ──────────────────────────────────────────

func _export_state() -> void:
	if not PlayerManager.player or not is_instance_valid(PlayerManager.player):
		return

	_step_counter += 1
	var p   := PlayerManager.player
	var pm  := PlayerManager
	var scene := get_tree().current_scene

	# Run5k: EXIT SHOP REWARD — daca AI iese rapid din shop dupa cumparatura, BONUS mare
	if _shop_purchase_step >= 0 and not _shop_exit_rewarded:
		var sp_curr : String = scene.scene_file_path if scene else ""
		if "02_shop" not in sp_curr:
			# AI a iesit din shop
			var delay = _step_counter - _shop_purchase_step
			if delay <= 30:
				_pending_reward += 500.0  # exit foarte rapid — reward mare
				_log_event("shop_exit_fast", {"delay_steps": delay})
			elif delay <= 100:
				_pending_reward += 200.0  # exit moderat
				_log_event("shop_exit_med", {"delay_steps": delay})
			# else: nu reward, dar nici penalty extra (anti-farming time deja in survival)
			_shop_exit_rewarded = true
			_shop_purchase_step = -1

	var enemies_data : Array = []
	for e in get_tree().get_nodes_in_group("enemies"):
		if not is_instance_valid(e):
			continue
		var script_path : String = e.get_script().resource_path if e.get_script() else ""
		var enemy_type  : String = script_path.get_file().get_basename() if script_path != "" else e.name
		enemies_data.append({
			"type" : enemy_type,
			"x"    : e.global_position.x,
			"y"    : e.global_position.y,
			"hp"   : e.hp,
		})

	var boss_hp_val : int = -1
	var boss_pos := {"x": 0.0, "y": 0.0, "found": false}
	var boss_phase : int = 0   # 0=intact, 1=below 75%, 2=phase2 (≤50%), 3=phase3 (≤25%)
	for node in get_tree().get_nodes_in_group("boss"):
		if is_instance_valid(node):
			boss_hp_val = node.hp
			# Boss are boss_node ca proxy vizual al pozitiei
			var bn = node.get("boss_node") if "boss_node" in node else null
			if bn and is_instance_valid(bn):
				boss_pos = {"x": bn.global_position.x, "y": bn.global_position.y, "found": true}
			else:
				boss_pos = {"x": node.global_position.x, "y": node.global_position.y, "found": true}
			# Faza derivata din HP
			var hp_ratio_b := float(node.hp) / float(node.max_hp) if "max_hp" in node and node.max_hp > 0 else 1.0
			if hp_ratio_b <= 0.25:
				boss_phase = 3
			elif hp_ratio_b <= 0.5:
				boss_phase = 2
			elif hp_ratio_b <= 0.75:
				boss_phase = 1
			else:
				boss_phase = 0
			if _min_boss_hp_this_run < 0 or node.hp < _min_boss_hp_this_run:
				_min_boss_hp_this_run = node.hp
			# Run8b: reward DENS ca AI sa invete sa bata boss-ul. Boss NU e in "enemies", deci
			# fara asta primea DOAR +1000 la final = prea rar pt 500 HP (gradient zero).
			# Damage +2/HP (×500 = +1000 dens) + bonus +100 la fiecare prag de faza (75/50/25%).
			if _prev_boss_hp >= 0 and node.hp < _prev_boss_hp:
				_pending_reward += float(_prev_boss_hp - node.hp) * 2.0
			_prev_boss_hp = node.hp
			if _prev_boss_phase >= 0 and boss_phase > _prev_boss_phase:
				_pending_reward += 100.0
			_prev_boss_phase = boss_phase

	var all_chests : Array = []
	for node in get_tree().get_nodes_in_group("buff_chest_managers"):
		all_chests.append_array(node.get_chest_data())

	var orbs_data : Array = []
	for orb in get_tree().get_nodes_in_group("boss_projectiles"):
		if is_instance_valid(orb):
			# Run7: viteza (directie*speed) pt dodge — agentul vede incotro vine proiectilul
			var ovx := 0.0; var ovy := 0.0
			if "direction" in orb and "speed" in orb:
				ovx = orb.direction.x * orb.speed; ovy = orb.direction.y * orb.speed
			orbs_data.append({"x": orb.global_position.x, "y": orb.global_position.y, "vx": ovx, "vy": ovy})

	# Run8b: beamuri ACTIVE ale boss-ului ca pseudo-orbs (punctul de pe linia beamului cel mai
	# apropiat de player) → agentul le vede in obs-ul de orbs si le poate dodge-ui. NU schimba
	# dim obs (pastreaza modelul 680k compatibil). Orizontal (rot~0) = linia y; vertical = linia x.
	for beam in get_tree().get_nodes_in_group("boss_beams"):
		if not is_instance_valid(beam) or not ("is_firing" in beam) or not beam.is_firing:
			continue
		var bx : float; var by : float
		if absf(beam.rotation) < 0.1:
			bx = p.global_position.x; by = beam.global_position.y   # beam orizontal
		else:
			bx = beam.global_position.x; by = p.global_position.y   # beam vertical
		orbs_data.append({"x": bx, "y": by, "vx": 0.0, "vy": 0.0})

	# Cel mai apropiat exit (LevelTransition) — exclude intrarea (usa pe care a venit)
	# si exclude LT-urile blocate (monitoring=false) — ex: in A1/01 goblini vii sau chest neschis
	var nearest_exit := {"x": 0.0, "y": 0.0, "found": false}
	var min_dist := INF
	var prev_path := LevelManager.previous_scene_path
	for lt in get_tree().get_nodes_in_group("level_transitions"):
		if not is_instance_valid(lt):
			continue
		if lt.level == null or lt.level == "":
			continue
		# Filtru NOU: ignora LT-urile cu monitoring=false (blocate de chest manager)
		# Fara asta AI primea reward sa se duca spre LT2 in A1/01 chiar daca era blocat
		# de bariera nord + monitoring oprit -> confuzie de policy (push in perete).
		if "monitoring" in lt and not lt.monitoring:
			continue
		if prev_path != "":
			var lt_path : String = lt.level
			if lt_path.begins_with("uid://"):
				var uid_int := ResourceUID.text_to_id(lt_path)
				if uid_int != ResourceUID.INVALID_ID:
					lt_path = ResourceUID.get_id_path(uid_int)
			if lt_path == prev_path:
				continue
		var d := p.global_position.distance_to(lt.global_position)
		if d < min_dist:
			min_dist = d
			nearest_exit = {"x": lt.global_position.x, "y": lt.global_position.y, "found": true}

	# Abilitatea activa curenta
	var ability_idx := 0
	if p.has_node("Abilities"):
		ability_idx = p.get_node("Abilities").selected_ability

	# Quest started
	var quest_started := QuestManager.get_quest_index_by_title("Defeat the Dark Wizard") != -1

	# Pozitia NPC-ului (doar cand quest-ul nu e luat inca)
	var npc_pos := {"x": 0.0, "y": 0.0, "found": false}
	if not quest_started:
		var min_npc_dist := INF
		for npc in get_tree().get_nodes_in_group("npcs"):
			if is_instance_valid(npc):
				var d := p.global_position.distance_to(npc.global_position)
				if d < min_npc_dist:
					min_npc_dist = d
					npc_pos = {"x": npc.global_position.x, "y": npc.global_position.y, "found": true}

	# Charge attack progress
	var charge_progress := 0.0
	if p.has_node("StateMachine"):
		var sm := p.get_node("StateMachine")
		if sm.current_state is State_ChargeAttack:
			charge_progress = 1.0 - clampf(sm.current_state.timer / sm.current_state.charge_duration, 0.0, 1.0)

	# Progres levere
	var levers_current := 0
	var levers_total   := 0
	for lm in get_tree().get_nodes_in_group("lever_managers"):
		if is_instance_valid(lm):
			levers_current = lm._activated_count
			levers_total   = lm._lever_nodes.size()
			break

	# Statui si placi de presiune (puzzle dungeon)
	var statues_data : Array = []
	for s in get_tree().get_nodes_in_group("pushable_statues"):
		if is_instance_valid(s):
			statues_data.append({"x": s.global_position.x, "y": s.global_position.y, "on_target": s.on_target})
	var plates_data : Array = []
	for pl in get_tree().get_nodes_in_group("pressure_plates"):
		if is_instance_valid(pl):
			plates_data.append({"x": pl.global_position.x, "y": pl.global_position.y, "active": pl.is_active})

	# Top 3 traps (spike/saw/arrow) — sortate dupa distanta
	var all_traps_data : Array = []
	for trap in get_tree().get_nodes_in_group("traps"):
		if not is_instance_valid(trap):
			continue
		var trap_active := true
		if "is_active" in trap:
			trap_active = trap.is_active
		all_traps_data.append({
			"x": trap.global_position.x,
			"y": trap.global_position.y,
			"is_active": trap_active,
			"_dist": p.global_position.distance_to(trap.global_position),
		})
	all_traps_data.sort_custom(func(a, b): return a["_dist"] < b["_dist"])
	var top_traps : Array = all_traps_data.slice(0, 3)
	var nearest_trap := {"x": 0.0, "y": 0.0, "found": false, "is_active": false}
	var min_trap_dist : float = INF
	if not top_traps.is_empty():
		var t0 = top_traps[0]
		min_trap_dist = t0["_dist"]
		nearest_trap = {"x": t0["x"], "y": t0["y"], "found": true, "is_active": t0["is_active"]}

	# Lich projectiles — proiectile flame periculoase
	var lich_projs : Array = []
	for proj in get_tree().get_nodes_in_group("lich_projectiles"):
		if not is_instance_valid(proj):
			continue
		var lvx := 0.0; var lvy := 0.0
		if "direction" in proj and "speed" in proj:
			lvx = proj.direction.x * proj.speed; lvy = proj.direction.y * proj.speed
		lich_projs.append({
			"x": proj.global_position.x,
			"y": proj.global_position.y,
			"vx": lvx, "vy": lvy,
			"_dist": p.global_position.distance_to(proj.global_position),
		})
	lich_projs.sort_custom(func(a, b): return a["_dist"] < b["_dist"])
	var top_lich_projs : Array = lich_projs.slice(0, 3)

	# Trap arrows — sagetile zburatoare din arrow traps
	var trap_arrows : Array = []
	for arr in get_tree().get_nodes_in_group("trap_arrows"):
		if not is_instance_valid(arr):
			continue
		var avx := 0.0; var avy := 0.0
		if "direction" in arr and "speed" in arr:
			avx = arr.direction.x * arr.speed; avy = arr.direction.y * arr.speed
		trap_arrows.append({
			"x": arr.global_position.x,
			"y": arr.global_position.y,
			"vx": avx, "vy": avy,
			"_dist": p.global_position.distance_to(arr.global_position),
		})
	trap_arrows.sort_custom(func(a, b): return a["_dist"] < b["_dist"])
	var top_trap_arrows : Array = trap_arrows.slice(0, 3)

	# Item chests (goblin room) — ability deterministic per chest
	var item_chests_data : Array = []
	for mgr in get_tree().get_nodes_in_group("item_chest_managers"):
		if is_instance_valid(mgr) and mgr.has_method("get_item_chest_data"):
			item_chests_data.append_array(mgr.get_item_chest_data())

	# Levers Area02/02 — toate 4 levere (pozitie + status)
	var levers_data : Array = []
	for lm in get_tree().get_nodes_in_group("lever_managers"):
		if is_instance_valid(lm) and "_lever_nodes" in lm:
			for lv in lm._lever_nodes:
				if is_instance_valid(lv):
					levers_data.append({
						"x": lv.global_position.x,
						"y": lv.global_position.y,
						"is_activated": lv.is_activated,
					})
			break

	# Locked door (Dungeon01/02) — pozitie + has_key flag
	var locked_door := {"x": 0.0, "y": 0.0, "found": false, "has_key": false}
	for door in get_tree().get_nodes_in_group("locked_doors"):
		if not is_instance_valid(door) or door.is_open:
			continue
		var has_key := false
		if "key_item" in door and door.key_item:
			has_key = PlayerManager.INVENTORY_DATA.get_item_held_quantity(door.key_item) > 0
		locked_door = {
			"x": door.global_position.x,
			"y": door.global_position.y,
			"found": true,
			"has_key": has_key,
		}
		break

	# Pickups pe jos (gems, bombs, arrows) — top 3 cele mai apropiate
	var pickups : Array = []
	for pk in get_tree().get_nodes_in_group("pickups"):
		if not is_instance_valid(pk) or not pk.visible:
			continue
		var pickup_type := 0   # default: gem/altceva
		if "item_data" in pk and pk.item_data:
			var iname : String = pk.item_data.name if "name" in pk.item_data else ""
			if iname == "Arrow":
				pickup_type = 1
			elif iname == "Bomb":
				pickup_type = 2
		pickups.append({
			"x": pk.global_position.x,
			"y": pk.global_position.y,
			"type": pickup_type,
			"_dist": p.global_position.distance_to(pk.global_position),
		})
	pickups.sort_custom(func(a, b): return a["_dist"] < b["_dist"])
	var top_pickups : Array = pickups.slice(0, 3)

	# Item droppers (Dungeon01/03 cheia) — pozitie cand cheia a fost spawn-ata
	var item_drop := {"x": 0.0, "y": 0.0, "found": false}
	for dropper in get_tree().get_nodes_in_group("item_droppers"):
		if not is_instance_valid(dropper):
			continue
		# Cauta ItemPickup-ul spawnat in interior (cheia ridicabila)
		for child in dropper.get_children():
			if child.has_method("get_class") and "ItemPickup" in child.get_class():
				item_drop = {"x": child.global_position.x, "y": child.global_position.y, "found": true}
				break
		# Fallback: pozitia dropper-ului (chiar daca cheia n-a cazut inca)
		if not item_drop.get("found", false) and "has_dropped" in dropper:
			item_drop = {
				"x": dropper.global_position.x,
				"y": dropper.global_position.y,
				"found": dropper.has_dropped,
			}
		break

	# Wave info pentru camera cu valuri (Area02/01, Dungeon01/03)
	var current_wave := 0
	var kills_in_room := 0
	var kill_target := 0
	for mgr in get_tree().get_nodes_in_group("kill_chest_managers"):
		if not is_instance_valid(mgr):
			continue
		if "current_wave" in mgr:
			current_wave = mgr.current_wave
		if "initial_kill_count" in mgr and "kill_target" in mgr:
			kills_in_room = pm.total_kill_count - mgr.initial_kill_count
			kill_target = mgr.kill_target
			break

	var state := {
		"reward"          : _pending_reward,
		"done"            : _done,
		"run_active"      : PlayerHud.quest_timer_active,
		"timer"           : PlayerHud.quest_time,
		"scene"           : scene.name if scene else "",
		"scene_path"      : scene.scene_file_path if scene else "",
		"available_chests"      : all_chests,
		"chests_active"         : not all_chests.is_empty(),
		"coverage_attack_active": PlayerManager.coverage_attack_active,
		"coverage_safe"         : PlayerManager.coverage_safe,
		"coverage_safe_pos"     : {"x": PlayerManager.coverage_safe_pos.x, "y": PlayerManager.coverage_safe_pos.y},
		"boss_orbs"             : orbs_data,
		"boss_hp"               : boss_hp_val,
		"player" : {
			"hp"       : p.hp,
			"max_hp"   : p.max_hp,
			"x"        : p.global_position.x,
			"y"        : p.global_position.y,
			"bombs"    : p.bomb_count,
			"arrows"   : p.arrow_count,
			"level"    : p.level,
			"attack"   : p.attack,
			"facing_x" : p.cardinal_direction.x,
			"facing_y" : p.cardinal_direction.y,
		},
		"buffs" : {
			"damage_multiplier"    : pm.damage_multiplier,
			"charge_multiplier"    : pm.charge_attack_multiplier,
			"speed_multiplier"     : pm.speed_multiplier,
			"kill_stack_active"    : pm.kill_stack_buff_active,
			"kill_stack_count"     : pm.kill_stack_count,
			"dash_stacks_max"      : pm.dash_stacks_max,
			"dash_stacks_current"  : pm.dash_stacks,
			"ability_multiplier"   : pm.ability_damage_multiplier,
			"bloodlust"            : pm.bloodlust_active,
			"ghost_blade"          : pm.ghost_blade_active,
			"last_stand"           : pm.last_stand_active,
			"momentum_active"      : pm.momentum_active,
			"momentum_stacks"      : pm.momentum_stacks,
			"double_strike_active" : pm.double_strike_active,
			"double_strike_ready"  : pm.double_strike_ready,
			"frenzy_active"        : pm.frenzy_active,
			"frenzy_stacks"        : pm.frenzy_stacks,
			"cheat_death_active"   : pm.cheat_death_active,
			"cheat_death_used"     : pm.cheat_death_used,
			"active_buff_ids"      : pm.active_buff_ids,
		},
		"enemies"      : enemies_data,
		"enemy_count"  : enemies_data.size(),
		"gems"           : PlayerManager.INVENTORY_DATA.get_item_held_quantity(_gem_item) if _gem_item else 0,
		"total_kills"    : pm.total_kill_count,
		"damage_taken"   : pm.damage_taken_this_run,
		"nearest_exit"    : nearest_exit,
		"ability_index"   : ability_idx,
		"quest_started"   : quest_started,
		"npc_pos"         : npc_pos,
		"levers_current"  : levers_current,
		"levers_total"    : levers_total,
		"in_dialog"       : DialogSystem.is_active,
		"in_shop"         : ShopMenu.is_active,
		"charge_progress" : charge_progress,
		"statues"         : statues_data,
		"plates"          : plates_data,
		"nearest_trap"    : nearest_trap,
		"top_traps"       : top_traps,
		"lich_projectiles" : top_lich_projs,
		"trap_arrows"     : top_trap_arrows,
		"item_chests"     : item_chests_data,
		"current_wave"    : current_wave,
		"kills_in_room"   : kills_in_room,
		"kill_target"     : kill_target,
		"levers"          : levers_data,
		"locked_door"     : locked_door,
		"item_drop"       : item_drop,
		"pickups"         : top_pickups,
		"boss_pos"        : boss_pos,
		"boss_phase"      : boss_phase,
	}

	# Reward per kill — doar cand exista inamici reali (nu plante din decor)
	# Run 5b boost: 15 → 30 (combat e bottleneck, BC nu invata facing precis)
	var new_kills := pm.total_kill_count - _prev_kill_count
	if new_kills > 0 and enemies_data.size() > 0:
		_pending_reward += new_kills * 30.0
		var scene_now = get_tree().current_scene
		var sp_now : String = scene_now.scene_file_path if scene_now else ""
		# Run5l_v2: ANTI-FARMING A1/03 MODERAT (-100 era prea agresiv, 5l natural reach 0.9%).
		# Inapoi la 5k level (-60) — net -30/kill, descurajare moderata fara a bloca combat normal.
		if "Area01/03" in sp_now and not _trigger_line_crossed:
			_pending_reward -= new_kills * 60.0   # net -30/kill A1/03 pre-trigger
		# Run5k: BOOST kill A2/01 — wave clear important pentru exit A2/02
		# Net effect: +30 + 30 = +60/kill in A2/01 (dublu vs default)
		elif "Area02/01" in sp_now:
			_pending_reward += new_kills * 30.0
		# Run5l: BOOST kill A2/02 — boss room cu orc+lich, combat dur, semnal puternic
		# Net effect: +30 + 30 = +60/kill in A2/02
		elif "Area02/02" in sp_now:
			_pending_reward += new_kills * 30.0
	_prev_kill_count = pm.total_kill_count

	# Reward pentru damage dat (reducere HP inamici intre exporturi)
	# Run 5b boost: 0.5 → 1.0 (semnal mai dens per hit, +10 per goblin full kill)
	var total_enemy_hp := 0
	for e in enemies_data:
		total_enemy_hp += int(e["hp"])
	if _prev_total_enemy_hp >= 0 and total_enemy_hp < _prev_total_enemy_hp:
		_pending_reward += float(_prev_total_enemy_hp - total_enemy_hp) * 1.0
	_prev_total_enemy_hp = total_enemy_hp if enemies_data.size() > 0 else -1

	# B1: Penalizare damage primit REDUSA (1.0 → 0.3) — descuraja combat prea tare
	if _prev_player_hp >= 0 and p.hp < _prev_player_hp:
		_pending_reward -= float(_prev_player_hp - p.hp) * 0.3
	_prev_player_hp = p.hp

	# B3 NOU: reward orientare attack — cand AI face damage SI e orientat spre inamic apropiat (<32px)
	# Run 5b boost: 2.0 → 5.0 (incurajeaza facing precis pentru one-shot kill)
	var did_damage_this_step := (new_kills > 0) or (_prev_total_enemy_hp >= 0 and total_enemy_hp < _prev_total_enemy_hp)
	if did_damage_this_step and enemies_data.size() > 0:
		var facing := Vector2(p.cardinal_direction.x, p.cardinal_direction.y)
		if facing.length() > 0.01:
			var fn := facing.normalized()
			for e in enemies_data:
				var ep := Vector2(float(e["x"]), float(e["y"]))
				var to_enemy := ep - p.global_position
				var d_enemy := to_enemy.length()
				if d_enemy > 0.01 and d_enemy < 32.0:
					var dot := fn.dot(to_enemy.normalized())
					if dot > 0.5:
						_pending_reward += 5.0
						break

	# alt-C2: partial clear milestone — bonus la 50% kill_target (incurajeaza progres in waves)
	# Run5k: 25 → 100 (boost pentru a marca clar "esti la jumatate")
	if kill_target > 0 and kills_in_room >= int(ceil(kill_target / 2.0)) and not _partial_clear_rewarded:
		_partial_clear_rewarded = true
		_pending_reward += 100.0
		_log_event("partial_clear", {"kills": kills_in_room, "target": kill_target})

	# Trigger line in Area01/03 — chests spawn dupa ce traversezi y<=-490
	var scene_path_curr : String = scene.scene_file_path if scene else ""
	if "Area01/03" in scene_path_curr:
		# B6 NOU: waypoints intermediare nord — gradient dens, AI invata "nord = bani"
		if not _waypoint_y0_passed and p.global_position.y <= 0.0:
			_waypoint_y0_passed = true
			_pending_reward += 20.0
			_log_event("waypoint_y0", {"scene": scene_path_curr})
		if not _waypoint_y200_passed and p.global_position.y <= -200.0:
			_waypoint_y200_passed = true
			_pending_reward += 30.0
			_log_event("waypoint_y200", {"scene": scene_path_curr})
		if not _waypoint_y350_passed and p.global_position.y <= -350.0:
			_waypoint_y350_passed = true
			_pending_reward += 50.0   # B6b: gradient suplimentar intre y=-200 si y=-490
			_log_event("waypoint_y350", {"scene": scene_path_curr})
		if not _trigger_line_crossed and p.global_position.y <= -490.0:
			_trigger_line_crossed = true
			_pending_reward += 1500.0  # Run5l_v2: 2500→1500 inapoi la 5k (2500 prea extrem, policy s-a destabilizat)
			_log_event("trigger_line_crossed", {"scene": scene_path_curr})
		# Run5h_v2: gradient nord 0.15 → 0.25 (push mai puternic spre trigger)
		# Pilot 5h: AI ajunge la y=-200 (71% ep A1/03) dar moare intre y=-200 si -490
		if not _trigger_line_crossed:
			if p.global_position.y < _prev_north_y:
				var progress := _prev_north_y - p.global_position.y
				_pending_reward += progress * 0.25   # Run5l_v2: 0.40→0.25 inapoi la 5k baseline
				_prev_north_y = p.global_position.y
			# Run5k FIX BUG: back-south penalty PRE-trigger
			# AI atingea waypoint y=-200, lua reward, apoi se intorcea sud fara penalty
			if _waypoint_y200_passed and p.global_position.y > -50.0:
				_pending_reward -= 0.15  # regres mare sud dupa wp y=-200 (TARE)
			elif _waypoint_y0_passed and p.global_position.y > 100.0:
				_pending_reward -= 0.08  # regres dupa wp y=0
		else:
			# Run5h_v2: back-south penalty BLAND -0.06 → -0.02 (pilot a aratat ca prea agresiv)
			# Stay-north bonus la fel
			if p.global_position.y <= -490.0:
				_pending_reward += 0.04   # stay-north bonus (zona chest)
			elif p.global_position.y > -200.0:
				_pending_reward -= 0.02   # back-south penalty bland
	else:
		_prev_north_y = INF   # reset cand iese din camera

	# Run5f: A2/01 — waypoints sud + reward continuu (pod ingust = greu de traversat)
	# Run5g: + bridge x-alignment reward + survival bonus
	# Spawn y=70, LevelTransitionSouth la y=1105, deci 1035 px de coborat
	# Bridge x-center ~416 (exit position), banda walkable [300, 500]
	if "Area02/01" in scene_path_curr:
		var py := p.global_position.y
		var px := p.global_position.x
		# Waypoint-uri sud (Run 5f)
		if not _waypoint_a2_y300_passed and py >= 300.0:
			_waypoint_a2_y300_passed = true
			_pending_reward += 20.0
			_log_event("waypoint_a2_y300", {"scene": scene_path_curr})
		if not _waypoint_a2_y600_passed and py >= 600.0:
			_waypoint_a2_y600_passed = true
			_pending_reward += 30.0
			_log_event("waypoint_a2_y600", {"scene": scene_path_curr})
		if not _waypoint_a2_y900_passed and py >= 900.0:
			_waypoint_a2_y900_passed = true
			_pending_reward += 50.0
			_log_event("waypoint_a2_y900", {"scene": scene_path_curr})
		if not _waypoint_a2_y1050_passed and py >= 1100.0:
			_waypoint_a2_y1050_passed = true
			_pending_reward += 300.0  # Run5l_v6 BIS: y1050→y1100 (aproape de LevelTransition la 1105)
			_log_event("waypoint_a2_y1100", {"scene": scene_path_curr})
		# Reward continuu pe progres SUD (Run 5f)
		if not _waypoint_a2_y1050_passed:
			if py > _prev_south_y:
				var progress := py - _prev_south_y
				_pending_reward += progress * 0.15
				_prev_south_y = py
		# Run5h_v2: SCOS reward bridge x-alignment — user a spart peretele subtire,
		# nu mai exista pod ingust, A2/01 e acum camera deschisa.
		# Waypoint-urile sud (y300/600/900/1050) raman valide ca gradient progres.
		# Run5k: survival bonus crescut 0.03 → 0.08 (movement-gated)
		# Cu shop fix functional, AI evita A2/01 ca anticipeaza penalty timpu in shop.
		# Mai mult survival reward ca sa-l motiveze sa intre/exploreze A2/01.
		var curr_a201_pos := Vector2(px, py)
		var a201_is_cleared := "Area02/01" in _room_cleared_in_scene
		# Run5l_v5: REVERT penalty blanket (era prea agresiv, AI evita A2/01). Pastrez survival.
		if _prev_a201_pos.distance_to(curr_a201_pos) > 2.0:
			_pending_reward += 0.08  # survival movement-gated (pre + post clear)
		_prev_a201_pos = curr_a201_pos
		# A2/02 magnet DELTA-based (Run5l_v8): reward DOAR pt apropiere, nu pt presence (era farming)
		# Run5l_v8b: post-clear → magnet activ pe TOATA camera (scoatem gate y>400 dupa clear)
		# + rate dublat post-clear (0.6→1.2), away-penalty triplat (0.1→0.3)
		# Run5l_v8d: post-BUFF → rate boost 1.2 → 2.5, away 0.3 → 0.6 (push agresiv spre exit dupa chest)
		var exit_magnet_active := py > 400.0 or a201_is_cleared
		if exit_magnet_active:
			var dist_exit: float = Vector2(px, py).distance_to(Vector2(415.0, 1100.0))
			var a201_buff_taken: bool = (_buff_picked_in_scene == "res://Levels/Area02/01.tscn")
			if _prev_exit_dist >= 0.0 and dist_exit < _prev_exit_dist:
				var delta_exit: float = _prev_exit_dist - dist_exit
				var rate: float = 2.5 if a201_buff_taken else (1.2 if a201_is_cleared else 0.2)
				_pending_reward += delta_exit * rate
			elif _prev_exit_dist >= 0.0 and dist_exit > _prev_exit_dist:
				var away_rate: float = 0.6 if a201_buff_taken else (0.3 if a201_is_cleared else 0.1)
				_pending_reward -= (dist_exit - _prev_exit_dist) * away_rate
			_prev_exit_dist = dist_exit
		# Run5l_v6: penalty stay-north A2/01 pre-clear — AI sta degeaba lang spawn
		if not a201_is_cleared and py < 250.0:
			_pending_reward -= 0.1  # forteaza avansare sud pentru combat
		# Run5l_v8b: post-clear → penalty progresiv pentru zona nordica (chest la y=990)
		# Run5l_v8e: 0.08 → 0.04 (era prea agresiv, AI evita A2/01 complet, reach 36%→10%)
		elif a201_is_cleared and py < 700.0:
			_pending_reward -= 0.04 * ((700.0 - py) / 700.0)  # max -0.04 la y=0, 0 la y=700
		# Run5l_v8b: center-push magnet — AI sta in colt stanga (x<200) sau dreapta (x>650)
		# pushes spre banda centrala walkable [300, 500] cu rate mic dar persistent
		# Run5l_v8e: 0.04 → 0.02 (penalty halved — contribuia la evita A2/01)
		var center_x: float = 415.0
		var x_offset: float = abs(px - center_x)
		if x_offset > 150.0:  # in afara benzii centrale ±150
			# pull spre centru: penalty progresiv cu cat e mai departe
			_pending_reward -= 0.02 * ((x_offset - 150.0) / 200.0)  # max -0.02 la x_offset=350
	else:
		_prev_south_y = -INF   # reset cand iese din A2/01
		_prev_a201_pos = Vector2.ZERO  # Run5h: reset anti-exploit tracker

	# Run5l: A2/02 — survival movement-gated + proximity reward lever neactivat
	if "Area02/02" in scene_path_curr:
		# Survival bonus (movement-gated, ca in A2/01) — semnal "stai aici, exploreaza"
		var curr_a202_pos := p.global_position
		if _prev_a202_pos.distance_to(curr_a202_pos) > 2.0:
			_pending_reward += 0.08
		_prev_a202_pos = curr_a202_pos
		# Run5l_v8c HYBRID: directie = nearest (gradient clar), magnet bonus = per-lever la <60px.
		# Direcția vine de la cel mai apropiat (semnal crisp, fara confuzie).
		# Bonus se aplica per lever neactivat la <60px (daca esti langa 2 simultan, +0.5 × 2).
		var nearest_lever_dist := INF
		var magnet_bonus := 0.0
		for lm in get_tree().get_nodes_in_group("lever_managers"):
			if is_instance_valid(lm) and "_lever_nodes" in lm:
				for lv in lm._lever_nodes:
					if is_instance_valid(lv) and "is_activated" in lv and not lv.is_activated:
						var d := p.global_position.distance_to(lv.global_position)
						if d < nearest_lever_dist:
							nearest_lever_dist = d
						if d < 60.0:
							magnet_bonus += 0.5  # bonus PER lever apropiat (hybrid)
		# Directional gradient pe nearest (range 700 acopera toata camera ~800×650, deoarece
		# distanta intre levere e 266-652px — cu 250 vechi, AI orbea dupa primul activat)
		if nearest_lever_dist < 700.0:
			if _prev_lever_dist >= 0.0 and _prev_lever_dist < 700.0:
				var delta_lever := _prev_lever_dist - nearest_lever_dist
				if delta_lever > 0.0:
					var lever_rate: float = 0.08 if nearest_lever_dist < 250.0 else 0.04
					_pending_reward += delta_lever * lever_rate
			_prev_lever_dist = nearest_lever_dist
		else:
			_prev_lever_dist = -1.0   # reset cand nici nearest nu mai e in raza
		_pending_reward += magnet_bonus
		# Run5l_v8d: A2/02 exit magnet POST-BUFF (chest deschis = puzzle complet)
		# Push agresiv spre exit south (LevelTransition2 la 336,561) cu rate 2.5 (ca A2/01 v8d)
		var a202_buff_taken: bool = (_buff_picked_in_scene == "res://Levels/Area02/02.tscn")
		if a202_buff_taken:
			var dist_a202_exit: float = p.global_position.distance_to(Vector2(336.0, 561.0))
			if _prev_a202_exit_dist >= 0.0 and dist_a202_exit < _prev_a202_exit_dist:
				_pending_reward += (_prev_a202_exit_dist - dist_a202_exit) * 2.5
			elif _prev_a202_exit_dist >= 0.0 and dist_a202_exit > _prev_a202_exit_dist:
				_pending_reward -= (dist_a202_exit - _prev_a202_exit_dist) * 0.6
			_prev_a202_exit_dist = dist_a202_exit
		else:
			_prev_a202_exit_dist = -1.0  # reset pre-buff
	else:
		_prev_a202_pos = Vector2.ZERO
		_prev_lever_dist = -1.0
		_prev_a202_exit_dist = -1.0

	# Run5l_v6: SHOP magnet spre exit south (291, 243) — drumul A2/01→SHOP→A2/02
	if "02_shop" in scene_path_curr:
		var shop_exit_dist := p.global_position.distance_to(Vector2(291.0, 243.0))
		if shop_exit_dist < 250.0:
			_pending_reward += (250.0 - shop_exit_dist) * 0.05  # max +12.5 la exit
		if shop_exit_dist < 30.0:
			_pending_reward += 1.0  # magnet lipit de exit south

	# Run5l_v3: D01/01 — puzzle statuie pe pressure plate
	# Reward proximity AI→statue (neactivata) + push reward (delta statue position)
	# + statue→plate closing distance (incurajeaza push in directia corecta)
	if "Dungeon01/01" in scene_path_curr:
		# Gaseste statue NEPLACED (on_target=false) cea mai apropiata
		var statue_pos := Vector2.ZERO
		var plate_pos := Vector2.ZERO
		var statue_found := false
		var plate_found := false
		for st in get_tree().get_nodes_in_group("pushable_statues"):
			if is_instance_valid(st) and "on_target" in st and not st.on_target:
				statue_pos = st.global_position
				statue_found = true
				break
		for pl in get_tree().get_nodes_in_group("pressure_plates"):
			if is_instance_valid(pl):
				plate_pos = pl.global_position
				plate_found = true
				break
		if statue_found:
			var ai_statue_dist := p.global_position.distance_to(statue_pos)
			# AI lipit de statuie => skip camping penalty (impinsul e lent, pare "imobil")
			_statue_push_active = ai_statue_dist < 45.0
			# A. Apropiere de POZITIA DE IMPINS (in spatele statuii, opus fata de placa) — NU de
			# centrul statuii. FIX Run8b: din BC agentul fugea stanga si rata pozitia din dreapta
			# statuii; asta il invata sa se pozitioneze CORECT pentru push. Delta-based (fara farming).
			if plate_found:
				var push_dir := (statue_pos - plate_pos).normalized()  # dinspre placa spre statuie
				var push_spot := statue_pos + push_dir * 24.0           # punctul de impins (in spate)
				var spot_dist := p.global_position.distance_to(push_spot)
				if spot_dist < 220.0:
					if _prev_pushspot_dist >= 0.0 and _prev_pushspot_dist < 220.0:
						var d_spot := _prev_pushspot_dist - spot_dist
						if d_spot > 0.0:
							_pending_reward += d_spot * 0.25  # pull spre pozitia de impins
					_prev_pushspot_dist = spot_dist
				else:
					_prev_pushspot_dist = -1.0
			_prev_statue_dist = ai_statue_dist
			_prev_statue_pos = statue_pos
			# B. Push reward DIRECTIONAL: statue→plate closing — DOAR delta (fara magnet plat,
			# ca sa NU poata farma stand langa placa). +0.8/px corect, -0.2/px gresit (spre pereti).
			# Optimizat: shaping pur potential-based; singurul reward "mare" e +500 la rezolvare.
			if plate_found:
				var sp_dist := statue_pos.distance_to(plate_pos)
				if _prev_statue_to_plate >= 0.0:
					var delta_sp := _prev_statue_to_plate - sp_dist
					if delta_sp > 0.0:
						_pending_reward += delta_sp * 0.8   # closing = push corect spre placa
					elif delta_sp < 0.0:
						_pending_reward += delta_sp * 0.2   # push GRESIT (departe de placa)
				_prev_statue_to_plate = sp_dist
		else:
			_prev_statue_dist = -1.0
			_prev_statue_to_plate = -1.0
			_prev_statue_pos = Vector2.ZERO
			_statue_push_active = false
			_prev_pushspot_dist = -1.0
	else:
		_prev_statue_dist = -1.0
		_prev_statue_to_plate = -1.0
		_prev_statue_pos = Vector2.ZERO
		_statue_push_active = false
		_prev_pushspot_dist = -1.0

	# Reward proximitate chest activ (delta-based, recompenseaza apropierea)
	# Include AMBELE: buff chests si item chests (goblin)
	var combined_chests : Array = all_chests + item_chests_data
	if PlayerHud.quest_timer_active and not combined_chests.is_empty() and not DialogSystem.is_active:
		var nearest_chest_dist := INF
		for chest_data in combined_chests:
			var d := p.global_position.distance_to(Vector2(float(chest_data.get("x", 0)), float(chest_data.get("y", 0))))
			if d < nearest_chest_dist:
				nearest_chest_dist = d
		# Run5l_v8b: BOOST rate cand camera curata (post-clear pull mare spre chest)
		# Run5l_v8g: REVERT v8f boost <300px (era prea agresiv, AI evita A2/01 complet)
		var sp_chest_curr: String = scene.scene_file_path if scene else ""
		var room_cleared_here := (sp_chest_curr == _room_cleared_in_scene and _room_cleared_in_scene != "")
		if _prev_chest_dist >= 0.0:
			var delta_chest := _prev_chest_dist - nearest_chest_dist
			if delta_chest > 0.0:
				var chest_rate: float = 0.2 if room_cleared_here else 0.05
				_pending_reward += delta_chest * chest_rate
			elif delta_chest < 0.0 and room_cleared_here:
				_pending_reward += delta_chest * 0.1   # v8g: back to 0.1 (era 0.3)
		_prev_chest_dist = nearest_chest_dist
		if nearest_chest_dist < 40.0:
			var chest_lipit: float = 1.5 if room_cleared_here else 0.5
			_pending_reward += chest_lipit   # v8g: back to 1.5 (era 3.0)
	else:
		_prev_chest_dist = -1.0

	# Penalizare proximitate trap activa (incurajeaza avoidance)
	if nearest_trap.get("found", false) and nearest_trap.get("is_active", false) and not DialogSystem.is_active:
		if min_trap_dist < 24.0:
			_pending_reward -= 0.3

	# Penalizare camping: daca nu se misca mai mult de 40 steps la rand
	var player_dist_moved := p.global_position.distance_to(_prev_player_pos)
	if not DialogSystem.is_active:
		# Run8: NU penaliza cand impinge statuia (miscare lenta = "imobil", dar e fix ce vrem)
		if player_dist_moved < 8.0 and not _statue_push_active:
			_still_steps += 1
			if _still_steps >= 20:
				_pending_reward -= 2.0
				_still_steps = 0
		else:
			_still_steps = 0
		_prev_player_pos = p.global_position

	# B5 (modificat): Penalitate stat in NPC — ACUM activa indiferent de quest
	# Run 4d initial avea conditia quest_started → AI invata sa NU vorbeasca cu NPC (no penalty)
	# Fix: penalty constant, mai mic fara quest (forteaza VORBESTE), mai mare dupa (forteaza PLEACA)
	if not DialogSystem.is_active:
		var scene_path_now : String = scene.scene_file_path if scene else ""
		if "Area01/02" in scene_path_now and not "_shop" in scene_path_now:
			if quest_started:
				_pending_reward -= 2.0   # dupa quest: pleaca!
			else:
				_pending_reward -= 1.0   # inainte de quest: vorbeste cu NPC sau pleaca

	# B8 NOU: penalty stat in scena dupa ce ai luat buff (forteaza plecare din A1/03)
	# Post-buff penalty AGRESIV (AI a luat chest, trebuie sa plece)
	if _buff_picked_in_scene != "" and not DialogSystem.is_active:
		var sp_now : String = scene.scene_file_path if scene else ""
		if sp_now == _buff_picked_in_scene:
			_pending_reward -= 3.0
		else:
			_buff_picked_in_scene = ""

	# B9: penalty post-clear MIC pre-buff (timp pt chest), AGRESIV post-buff
	if _room_cleared_in_scene != "" and not DialogSystem.is_active:
		var sp_clr : String = scene.scene_file_path if scene else ""
		if sp_clr == _room_cleared_in_scene:
			# Daca a luat deja buff in aceasta scena → penalty mare aplicat de buff block (mai sus)
			# Aici doar penalty MIC pentru "stat post-clear fara buff" — incurajeaza chest pickup
			if _buff_picked_in_scene != sp_clr:
				_pending_reward -= 0.3  # mic, AI are timp sa caute chest
		else:
			_room_cleared_in_scene = ""

	# Reward shaping: apropierea de NPC (doar inainte de quest) — BOOST run 4d-fix
	if not quest_started and npc_pos.get("found", false) and not DialogSystem.is_active:
		var curr_npc_dist := p.global_position.distance_to(
			Vector2(float(npc_pos["x"]), float(npc_pos["y"])))
		if _prev_npc_dist >= 0.0:
			var delta_npc := _prev_npc_dist - curr_npc_dist
			if delta_npc > 0.0:
				_pending_reward += delta_npc * 0.05   # BOOST 0.005 → 0.05 (10x)
		if curr_npc_dist < 60.0:
			_pending_reward += 0.5   # BOOST 0.1 → 0.5 (5x)
		_prev_npc_dist = curr_npc_dist
	else:
		_prev_npc_dist = -1.0

	# B2: Apropiere inamici — BOOST 0.004 → 0.03 (7.5x) + SCOS conditie player_dist_moved>2.0
	if quest_started and enemies_data.size() > 0 and not DialogSystem.is_active:
		var nearest_enemy_dist := INF
		for e in enemies_data:
			var d := p.global_position.distance_to(Vector2(float(e["x"]), float(e["y"])))
			if d < nearest_enemy_dist:
				nearest_enemy_dist = d
		if _prev_enemy_dist >= 0.0:
			var delta_enemy := _prev_enemy_dist - nearest_enemy_dist
			if delta_enemy > 0.0:
				_pending_reward += delta_enemy * 0.25  # Run8b: 0.10→0.25 (statea in colt, nu cauta inamici)
		_prev_enemy_dist = nearest_enemy_dist
	else:
		_prev_enemy_dist = -1.0

	# Run8b: pull spre BOSS (teleportant) — DOAR miscarea agentului spre boss (proiectata pe
	# directia spre boss), NU schimbarea de distanta (boss-ul se teleporteaza → spike + reward
	# pe gratis cand sare langa agent). Il duce langa boss ca sa-l poata lovi.
	if boss_pos.get("found", false) and not DialogSystem.is_active:
		var bpos := Vector2(float(boss_pos["x"]), float(boss_pos["y"]))
		if _prev_boss_approach_pos != Vector2.ZERO:
			var agent_move := p.global_position - _prev_boss_approach_pos
			var to_boss := bpos - p.global_position
			if to_boss.length() > 0.01 and agent_move.length() > 0.01:
				var approach := agent_move.dot(to_boss.normalized())
				if approach > 0.0:
					_pending_reward += approach * 0.20
		_prev_boss_approach_pos = p.global_position
	else:
		_prev_boss_approach_pos = Vector2.ZERO

	# Run8b: DODGE coverage attack — pull spre zona VERDE (safe spot) cand atacul „pe toata
	# harta" e activ. Miscarea agentului spre safe (agent-movement, fara spike) + bonus cand e safe.
	if PlayerManager.coverage_attack_active and not DialogSystem.is_active:
		var safe_pos : Vector2 = PlayerManager.coverage_safe_pos
		if safe_pos != Vector2.ZERO:
			if _prev_cov_approach_pos != Vector2.ZERO:
				var cmove := p.global_position - _prev_cov_approach_pos
				var to_safe := safe_pos - p.global_position
				if to_safe.length() > 0.01 and cmove.length() > 0.01:
					var c_appr := cmove.dot(to_safe.normalized())
					if c_appr > 0.0:
						_pending_reward += c_appr * 0.30   # pull PUTERNIC spre verde (atacul e letal)
			_prev_cov_approach_pos = p.global_position
			if PlayerManager.coverage_safe:
				_pending_reward += 0.5   # bonus cat sta in zona verde
		else:
			_prev_cov_approach_pos = Vector2.ZERO
	else:
		_prev_cov_approach_pos = Vector2.ZERO

	# Reward shaping: apropierea de nearest_exit
	# Run5l_v4_BIS: BOOST 5× rate dupa room_cleared SAU buff_picked (orice camera).
	# AI termina obiectivul → pull mare spre exit ca sa nu stagneze.
	# Run8: in A2/02 NU trage spre exit (jos) pana nu-s TOATE leverele facute — altfel exit-ul
	# concureaza cu manetele de SUS (ex. manet la y=61) si agentul merge "full jos" in loc sa
	# termine puzzle-ul. Dupa ce-s toate leverele, pull-ul spre exit revine (il ghideaza afara).
	var a202_puzzle_pending := ("Area02/02" in scene_path_curr) and levers_total > 0 and levers_current < levers_total
	if PlayerHud.quest_timer_active and nearest_exit.get("found", false) and not DialogSystem.is_active and not a202_puzzle_pending:
		var curr_dist := p.global_position.distance_to(
			Vector2(float(nearest_exit["x"]), float(nearest_exit["y"])))
		var sp_now : String = scene.scene_file_path if scene else ""
		var milestone_done := (_room_cleared_in_scene == sp_now) or (_buff_picked_in_scene == sp_now)
		var rate_close := 0.15 if milestone_done else 0.03  # 5× post-milestone
		var rate_retreat := 0.025 if milestone_done else 0.005  # penalty retragere 5×
		if _prev_exit_dist >= 0.0:
			var delta_dist := _prev_exit_dist - curr_dist
			if delta_dist > 0.0:
				_pending_reward += delta_dist * rate_close
			elif delta_dist < 0.0:
				_pending_reward += delta_dist * rate_retreat
		_prev_exit_dist = curr_dist
	else:
		_prev_exit_dist = -1.0

	# Run8b: pull spre USA BOSS (locked_door) cand ai cheia — usa blocheaza transition-ul deci
	# nearest_exit nu pointeaza spre ea; fara asta agentul lua cheia si statea pe loc.
	if locked_door.get("found", false) and locked_door.get("has_key", false) and not DialogSystem.is_active:
		var door_dist := p.global_position.distance_to(Vector2(float(locked_door["x"]), float(locked_door["y"])))
		if _prev_door_dist >= 0.0:
			var d_door := _prev_door_dist - door_dist
			if d_door > 0.0:
				_pending_reward += d_door * 0.20  # pull spre usa boss
		_prev_door_dist = door_dist
	else:
		_prev_door_dist = -1.0

	var file := FileAccess.open(STATE_FILE, FileAccess.WRITE)
	if file:
		file.store_string(JSON.stringify(state, "\t"))
		file.close()

	_pending_reward = 0.0


# ── logging episoade ───────────────────────────────────────────────────────────

func _log_episode(outcome: String, time: float) -> void:
	var pm    := PlayerManager
	var p     := pm.player
	var scene := get_tree().current_scene
	var entry := {
		"event"        : "episode_end",
		"timestamp"    : Time.get_unix_time_from_system(),
		"outcome"      : outcome,
		"time"         : time,
		"reward_total" : 1000.0 - time if outcome == "win" else -500.0 - time,  # Run5l_v4: revert
		"kills"        : pm.total_kill_count,
		"damage_taken" : pm.damage_taken_this_run,
		"buffs"        : pm.active_buff_ids.duplicate(),
		"buff_count"   : pm.active_buff_ids.size(),
		"gems"         : PlayerManager.INVENTORY_DATA.get_item_held_quantity(_gem_item) if _gem_item else 0,
		"scene_path"   : scene.scene_file_path if scene else "",
		"death_x"      : p.global_position.x if p and is_instance_valid(p) else 0.0,
		"death_y"      : p.global_position.y if p and is_instance_valid(p) else 0.0,
		"level"        : p.level            if p and is_instance_valid(p) else 0,
		"hp_remaining" : p.hp               if p and is_instance_valid(p) else 0,
		"max_hp"       : p.max_hp           if p and is_instance_valid(p) else 0,
		"boss_reached" : _boss_reached,
		"boss_hp_min"  : _min_boss_hp_this_run,
		"rooms_visited": _rooms_visited.duplicate(),
		"dmg_mult"     : pm.damage_multiplier,
		"speed_mult"   : pm.speed_multiplier,
		"ability_mult" : pm.ability_damage_multiplier,
	}
	var file := FileAccess.open(EVENTS_FILE, FileAccess.READ_WRITE)
	if not file:
		file = FileAccess.open(EVENTS_FILE, FileAccess.WRITE)
	if file:
		file.seek_end()
		file.store_line(JSON.stringify(entry))
		file.close()
	_reset_episode_tracking()


func _log_event(event_type: String, data: Dictionary) -> void:
	var entry := {"event": event_type, "timestamp": Time.get_unix_time_from_system()}
	entry.merge(data)
	var file := FileAccess.open(EVENTS_FILE, FileAccess.READ_WRITE)
	if not file:
		file = FileAccess.open(EVENTS_FILE, FileAccess.WRITE)
	if file:
		file.seek_end()
		file.store_line(JSON.stringify(entry))
		file.close()
