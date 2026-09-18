class_name ItemEffectAddBombs extends ItemEffect

@export var amount: int = 10

func use() -> void:
	PlayerManager.player.bomb_count += amount
