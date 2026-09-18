# Sageata trasa de capcana - zboara intr-o directie si da damage playerului
class_name TrapArrow extends Node2D

var direction : Vector2 = Vector2.RIGHT
var speed : float = 250.0
var damage : int = 2

@onready var hurt_box: HurtBox = $HurtBox
@onready var sprite: Sprite2D = $Sprite2D


func _ready() -> void:
	add_to_group("trap_arrows")
	hurt_box.did_damage.connect(_on_hit)
	# Distruge sagetea dupa 8 secunde (daca nu loveste nimic)
	get_tree().create_timer(8.0).timeout.connect(queue_free)


func start() -> void:
	hurt_box.damage = damage
	# Roteste sageata in directia miscarii
	sprite.rotation = direction.angle()
	hurt_box.rotation = direction.angle()


func _process(delta: float) -> void:
	position += direction * speed * delta


func _on_hit() -> void:
	# Sageata dispare dupa ce loveste
	queue_free()
