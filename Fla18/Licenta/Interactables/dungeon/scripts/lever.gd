class_name Lever extends Node2D

signal lever_activated

# Each lever occupies a 2x2 tile block (32x32px total).
# 5 states, each 2 cols wide in the atlas (cols 0-9 of rows 9-10):
#   state 0 (left-down)  : atlas cols 0-1  <- default placed state
#   state 2 (neutral)    : atlas cols 4-5
#   state 4 (right-down) : atlas cols 8-9  <- activated state
const SOURCE_ID := 0

@export var tilemap: TileMapLayer
@export var tile_pos: Vector2i   # top-left tile of the 2x2 block

const LEVER_SFX := preload("res://Interactables/dungeon/lever-01.wav")

@onready var hit_box: HitBox = $HitBox
@onready var audio: AudioStreamPlayer2D = $Audio

var is_activated: bool = false

func _ready() -> void:
	audio.stream = LEVER_SFX
	hit_box.damaged.connect(_on_hit)
	if not tilemap:
		tilemap = get_parent().get_node_or_null("LevelTileMapLayer2") as TileMapLayer

func _on_hit(_hurt_box: HurtBox) -> void:
	if is_activated:
		return
	is_activated = true
	audio.play()
	_animate_activation()

func _animate_activation() -> void:
	var tween := create_tween()
	tween.tween_callback(func(): _set_cols(4))  # snap to neutral mid-swing
	tween.tween_interval(0.1)
	tween.tween_callback(func(): _set_cols(8))  # land on right-down
	tween.tween_interval(0.08)
	tween.tween_callback(lever_activated.emit)

func _set_cols(col: int) -> void:
	if not tilemap:
		return
	tilemap.set_cell(tile_pos,                    SOURCE_ID, Vector2i(col,     9))
	tilemap.set_cell(tile_pos + Vector2i(1, 0),   SOURCE_ID, Vector2i(col + 1, 9))
	tilemap.set_cell(tile_pos + Vector2i(0, 1),   SOURCE_ID, Vector2i(col,     10))
	tilemap.set_cell(tile_pos + Vector2i(1, 1),   SOURCE_ID, Vector2i(col + 1, 10))
