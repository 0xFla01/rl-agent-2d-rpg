extends CanvasLayer

@export var button_focus_audio : AudioStream = preload( "res://title_scene/audio/menu_focus.wav" )
@export var button_select_audio : AudioStream = preload( "res://title_scene/audio/menu_select.wav" )

var hearts : Array[ HeartGUI ] = []


@onready var game_over : Control = $Control/GameOver
@onready var continue_button: Button = $Control/GameOver/VBoxContainer/ContinueButton
@onready var title_button: Button = $Control/GameOver/VBoxContainer/TitleButton
@onready var animation_player: AnimationPlayer = $Control/GameOver/AnimationPlayer
@onready var audio: AudioStreamPlayer = $AudioStreamPlayer

@onready var abilities: Control = $Control/Abilities
@onready var ability_items: HBoxContainer = $Control/Abilities/HBoxContainer
@onready var arrow_count_label: Label = %ArrowCountLabel
@onready var bomb_count_label: Label = %BombCountLabel


@onready var boss_ui: Control = $Control/BossUI
@onready var boss_hp_bar: TextureProgressBar = $Control/BossUI/TextureProgressBar
@onready var boss_label: Label = $Control/BossUI/Label

@onready var notification_ui : NotificationUI = $Control/Notification

@onready var quest_timer : Control = $Control/QuestTimer
@onready var quest_timer_label : Label = $Control/QuestTimer/QuestTimerLabel

@onready var stack_counter : Control = $Control/StackCounter
@onready var stack_label : Label = $Control/StackCounter/StackLabel

var quest_time : float = 0.0
var quest_timer_active : bool = false

var _victory_panel     : Control = null
var _victory_time_lbl  : Label   = null
var _victory_best_lbl  : Label   = null
var _victory_stats_lbl : Label   = null
var _victory_new_run   : Button  = null




func _ready():
	for child in $Control/HFlowContainer.get_children():
		if child is HeartGUI:
			hearts.append( child )
			child.visible = false
	
	hide_game_over_screen()
	continue_button.focus_entered.connect( play_audio.bind( button_focus_audio ) )
	continue_button.pressed.connect( load_game )
	title_button.focus_entered.connect( play_audio.bind( button_focus_audio ) )
	title_button.pressed.connect( title_screen )
	LevelManager.level_load_started.connect( hide_game_over_screen )
	
	hide_boss_health()
	
	update_ability_ui( 0 )
	PauseMenu.shown.connect( _on_show_pause )
	PauseMenu.hidden.connect( _on_hide_pause )
	
	quest_timer.visible = false
	QuestManager.quest_updated.connect( _on_quest_updated )

	var new_run_btn := Button.new()
	new_run_btn.text = "New Run"
	new_run_btn.focus_entered.connect( play_audio.bind( button_focus_audio ) )
	new_run_btn.pressed.connect( _new_run )
	$Control/GameOver/VBoxContainer.add_child( new_run_btn )

	PlayerManager.run_completed.connect( _on_run_completed )
	# NU conectam show_game_over_screen la run_failed: state_death.gd il apeleaza
	# direct DUPA emit() — dubla conectare = 2x _new_run() in paralel cu race conditions.

	_build_victory_panel()
	pass



func update_hp( _hp: int, _max_hp: int ) -> void:
	update_max_hp( _max_hp )
	for i in _max_hp:
		update_heart( i, _hp )
		pass
	pass



func update_heart( _index : int, _hp : int ) -> void:
	var _value : int = clampi( _hp - _index * 2, 0, 2 )
	hearts[ _index ].value = _value
	pass



func update_max_hp( _max_hp : int ) -> void:
	var _heart_count : int = roundi( _max_hp * 0.5 )
	for i in hearts.size():
		if i < _heart_count:
			hearts[i].visible = true
		else:
			hearts[i].visible = false
	pass



func show_game_over_screen() -> void:
	if AIController.enabled:
		_new_run()
		return

	game_over.visible = true
	game_over.mouse_filter = Control.MOUSE_FILTER_STOP

	var can_continue : bool = SaveManager.get_save_file() != null
	continue_button.visible = can_continue
	title_button.visible = true

	animation_player.play("show_game_over")
	await animation_player.animation_finished

	if can_continue == true:
		continue_button.grab_focus()
	else:
		title_button.grab_focus()
	



