class_name ItemEffectBerserker extends ItemEffect

func use() -> void:
	PlayerManager.damage_multiplier += 0.4
	var p := PlayerManager.player
	# max_hp e in JUMATATI (6 = 3 inimi). -2 = -1 inima full.
	p.max_hp = max(2, p.max_hp - 2)
	p.hp = mini(p.hp, p.max_hp)   # daca aveai full HP, pierzi acel exces
	p.update_hp(0)
	p.update_damage_values()
