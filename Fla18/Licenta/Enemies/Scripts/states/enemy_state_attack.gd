class_name EnemyStateAttack extends EnemyState

@export var anim_name : String = "attack"
@export var next_state : EnemyState

var attack_finished : bool = false


func init() -> void:
	pass


func enter() -> void:
	attack_finished = false
	enemy.velocity = Vector2.ZERO
	if enemy is Orc:
		(enemy as Orc).start_attack()
	enemy.animation_player.animation_finished.connect(_on_anim_finished)
	pass


func exit() -> void:
	if enemy is Orc:
		(enemy as Orc).end_attack()
	if enemy.animation_player.animation_finished.is_connected(_on_anim_finished):
		enemy.animation_player.animation_finished.disconnect(_on_anim_finished)
	pass


func process(_delta: float) -> EnemyState:
	enemy.velocity = Vector2.ZERO
	if attack_finished:
		return next_state
	return null


func physics(_delta: float) -> EnemyState:
	return null


func _on_anim_finished(_anim_name: String) -> void:
	attack_finished = true
