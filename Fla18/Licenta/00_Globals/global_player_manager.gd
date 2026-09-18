extends Node

const PLAYER = preload("res://Player/player.tscn")
const INVENTORY_DATA : InventoryData = preload("res://GUI/pause_menu/inventory/player_inventory.tres")

signal camera_shook( trauma : float )
signal interact_pressed
signal player_leveled_up
signal run_completed( time : float )
signal run_failed

var interact_handled : bool = true
var player : Player
var player_spawned : bool = false

var damage_multiplier : float = 1.0
var charge_attack_multiplier : float = 2.0

var kill_stack_buff_active : bool = false
var kill_stack_count : int = 0
const KILL_STACK_DAMAGE_PER : int = 2
const KILL_STACK_CAP : int = 30

const DASH_STACK_MAX : int = 2
const DASH_STACK_RECHARGE_TIME : float = 2.0
var dash_stacks_max : int = DASH_STACK_MAX
var dash_stacks : int = DASH_STACK_MAX
var dash_recharge_timer : float = 0.0

var ability_damage_multiplier : float = 1.0
var speed_multiplier : float = 1.0

var total_kill_count : int = 0

var damage_taken_this_run : int = 0
var active_buff_ids  : Array[String] = []
var bloodlust_active : bool = false
var ghost_blade_active : bool = false
var last_stand_active  : bool = false
var momentum_active    : bool = false
var momentum_stacks    : int  = 0

var double_strike_active : bool = false
var double_strike_ready  : bool = false

var cheat_death_active : bool = false
var cheat_death_used   : bool = false

var coverage_safe         : bool    = false
var coverage_attack_active : bool   = false
var coverage_safe_pos      : Vector2 = Vector2.ZERO
var coverage_safe_positions : Array  = []   # Run9: 4 zone safe simultane (coverage attack)

var frenzy_active      : bool = false
var frenzy_stacks      : int  = 0
var frenzy_reset_timer : float = 0.0
const FRENZY_STACK_CAP  : int   = 20
const FRENZY_RESET_TIME : float = 4.0

#var level_requirements = [ 0, 50, 100, 200, 400, 800, 1500, 3000, 6000, 12000, 2500 ]
var level_requirements = [ 0, 5, 10, 20, 40 ]


func _ready() -> void:
	add_player_instance()
	await get_tree().create_timer(0.2).timeout
	player_spawned = true


func _process(delta: float) -> void:
	if dash_stacks < dash_stacks_max:
		dash_recharge_timer += delta
		if dash_recharge_timer >= DASH_STACK_RECHARGE_TIME:
			dash_recharge_timer = 0.0
			dash_stacks += 1

	if frenzy_active and frenzy_stacks > 0:
		frenzy_reset_timer += delta
		if frenzy_reset_timer >= FRENZY_RESET_TIME:
			frenzy_stacks = 0
			frenzy_reset_timer = 0.0


func can_dash() -> bool:
	return dash_stacks > 0


func consume_dash_stack() -> void:
	if dash_stacks > 0:
		dash_stacks -= 1
		if dash_stacks == dash_stacks_max - 1:
			dash_recharge_timer = 0.0



func add_player_instance() -> void:
	player = PLAYER.instantiate()
	add_child( player )
	pass



func set_health( hp: int, max_hp: int ) -> void:
	player.max_hp = max_hp
	player.hp = hp
	player.update_hp( 0 )



func reward_xp( _xp : int ) -> void:
	player.xp += _xp
	# check for level advancement
	check_for_level_advance()


# Check for level advance, recursively.
# A recursive function will call itself under certain conditions,
# and will NOT call itself under other conditions, known as a base condition.
# An exit or base condition that stops the recursion is essential, 
# otherwise the function will call itself indefinitely and lock up the program 
func check_for_level_advance() -> void:
	if player.level >= level_requirements.size():
		return
	if player.xp >= level_requirements[ player.level ]:
		player.level += 1
		player.attack += 1
		player.defense += 1
		player_leveled_up.emit()
		check_for_level_advance()
	pass




func set_player_position( _new_pos : Vector2 ) -> void:
	player.global_position = _new_pos
	pass



func set_as_parent( _p : Node2D ) -> void:
	if player.get_parent():
		player.get_parent().remove_child( player )
	_p.add_child( player )



func unparent_player( _p : Node2D ) -> void:
	if player and is_instance_valid(player) and player.get_parent() == _p:
		_p.remove_child( player )



func play_audio( _audio : AudioStream ) -> void:
	player.audio.stream = _audio
	player.audio.play()



