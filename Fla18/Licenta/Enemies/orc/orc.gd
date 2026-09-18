class_name Orc extends Enemy

const DEATH_SFX := preload("res://Enemies/Slime/hit_00.wav")

@export var attack_damage : int = 2
@export var attack_cooldown : float = 1.5
@export var attack_range : float = 28.0

var attack_timer : float = 0.0
var is_attacking : bool = false

var _death_audio : AudioStreamPlayer2D


func _ready() -> void:
	super()
	_death_audio = AudioStreamPlayer2D.new()
	_death_audio.stream = DEATH_SFX
	_death_audio.volume_db = -4.0
	add_child(_death_audio)
	enemy_destroyed.connect(_play_death_sfx)


func _play_death_sfx(_hurt_box: HurtBox) -> void:
	_death_audio.play()


func _process(_delta: float) -> void:
	if attack_timer > 0:
		attack_timer -= _delta


func update_animation( state : String ) -> void:
	var anim_name : String = state + "_" + anim_direction()
	if animation_player and animation_player.has_animation(anim_name):
		animation_player.play(anim_name)


func anim_direction() -> String:
	if cardinal_direction == Vector2.DOWN:
		return "front"
	elif cardinal_direction == Vector2.UP:
		return "back"
	elif cardinal_direction == Vector2.LEFT:
		return "left"
	else:
		return "right"


func set_direction( _new_direction : Vector2 ) -> bool:
	direction = _new_direction
	if direction == Vector2.ZERO:
		return false
	
	var to_player : Vector2 = direction
	if player and is_instance_valid(player):
		to_player = (player.global_position - global_position).normalized()
	
	var new_dir : Vector2
	if abs(to_player.x) > abs(to_player.y):
		new_dir = Vector2.RIGHT if to_player.x > 0 else Vector2.LEFT
	else:
		new_dir = Vector2.DOWN if to_player.y > 0 else Vector2.UP
	
	if new_dir == cardinal_direction:
		return false
	
	cardinal_direction = new_dir
	direction_changed.emit( new_dir )
	sprite.scale.x = 1
	sprite.flip_h = false
	return true


func can_attack() -> bool:
	if attack_timer > 0 or is_attacking:
		return false
	if not player or player.hp <= 0:
		return false
	return global_position.distance_to(player.global_position) <= attack_range


func start_attack() -> void:
	is_attacking = true
	attack_timer = attack_cooldown
	update_animation("attack")
	if has_node("AttackHurtBox"):
		var hb = get_node("AttackHurtBox")
		hb.damage = attack_damage
		hb.monitoring = true


func end_attack() -> void:
	is_attacking = false
	if has_node("AttackHurtBox"):
		var hb = get_node("AttackHurtBox")
		hb.monitoring = false


func _take_damage( hurt_box : HurtBox ) -> void:
	if invulnerable == true:
		return
	hp -= hurt_box.damage
	PlayerManager.shake_camera()
	EffectManager.damage_text( hurt_box.damage, global_position + Vector2(0,-36) )
	if hp > 0:
		enemy_damaged.emit( hurt_box )
	else:
		enemy_destroyed.emit( hurt_box )
