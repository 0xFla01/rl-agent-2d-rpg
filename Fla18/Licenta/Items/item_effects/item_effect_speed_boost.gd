class_name ItemEffectSpeedBoost extends ItemEffect

func use() -> void:
	PlayerManager.speed_multiplier *= 1.5
