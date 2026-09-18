extends Node2D

@export var speed: float = 130.0
@export var damage: int = 6
@export var lifetime: float = 2.5

var direction: Vector2 = Vector2.RIGHT

@onready var hurt_box: HurtBox = $HurtBox
@onready var sprite: Sprite2D = $Sprite2D

const ANIM_COLS: int   = 9  # total columns in sheet
const ANIM_ROWS: int   = 4  # total rows (down/up/left/right)
const ANIM_STAGES: int = 4  # first 4 columns = projectile growth stages

var _timer: float = 0.0

func _ready() -> void:
	add_to_group("lich_projectiles")
	hurt_box.damage = damage
	hurt_box.area_entered.connect(_on_hit)
	sprite.hframes = ANIM_COLS
	sprite.vframes = ANIM_ROWS
	sprite.frame   = _direction_row() * ANIM_COLS + 0
	rotation = 0.0

func _process(delta: float) -> void:
	position += direction * speed * delta
	_timer += delta
	if _timer >= lifetime:
		queue_free()
	var stage := mini(int(_timer / (lifetime / ANIM_STAGES)), ANIM_STAGES - 1)
	sprite.frame = _direction_row() * ANIM_COLS + stage

func _direction_row() -> int:
	if abs(direction.y) >= abs(direction.x):
		return 0 if direction.y > 0 else 1   # 0=down, 1=up
	else:
		return 2 if direction.x < 0 else 3   # 2=left, 3=right

func _on_hit(_area: Area2D) -> void:
	queue_free()
