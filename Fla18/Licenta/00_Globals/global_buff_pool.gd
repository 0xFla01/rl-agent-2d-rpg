extends Node

## Central buff registry. Register as autoload "BuffPool".
## Each entry: id, name, desc (display text), apply (Callable), conflicts (Array[String])
## Smart selection: excludes already-active buffs, conflicting combos, and dangerous trades.

var _pool : Array[Dictionary] = []

func _ready() -> void:
	_pool = [
		{
			"id": "big_damage",
			"name": "BRUTE FORCE",
			"desc": "+50%\nBASE DAMAGE",
			"apply": _apply_big_damage,
			"conflicts": [],
		},
		{
			"id": "charge_master",
			"name": "CHARGE MASTER",
			"desc": "CHARGE ATTACK\n×4 BONUS DAMAGE",
			"apply": _apply_charge_master,
			"conflicts": ["ghost_blade"],
		},
		{
			"id": "kill_stack",
			"name": "KILL STACKS",
			"desc": "+2 DMG PER KILL\nmax 30 stacks\nresets on dash",
			"apply": _apply_kill_stack,
			"conflicts": [],
		},
		{
			"id": "speed_boost",
			"name": "SWIFT FEET",
			"desc": "+40% MOVE SPEED",
			"apply": _apply_speed_boost,
			"conflicts": ["momentum"],
		},
		{
			"id": "extra_dash",
			"name": "SHADOW STEP",
			"desc": "+1 EXTRA DASH\nCHARGE",
			"apply": _apply_extra_dash,
			"conflicts": [],
		},
		{
			"id": "ability_power",
			"name": "ARCANE SURGE",
			"desc": "×2 ABILITY DAMAGE\n(bow, boomerang\n& grapple)",
			"apply": _apply_ability_power,
			"conflicts": [],
		},
		{
			"id": "iron_will",
			"name": "IRON WILL",
			"desc": "+2 MAX HEARTS\n−15% DAMAGE",
			"apply": _apply_iron_will,
			"conflicts": ["glass_cannon", "last_stand"],
		},
		{
			"id": "glass_cannon",
			"name": "GLASS CANNON",
			"desc": "−1 MAX HEART\n+60% DAMAGE",
			"apply": _apply_glass_cannon,
			"conflicts": ["iron_will"],
		},
		{
			"id": "bloodlust",
			"name": "BLOODLUST",
			"desc": "Killing an enemy\nheals 1 HP",
			"apply": _apply_bloodlust,
			"conflicts": [],
		},
		{
			"id": "ghost_blade",
			"name": "GHOST BLADE",
			"desc": "Regular atk: 0 dmg\nCharge atk ×6",
			"apply": _apply_ghost_blade,
			"conflicts": ["charge_master"],
		},
		{
			"id": "last_stand",
			"name": "LAST STAND",
			"desc": "Below 3 HP:\n+120% DAMAGE",
			"apply": _apply_last_stand,
			"conflicts": ["iron_will"],
		},
		{
			"id": "momentum",
			"name": "MOMENTUM",
			"desc": "+5% speed per kill\n(max +50%)",
			"apply": _apply_momentum,
			"conflicts": ["speed_boost"],
		},
		{
			"id": "double_strike",
			"name": "DOUBLE STRIKE",
			"desc": "After Dash:\nnext attack\ndeals 300% DMG",
			"apply": _apply_double_strike,
			"conflicts": [],
		},
		{
			"id": "cheat_death",
			"name": "CHEAT DEATH",
			"desc": "Once per run:\non death, revive\nat 20% HP &\n1s invincible",
			"apply": _apply_cheat_death,
			"conflicts": [],
		},
		{
			"id": "frenzy",
			"name": "FRENZY",
			"desc": "Each hit:\n+3% atk speed\n(max +60%)\nResets after 4s",
			"apply": _apply_frenzy,
			"conflicts": [],
		},
	]


## Returns up to `count` random buffs, filtered for coherence.
func get_random_buffs(count: int) -> Array[Dictionary]:
	var active   : Array[String] = PlayerManager.active_buff_ids
	var player_hp : int = PlayerManager.player.max_hp if PlayerManager.player else 6

	var available : Array[Dictionary] = []
	for b in _pool:
		if b.id in active:
			continue
		var skip := false
		for c in b.conflicts:
			if c in active:
				skip = true
				break
		if skip:
			continue
		if b.id == "glass_cannon" and player_hp <= 2:
			continue
		available.append(b)

	available.shuffle()
	var result : Array[Dictionary] = []
	for i in mini(count, available.size()):
		result.append(available[i])
	return result


# ─── apply functions ──────────────────────────────────────────────────────────

func _apply_big_damage() -> void:
	PlayerManager.damage_multiplier *= 1.5

func _apply_charge_master() -> void:
	PlayerManager.charge_attack_multiplier = max(PlayerManager.charge_attack_multiplier, 4.0)

func _apply_kill_stack() -> void:
	PlayerManager.kill_stack_buff_active = true
	PlayerManager.kill_stack_count = 0

func _apply_speed_boost() -> void:
	PlayerManager.speed_multiplier *= 1.4

func _apply_extra_dash() -> void:
	PlayerManager.dash_stacks_max += 1
	PlayerManager.dash_stacks = PlayerManager.dash_stacks_max

func _apply_ability_power() -> void:
	PlayerManager.ability_damage_multiplier *= 2.0

func _apply_iron_will() -> void:
	if PlayerManager.player:
		PlayerManager.player.max_hp += 4
		PlayerManager.player.hp += 4   # umple inimile noi (altfel ramaneau goale)
		PlayerManager.player.update_hp(0)
	PlayerManager.damage_multiplier *= 0.85

func _apply_glass_cannon() -> void:
	if PlayerManager.player:
		PlayerManager.player.max_hp = max(2, PlayerManager.player.max_hp - 2)
		PlayerManager.player.hp = mini(PlayerManager.player.hp, PlayerManager.player.max_hp)
		PlayerManager.player.update_hp(0)
	PlayerManager.damage_multiplier *= 1.6

func _apply_bloodlust() -> void:
	PlayerManager.bloodlust_active = true

func _apply_ghost_blade() -> void:
	PlayerManager.ghost_blade_active = true
	PlayerManager.charge_attack_multiplier = maxf(PlayerManager.charge_attack_multiplier * 3.0, 6.0)

func _apply_last_stand() -> void:
	PlayerManager.last_stand_active = true

func _apply_momentum() -> void:
	PlayerManager.momentum_active = true
	PlayerManager.momentum_stacks = 0

func _apply_double_strike() -> void:
	PlayerManager.double_strike_active = true

func _apply_cheat_death() -> void:
	PlayerManager.cheat_death_active = true
	PlayerManager.cheat_death_used = false

func _apply_frenzy() -> void:
	PlayerManager.frenzy_active = true
	PlayerManager.frenzy_stacks = 0