func hide_game_over_screen() -> void:
	game_over.visible = false
	game_over.mouse_filter = Control.MOUSE_FILTER_IGNORE
	game_over.modulate = Color( 1,1,1,0 )



func load_game() -> void:
	play_audio( button_select_audio )
	await fade_to_black()
	SaveManager.load_game()


func title_screen() -> void:
	play_audio( button_select_audio )
	await fade_to_black()
	# Cleanup UI persistente — fara asta, boss HP / quest timer / panels raman pe ecran
	hide_boss_health()
	stop_quest_timer()
	if quest_timer:
		quest_timer.visible = false
	if _victory_panel:
		_victory_panel.visible = false
		_victory_panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	if game_over:
		game_over.visible = false
	PlayerManager.reset_run()
	LevelManager.load_new_level( "res://title_scene/title_scene.tscn", "", Vector2.ZERO )


func fade_to_black() -> bool:
	animation_player.play("fade_to_black")
	await animation_player.animation_finished
	PlayerManager.player.revive_player()
	return true



func play_audio( _a : AudioStream ) -> void:
	audio.stream = _a
	audio.play()



func show_boss_health( boss_name : String ) -> void:
	boss_ui.visible = true
	boss_label.text = boss_name
	update_boss_health( 1, 1 )
	pass


func hide_boss_health() -> void:
	boss_ui.visible = false
	pass


func update_boss_health( hp : int, max_hp : int ) -> void:
	boss_hp_bar.value = clampf( float(hp) / float(max_hp) * 100, 0, 100 )
	pass



func queue_notification( _title : String, _message : String ) -> void:
	notification_ui.add_notification_to_queue( _title, _message )
	pass


func update_ability_items( items : Array[String] ) -> void:
	var ability_items : Array[ Node ] = ability_items.get_children()
	for i in ability_items.size():
		if items[ i ] == "":
			ability_items[ i ].visible = false
		else:
			ability_items[ i ].visible = true
	pass


func update_ability_ui( ability_index : int ) -> void:
	var _items : Array[ Node ] = ability_items.get_children()
	for a in _items:
		a.self_modulate = Color(1,1,1,0)
		a.modulate = Color(0.6,0.6,0.6,0.8)
	_items[ ability_index ].self_modulate = Color(1,1,1,1)
	_items[ ability_index ].modulate = Color(1,1,1,1)
	play_audio( button_focus_audio )
	pass


func update_arrow_count( count : int ) -> void:
	arrow_count_label.text = str( count )
	pass


func update_bomb_count( count : int ) -> void:
	bomb_count_label.text = str( count )
	pass


func _on_show_pause() -> void:
	abilities.visible = false
	pass


func _on_hide_pause() -> void:
	abilities.visible = true
	pass


func _process(delta: float) -> void:
	if quest_timer_active:
		quest_time += delta
		if quest_timer_label:
			quest_timer_label.text = _format_time(quest_time)

	if stack_counter:
		var lines : Array[String] = []
		if PlayerManager.kill_stack_buff_active:
			lines.append( "KILL STACKS  %d / %d" % [ PlayerManager.kill_stack_count, PlayerManager.KILL_STACK_CAP ] )
		if PlayerManager.momentum_active:
			lines.append( "MOMENTUM  +%d%%" % [ PlayerManager.momentum_stacks * 5 ] )
		if PlayerManager.frenzy_active:
			lines.append( "FRENZY  +%d%%" % [ PlayerManager.frenzy_stacks * 3 ] )
		if PlayerManager.double_strike_active:
			var ds_text := "DOUBLE STRIKE  " + ( "[READY]" if PlayerManager.double_strike_ready else "[-]" )
			lines.append( ds_text )
		stack_counter.visible = not lines.is_empty()
		if stack_label:
			stack_label.text = "\n".join( lines )


func _on_quest_updated(quest) -> void:
	if quest.title == "Defeat the Dark Wizard":
		if quest.is_complete:
			# Quest finished - stop timer
			stop_quest_timer()
		elif not quest_timer_active:
			# Quest started or restarted - begin from 0
			start_quest_timer()


