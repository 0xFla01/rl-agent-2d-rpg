@tool
@icon( "res://npc/icons/npc.svg" )
class_name NPC extends CharacterBody2D

signal do_behavior_enabled

var state : String = "idle"
var direction : Vector2 = Vector2.DOWN
var direction_name : String = "down"
var do_behavior : bool = true
# Persistent flag — odata acceptat questul de la acest NPC in sesiunea curenta,
# nu se mai re-activeaza dialogul la moarte/reset. Previne AI spam la NPC.
var _quest_ever_taken : bool = false

@export var npc_resource : NPCResource : set = _set_npc_resource

@onready var animation: AnimationPlayer = $AnimationPlayer
@onready var sprite: Sprite2D = $Sprite2D


func _ready() -> void:
	setup_npc()
	if Engine.is_editor_hint():
		return
	add_to_group("npcs")
	gather_interactables()
	do_behavior_enabled.emit()
	_disable_dialog_if_quest_taken()
	QuestManager.quest_updated.connect(func(_q): _disable_dialog_if_quest_taken())
	PlayerManager.run_failed.connect(_on_run_reset)
	PlayerManager.run_completed.connect(func(_t): _on_run_reset())



func _physics_process( _delta: float ) -> void:
	move_and_slide()


func gather_interactables() -> void:
	for c in get_children():
		if c is DialogInteraction:
			c.player_interacted.connect( _on_player_interacted )
			c.finished.connect( _on_interaction_finished )



func _on_player_interacted() -> void:
	update_direction( PlayerManager.player.global_position )
	state = "idle"
	velocity = Vector2.ZERO
	update_animation()
	do_behavior = false
	pass



func _on_interaction_finished() -> void:
	state = "idle"
	update_animation()
	do_behavior = true
	do_behavior_enabled.emit()
	pass



func update_animation() -> void:
	animation.play( state + "_" + direction_name )



func update_direction( target_position : Vector2 ) -> void:
	direction = global_position.direction_to( target_position )
	update_direction_name()
	if direction_name == "side" and direction.x < 0:
		sprite.flip_h = true
	else:
		sprite.flip_h = false



func update_direction_name() -> void:
	var threshold : float = 0.45
	if direction.y < -threshold:
		direction_name = "up"
	elif direction.y > threshold:
		direction_name = "down"
	elif direction.x > threshold || direction.x < -threshold:
		direction_name = "side"



func _disable_dialog_if_quest_taken() -> void:
	# Exceptie: shopkeeper-ul ramane interactibil dupa quest (vinzator).
	# Folosim class check (Shopkeeper class_name) — `is_in_group` esueaza pentru
	# ca NPC._ready ruleaza inaintea Shopkeeper._ready (group setat dupa NPC).
	if get_parent() is Shopkeeper:
		return
	var quest_taken := QuestManager.get_quest_index_by_title("Defeat the Dark Wizard") != -1
	if quest_taken:
		_quest_ever_taken = true
	for c in get_children():
		if c is DialogInteraction:
			c.enabled = not quest_taken


func _on_run_reset() -> void:
	# Shopkeeper-ul ramane interactibil intotdeauna (vinzator).
	if get_parent() is Shopkeeper:
		for c in get_children():
			if c is DialogInteraction:
				c.enabled = true
		return
	# Pentru NPCuri normale: re-activeaza dialogul DOAR daca questul nu a fost
	# vreodata acceptat in sesiunea curenta. Previne AI spam la NPC dupa moarte.
	if _quest_ever_taken:
		return
	for c in get_children():
		if c is DialogInteraction:
			c.enabled = true


func setup_npc() -> void:
	if npc_resource:
		if sprite:
			sprite.texture = npc_resource.sprite
	pass



func _set_npc_resource( _npc : NPCResource ) -> void:
	npc_resource = _npc
	setup_npc()