func interact() -> void:
	interact_handled = false
	interact_pressed.emit()



func shake_camera( trauma : float = 1 ) -> void:
	camera_shook.emit( clampi( trauma, 0, 3 ) )



func reset_camera_on_player( tween_duration : float = 0.5 ) -> void:
	var camera : Camera2D = get_viewport().get_camera_2d()
	if camera:
		if camera.get_parent() == player:
			print("Camera already on player")
			return
		camera.reparent( player )
		
		var tween : Tween = create_tween()
		tween.set_ease( Tween.EASE_OUT )
		tween.set_trans( Tween.TRANS_QUAD )
		tween.tween_property( camera, "position", Vector2.ZERO, tween_duration )
	pass


func on_enemy_killed() -> void:
	total_kill_count += 1
	if kill_stack_buff_active and kill_stack_count < KILL_STACK_CAP:
		kill_stack_count += 1
	if bloodlust_active and player:
		player.update_hp(1)
	if momentum_active and momentum_stacks < 10:
		momentum_stacks += 1
		# IMPORTANT: NU mai setam speed_multiplier aici — overwrite-ul anula
		# potion-ul de speed (1.5) si oricare alt buff de speed. Bonusul momentum
		# se aplica separat in state_walk.gd ca multiplicator peste speed_multiplier.
	if player:
		player.update_damage_values()


func on_player_dashed() -> void:
	if kill_stack_buff_active and kill_stack_count > 0:
		kill_stack_count = 0
		if player:
			player.update_damage_values()
	if double_strike_active:
		double_strike_ready = true


func on_player_attack_hit() -> void:
	if not frenzy_active:
		return
	frenzy_reset_timer = 0.0
	frenzy_stacks = mini(frenzy_stacks + 1, FRENZY_STACK_CAP)


func get_frenzy_speed() -> float:
	return 1.0 + frenzy_stacks * 0.03


func get_buff_damage_bonus() -> int:
	if kill_stack_buff_active:
		return kill_stack_count * KILL_STACK_DAMAGE_PER
	return 0


func reset_run() -> void:
	reset_buffs()
	total_kill_count = 0
	player_spawned = false
	QuestManager.remove_quest("Defeat the Dark Wizard")
	PlayerHud.reset_quest_timer()
	var persistence : Array = SaveManager.current_save.persistence
	persistence.clear()
	SaveManager.current_save.abilities = ["", "", "", ""]
	if player:
		# Restaureaza stats la default — altfel berserker (max_hp-2) si level-up
		# (level/attack/defense+1) persistau dupa moarte si new_run.
		player.max_hp = 12
		player.level = 1
		player.xp = 0
		player.attack = 10
		player.defense = 1
		player.defense_bonus = 0
		player.hp = player.max_hp
		player.bomb_count = 10
		player.arrow_count = 30
		player.update_hp(0)
		player.player_abilities.abilities = ["", "", "", ""]
		player.player_abilities.setup_abilities()
	var gem_item : ItemData = load("res://Items/gem.tres")
	var gem_count := INVENTORY_DATA.get_item_held_quantity(gem_item)
	if gem_count > 0:
		INVENTORY_DATA.use_item(gem_item, gem_count)
	# Run8b: scoate CHEIA de dungeon la reset — altfel ramane intre episoade si blocheaza
	# intrarea in D01/03 (dungeon_02_manager) + permite skip waves.
	var key_item : ItemData = load("res://Items/key_dungeon.tres")
	if key_item:
		var key_count := INVENTORY_DATA.get_item_held_quantity(key_item)
		if key_count > 0:
			INVENTORY_DATA.use_item(key_item, key_count)


func reset_buffs() -> void:
	damage_multiplier = 1.0
	charge_attack_multiplier = 2.0
	kill_stack_buff_active = false
	kill_stack_count = 0
	dash_stacks_max = DASH_STACK_MAX
	dash_stacks = DASH_STACK_MAX
	dash_recharge_timer = 0.0
	ability_damage_multiplier = 1.0
	speed_multiplier = 1.0
	total_kill_count = 0
	damage_taken_this_run = 0
	active_buff_ids.clear()
	bloodlust_active = false
	ghost_blade_active = false
	last_stand_active = false
	momentum_active = false
	momentum_stacks = 0
	double_strike_active = false
	double_strike_ready = false
	cheat_death_active = false
	cheat_death_used = false
	frenzy_active = false
	frenzy_stacks = 0
	frenzy_reset_timer = 0.0
	if player:
		player.update_damage_values()
