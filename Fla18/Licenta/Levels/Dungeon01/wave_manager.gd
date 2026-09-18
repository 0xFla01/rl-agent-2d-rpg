class_name WaveManager extends Node

const GOBLIN_SCENE   := preload("res://Enemies/goblin/goblin.tscn")
const ORC_SCENE      := preload("res://Enemies/orc/orc.tscn")
const LICH_SCENE     := preload("res://Enemies/lich/lich.tscn")
const SKELETON_SCENE := preload("res://Enemies/skeleton/skeleton.tscn")

const CORNER_POSITIONS: Array = [
	Vector2(128, -64),
	Vector2(490, -64),
	Vector2(128, 200),
	Vector2(490, 200),
]

# Skeletons spawn offset inward so they don't clip into the side walls
const SKELETON_OFFSETS: Array = [
	Vector2(32, 0),
	Vector2(-32, 0),
	Vector2(32, 0),
	Vector2(-32, 0),
]

@export var enemy_counter_path: NodePath = NodePath("../EnemyCounter")
@export var item_dropper_path: NodePath  = NodePath("../ItemDropper")

var _current_wave: int = 0
var _enemy_counter: EnemyCounter = null
var _item_dropper: Node = null


func _ready() -> void:
	_enemy_counter = get_node_or_null(enemy_counter_path) as EnemyCounter
	_item_dropper  = get_node_or_null(item_dropper_path)
	if _enemy_counter:
		_enemy_counter.enemies_defeated.connect(_on_wave_cleared)


func _on_wave_cleared() -> void:
	_current_wave += 1
	match _current_wave:
		1: _spawn_wave.call_deferred(GOBLIN_SCENE)
		2: _spawn_wave.call_deferred(ORC_SCENE)
		3: _spawn_lich_wave.call_deferred()
		_:
			if _item_dropper and _item_dropper.has_method("drop_item"):
				_item_dropper.call_deferred("drop_item")


func _spawn_wave(scene: PackedScene) -> void:
	for pos in CORNER_POSITIONS:
		var enemy := scene.instantiate()
		enemy.position = pos
		_enemy_counter.add_child(enemy)


func _spawn_lich_wave() -> void:
	# Run8: 4 -> 2 lich (user: prea multi inamici in D01/03). Colturile diagonale pt spread.
	# Lich-ul oricum poate spawna scheleti dinamic in combat (mecanica lui).
	var lich_positions: Array = [CORNER_POSITIONS[0], CORNER_POSITIONS[3]]
	for pos in lich_positions:
		var lich := LICH_SCENE.instantiate()
		lich.position = pos
		_enemy_counter.add_child(lich)
