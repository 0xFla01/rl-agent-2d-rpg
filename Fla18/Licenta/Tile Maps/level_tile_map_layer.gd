class_name LevelTileMapLayer extends TileMapLayer

@export var tile_size : float = 32
@export var update_bounds : bool = true
## When true, manually creates StaticBody2D collision for tiles at negative cell-Y
## coordinates. Godot 4 TileMapLayer does not generate collision bodies for those
## cells, so decorations placed at the top of the map would otherwise be passable.
@export var fix_negative_y_collision : bool = false


# Called when the node enters the scene tree for the first time.
func _ready():
	if update_bounds:
		LevelManager.change_tilemap_bounds( _get_tilemap_bounds() )
	if fix_negative_y_collision:
		_apply_negative_y_collision_fix.call_deferred()
	pass # Replace with function body.


func _get_tilemap_bounds() -> Array[ Vector2 ]:
	var bounds : Array[ Vector2 ] = []
	bounds.append(
		Vector2( get_used_rect().position * tile_size ) + position
	)
	bounds.append(
		Vector2( get_used_rect().end * tile_size ) + position
	)
	return bounds


func _apply_negative_y_collision_fix() -> void:
	if not tile_set or tile_set.get_physics_layers_count() == 0:
		return

	var coll_layer : int = tile_set.get_physics_layer_collision_layer(0)

	for cell in get_used_cells():
		if cell.y >= 0:
			continue
		var data : TileData = get_cell_tile_data(cell)
		if not data:
			continue

		var poly_count : int = data.get_collision_polygons_count(0)
		# Skip tile-uri fara collision polygons definite (decoratii precum skull_king/bones).
		# Fallback la rect full-tile creeaza blocuri patrate dubioase peste sprite-uri mici.
		if poly_count == 0:
			continue

		var body := StaticBody2D.new()
		body.collision_layer = coll_layer
		body.collision_mask  = 0
		body.position        = map_to_local(cell)

		for i in range(poly_count):
			var pts  : PackedVector2Array = data.get_collision_polygon_points(0, i)
			var cpoly := CollisionPolygon2D.new()
			cpoly.polygon = pts
			body.add_child(cpoly)

		add_child(body)