func start_quest_timer() -> void:
	quest_time = 0.0
	quest_timer_active = true
	if quest_timer:
		quest_timer.visible = true
	if quest_timer_label:
		quest_timer_label.text = "00:00"

func reset_quest_timer() -> void:
	quest_time = 0.0
	quest_timer_active = false
	if quest_timer:
		quest_timer.visible = false
	if quest_timer_label:
		quest_timer_label.text = "00:00"


func stop_quest_timer() -> void:
	quest_timer_active = false


var _new_run_in_progress : bool = false

func _new_run() -> void:
	if _new_run_in_progress:
		return   # protectie double-call (race intre state_death + AIController reset)
	_new_run_in_progress = true

	if _victory_panel:
		_victory_panel.visible = false
		_victory_panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	# Cleanup UI persistente — fara asta, boss HP bar ramanea pe ecran dupa
	# moarte la boss + new_run (ne fiind boss spawnat in noua scena, nu mai aparea hide).
	hide_boss_health()
	play_audio( button_select_audio )
	await fade_to_black()
	PlayerManager.reset_run()

	# Curriculum spawn pentru AI: ocazional sare direct in camere adanci
	var spawn_scene := "res://Levels/Area01/02.tscn"
	if AIController.enabled:
		spawn_scene = AIController.get_curriculum_spawn()

	LevelManager.load_new_level( spawn_scene, "", Vector2.ZERO, true )

	# Daca AI a sarit peste A1/02 (NPC room), porneste questul automat.
	# Altfel quest_started ramane false si majoritatea reward-urilor de progres nu fire-eaza.
	if AIController.enabled and spawn_scene != "res://Levels/Area01/02.tscn":
		await LevelManager.level_loaded
		QuestManager.update_quest("Defeat the Dark Wizard", "", false)
		_give_ai_curriculum_kit(spawn_scene)   # Run8: gems + buff-uri pt camerele SARITE
		# Fix nearest_exit: la spawn override, LT-ul "south" e tehnic intrarea (back-edge).
		# Simulam ca AI a venit din scena precedenta naturala -> filtrul exclude LT-ul gresit
		# si nearest_exit pointeaza spre exit-ul real (forward).
		if AIController.CURRICULUM_PREV_SCENE.has(spawn_scene):
			LevelManager.previous_scene_path = AIController.CURRICULUM_PREV_SCENE[spawn_scene]
		# Invincibilitate 4s la spawn override — Python sleep 1.5s real + buffer pentru ca
		# AI sa primeasca obs si sa decida primele actiuni. Mai sigur decat 1.5s anterior.
		var p := PlayerManager.player
		if p and is_instance_valid(p) and p.has_method("make_invulnerable"):
			p.make_invulnerable(4.0)
		# Freeze inamici pana playerul se misca >16px (sau timeout 6s real). Foloseste
		# process_mode = DISABLED pentru a inghita TOATA subtree (state_machine, hit/hurt
		# boxes, animations) — set_physics_process(false) singur nu opreste state_machine.
		_freeze_enemies_until_player_moves()

	_new_run_in_progress = false


