extends Node

signal level_load_started
signal level_loaded
signal tilemap_bounds_changed( bounds : Array[ Vector2 ] )

var current_tilemap_bounds : Array[ Vector2 ]
var target_transition : String
var position_offset : Vector2
var previous_scene_path : String = ""


func _ready() -> void:
	await get_tree().process_frame
	level_loaded.emit()
	PlayerManager.run_completed.connect( func(_t): previous_scene_path = "" )
	PlayerManager.run_failed.connect(    func():   previous_scene_path = "" )



func change_tilemap_bounds( bounds : Array[ Vector2 ] ) -> void:
	current_tilemap_bounds = bounds
	tilemap_bounds_changed.emit( bounds )


func load_new_level(
		level_path : String,
		_target_transition : String,
		_position_offset : Vector2,
		reset_previous : bool = false
) -> void:

	get_tree().paused = true
	target_transition = _target_transition
	position_offset = _position_offset

	if reset_previous:
		previous_scene_path = ""
	else:
		var cur := get_tree().current_scene
		previous_scene_path = cur.scene_file_path if cur else ""

	await SceneTransition.fade_out()
	
	level_load_started.emit()
	
	await get_tree().process_frame
	
	get_tree().change_scene_to_file( level_path )
	
	await SceneTransition.fade_in()
	
	get_tree().paused = false

	await get_tree().process_frame

	# Fix vizual: curata orice obiect agatat (vaza) ramas pe player de la o aruncare/tranzitie
	# intrerupta. Scenariu: ridica vaza -> arunca -> intra in shop INAINTE sa cada/sparga ->
	# vaza veche ramane in held_item -> urmatoarea ridicata pare lipita vizual pe cap.
	# La fiecare incarcare de nivel golim held_item (acolo se tin doar obiectele carate).
	if PlayerManager.player and is_instance_valid( PlayerManager.player ):
		var _hi = PlayerManager.player.held_item
		if _hi:
			for _c in _hi.get_children():
				_c.queue_free()

	level_loaded.emit()


	pass