func _give_ai_curriculum_kit(spawn_scene: String) -> void:
	# Run8: kit de start pt spawn curriculum — simuleaza camerele SARITE (gems + buff-uri).
	# Altfel agentul ajunge adanc SARAC (nu poate folosi shop-ul) + FARA power-up-uri
	# (= A2/01 nedrept de greu). reset_run() a curatat tot inainte, deci asta e singurul kit.
	# Cantitati ~ ce-ar avea natural la acea adancime + mic scaffolding (+1 buff) pt invatare.
	# Realist: A1/01 da o ARMA SECUNDARA (boomerang/grapple/arrow), A1/03 da un BUFF.
	# === FILMARE: kit FIX D01 (boomerang + kill_stack + momentum 45% + HP full) — orice camera
	# dungeon, cu timer per camera pt video continuu (statuie 22:03, hub 35:35). ===
	if "Dungeon01/" in spawn_scene:
		var pl_f := PlayerManager.player
		if pl_f and is_instance_valid(pl_f) and "player_abilities" in pl_f:
			pl_f.player_abilities.abilities[0] = "BOOMERANG"
			pl_f.player_abilities.setup_abilities()
		PlayerManager.kill_stack_buff_active = true
		PlayerManager.kill_stack_count = 0
		if not PlayerManager.active_buff_ids.has("kill_stack"):
			PlayerManager.active_buff_ids.append("kill_stack")
		PlayerManager.momentum_active = true
		PlayerManager.momentum_stacks = 9   # 9 * 5% = 45%
		if not PlayerManager.active_buff_ids.has("momentum"):
			PlayerManager.active_buff_ids.append("momentum")
		if pl_f and is_instance_valid(pl_f):
			pl_f.hp = pl_f.max_hp
			pl_f.update_hp(0)
			pl_f.update_damage_values()
		# Timer per camera pt video continuu (timer crescator: statuie→hub→waves→boss)
		if "Dungeon01/01" in spawn_scene:
			quest_time = 1323.0   # 22:03 statuie
		elif "Dungeon01/03" in spawn_scene:
			quest_time = 2300.0   # 38:20 waves
		elif "Dungeon01/04" in spawn_scene:
			quest_time = 2416.0   # 40:16 boss
		else:
			quest_time = 2135.0   # 35:35 hub (D01/02)
		quest_timer_active = true
		if quest_timer:
			quest_timer.visible = true
		return
	var n_buffs := 0
	var gems := 0
	if "Area02/01" in spawn_scene:
		n_buffs = 1; gems = randi_range(20, 35)   # 1 arma (A1/01) + 1 buff (A1/03)
	elif "Area02/02" in spawn_scene:
		n_buffs = 2; gems = randi_range(30, 50)   # 1 arma + 2 buff (+ A2/01 + shop)
	else:
		return
	var pl := PlayerManager.player
	# gems (bani pt shop)
	var gem_item : ItemData = load("res://Items/gem.tres")
	if gem_item and gems > 0:
		PlayerManager.INVENTORY_DATA.add_item(gem_item, gems)
	# 1 arma secundara random (ca din A1/01) — echipata in slot-ul corect
	if pl and is_instance_valid(pl) and "player_abilities" in pl:
		var weapons := [[0, "BOOMERANG"], [1, "GRAPPLE"], [2, "ARROW"]]
		var w = weapons[randi() % weapons.size()]
		pl.player_abilities.abilities[w[0]] = w[1]
		pl.player_abilities.setup_abilities()
	# buff-uri random distincte (acelasi mecanism ca buff chest: apply.call() + track id)
	for buff in BuffPool.get_random_buffs(n_buffs):
		buff.apply.call()
		PlayerManager.active_buff_ids.append(buff.id)
	if pl and is_instance_valid(pl):
		pl.update_damage_values()


func _freeze_enemies_until_player_moves() -> void:
	# Astept un frame ca toate enemy._ready sa ruleze si sa se inregistreze in "enemies"
	await get_tree().process_frame
	var enemies := get_tree().get_nodes_in_group("enemies")
	# Freeze SELECTIV: dezactiveaza state_machine (chase/attack AI) si miscare fizica,
	# dar PASTREAZA hit_box activ ca playerul sa poata da damage in inamici inghetati.
	for enemy in enemies:
		if not is_instance_valid(enemy):
			continue
		if "state_machine" in enemy and enemy.state_machine:
			enemy.state_machine.process_mode = Node.PROCESS_MODE_DISABLED
		enemy.set_physics_process(false)
		if enemy is CharacterBody2D:
			enemy.velocity = Vector2.ZERO
	# Timp fix sincronizat cu invuln-ul (4s). Dupa expirare AI ar trebui sa aiba deja
	# controlul activ + a inceput sa atace.
	await get_tree().create_timer(4.0).timeout
	for enemy in enemies:
		if not is_instance_valid(enemy):
			continue
		if "state_machine" in enemy and enemy.state_machine:
			enemy.state_machine.process_mode = Node.PROCESS_MODE_INHERIT
		enemy.set_physics_process(true)


func _on_run_completed(time: float) -> void:
	stop_quest_timer()
	var best := _load_best_time()
	var is_new_best := (best <= 0.0 or time < best)
	if is_new_best:
		_save_best_time(time)
		best = time

	if not _victory_panel or not _victory_time_lbl:
		return
	_victory_time_lbl.text  = "Time: " + _format_time(time)
	var best_str := "Best: " + _format_time(best)
	if is_new_best:
		best_str += "  ★ NEW BEST!"
	_victory_best_lbl.text  = best_str
	_victory_stats_lbl.text = "Kills: %d" % PlayerManager.total_kill_count
	_victory_panel.visible = true
	_victory_panel.mouse_filter = Control.MOUSE_FILTER_STOP
	if _victory_new_run:
		_victory_new_run.grab_focus()


func _format_time(t: float) -> String:
	var minutes : int = int(t / 60.0)
	var seconds : int = int(t) % 60
	return "%02d:%02d" % [minutes, seconds]


func _build_victory_panel() -> void:
	var panel := PanelContainer.new()
	panel.name = "VictoryPanel"
	panel.visible = false
	panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	panel.set_anchors_preset(Control.PRESET_FULL_RECT)
	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.0, 0.0, 0.05, 0.82)
	panel.add_theme_stylebox_override("panel", style)
	$Control.add_child(panel)
	_victory_panel = panel

	var center := CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	panel.add_child(center)

	var vbox := VBoxContainer.new()
	vbox.name = "VBoxContainer"
	vbox.custom_minimum_size = Vector2(300, 0)
	vbox.add_theme_constant_override("separation", 14)
	center.add_child(vbox)

	var title_lbl := Label.new()
	title_lbl.text = "VICTORY!"
	title_lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title_lbl.add_theme_font_size_override("font_size", 36)
	title_lbl.add_theme_color_override("font_color", Color(1.0, 0.9, 0.25, 1))
	title_lbl.add_theme_color_override("font_outline_color", Color.BLACK)
	title_lbl.add_theme_constant_override("outline_size", 3)
	vbox.add_child(title_lbl)

	vbox.add_child(HSeparator.new())

	var time_lbl := Label.new()
	time_lbl.text = "Time: --:--"
	time_lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	time_lbl.add_theme_font_size_override("font_size", 24)
	vbox.add_child(time_lbl)
	_victory_time_lbl = time_lbl

	var best_lbl := Label.new()
	best_lbl.text = "Best: --:--"
	best_lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	best_lbl.add_theme_font_size_override("font_size", 16)
	best_lbl.add_theme_color_override("font_color", Color(0.5, 1.0, 0.5, 1))
	vbox.add_child(best_lbl)
	_victory_best_lbl = best_lbl

	var stats_lbl := Label.new()
	stats_lbl.text = ""
	stats_lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	stats_lbl.add_theme_font_size_override("font_size", 14)
	stats_lbl.add_theme_color_override("font_color", Color(0.85, 0.85, 0.85, 1))
	vbox.add_child(stats_lbl)
	_victory_stats_lbl = stats_lbl

	vbox.add_child(HSeparator.new())

	var new_run_btn := Button.new()
	new_run_btn.text = "New Run"
	new_run_btn.focus_entered.connect(play_audio.bind(button_focus_audio))
	new_run_btn.pressed.connect(_new_run)
	vbox.add_child(new_run_btn)
	_victory_new_run = new_run_btn

	var title_btn := Button.new()
	title_btn.name = "TitleScreenButton"
	title_btn.text = "Title Screen"
	title_btn.focus_entered.connect(play_audio.bind(button_focus_audio))
	title_btn.pressed.connect(title_screen)
	vbox.add_child(title_btn)


func _load_best_time() -> float:
	if not FileAccess.file_exists("user://best_time.json"):
		return 0.0
	var f := FileAccess.open("user://best_time.json", FileAccess.READ)
	if not f:
		return 0.0
	var data = JSON.parse_string(f.get_as_text())
	f.close()
	if data is Dictionary and data.has("best"):
		return float(data["best"])
	return 0.0


func _save_best_time(t: float) -> void:
	var f := FileAccess.open("user://best_time.json", FileAccess.WRITE)
	if f:
		f.store_string(JSON.stringify({"best": t}))
		f.close()
