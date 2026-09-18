class_name DarkWizardBoss extends Node2D

const ENERGY_EXPLOSION_SCENE : PackedScene = preload( "res://Levels/Dungeon01/dark_wizard/energy_explosion.tscn" )
const ENERGY_BALL_SCENE      : PackedScene = preload( "res://Levels/Dungeon01/dark_wizard/energy_orb.tscn" )
const HURTBOX_SCENE          : PackedScene = preload( "res://GeneralNodes/HurtBox/hurt_box.tscn" )
const SKELETON_SCENE         : PackedScene = preload( "res://Enemies/skeleton/skeleton.tscn" )

@export var max_hp : int = 300
@export var debug_min_hp : int = 0
var hp : int = 300

var audio_hurt : AudioStream = preload("res://Levels/Dungeon01/dark_wizard/audio/boss_hurt.wav")
var audio_shoot : AudioStream = preload("res://Levels/Dungeon01/dark_wizard/audio/boss_fireball.wav")

var current_position : int = 0
var positions : Array[ Vector2 ]
var beam_attacks : Array[ BeamAttack ]

var _coverage_50_done  := false
var _coverage_25_done  := false
var _coverage_pending  := false

var _h_beam_indices : Array[int] = []
var _v_beam_indices : Array[int] = []

var _phase3_entered  := false
var _fight_start_ms  : int = 0
var _last_urgency    : int = 0
var _defeated        := false
var _run_ended       := false   # Run8b: player mort / run reset → opreste atacurile (fix respawn mort)

var _urgency_label : Label


@onready var animation_player: AnimationPlayer = $BossNode/AnimationPlayer
@onready var animation_player_damaged: AnimationPlayer = $BossNode/AnimationPlayer_Damaged
@onready var cloak_animation_player: AnimationPlayer = $BossNode/CloakSprite/AnimationPlayer

@onready var audio: AudioStreamPlayer2D = $BossNode/AudioStreamPlayer2D
@onready var boss_node: Node2D = $BossNode
@onready var persistent_data_handler: PersistentDataHandler = $PersistentDataHandler
@onready var hurt_box: HurtBox = $BossNode/HurtBox
@onready var hit_box: HitBox = $BossNode/HitBox

@onready var hand_01: Sprite2D = $BossNode/CloakSprite/Hand01
@onready var hand_02: Sprite2D = $BossNode/CloakSprite/Hand02
@onready var hand_01_up: Sprite2D = $BossNode/CloakSprite/Hand01_UP
@onready var hand_02_up: Sprite2D = $BossNode/CloakSprite/Hand02_UP
@onready var hand_01_side: Sprite2D = $BossNode/CloakSprite/Hand01_SIDE
@onready var hand_02_side: Sprite2D = $BossNode/CloakSprite/Hand02_SIDE
@onready var door_block: TileMapLayer = $"../DoorBlock"



func _ready() -> void:
	add_to_group("boss")
	persistent_data_handler.get_value()
	if persistent_data_handler.value == true:
		door_block.enabled = false
		queue_free()
		return

	hp = max_hp
	_fight_start_ms = Time.get_ticks_msec()
	PlayerHud.show_boss_health( "Dark Wizard" )
	hit_box.damaged.connect( damage_taken )
	# Run8b: cand playerul moare (run reset), opreste atacurile (coverage etc.) ca sa NU
	# omoare playerul re-spawnat in episodul urmator.
	PlayerManager.run_failed.connect( func(): _run_ended = true )
	
	for c in $PositionTargets.get_children():
		positions.append( c.global_position )
	$PositionTargets.visible = false
	
	for b in $BeamAttacks.get_children():
		beam_attacks.append( b )

	for i in beam_attacks.size():
		if absf( beam_attacks[i].rotation ) < 0.1:
			_h_beam_indices.append( i )
		else:
			_v_beam_indices.append( i )

	_setup_urgency_label()
	teleport( 0 )


func _setup_urgency_label() -> void:
	var canvas := CanvasLayer.new()
	canvas.layer = 80
	add_child( canvas )
	_urgency_label = Label.new()
	_urgency_label.set_anchors_preset( Control.PRESET_TOP_WIDE )
	_urgency_label.position = Vector2( 0, 6 )
	_urgency_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_urgency_label.add_theme_color_override( "font_color", Color( 1.0, 0.72, 0.1 ) )
	_urgency_label.add_theme_color_override( "font_outline_color", Color( 0, 0, 0, 1 ) )
	_urgency_label.add_theme_constant_override( "outline_size", 3 )
	_urgency_label.add_theme_font_size_override( "font_size", 14 )
	canvas.add_child( _urgency_label )


# Called every frame. 'delta' is the elapsed time since the previous frame.
func _process(delta: float) -> void:
	hand_01_up.position = hand_01.position
	hand_01_up.frame = hand_01.frame + 4
	hand_02_up.position = hand_02.position
	hand_02_up.frame = hand_02.frame + 4
	hand_01_side.position = hand_01.position
	hand_01_side.frame = hand_01.frame + 8
	hand_02_side.position = hand_02.position
	hand_02_side.frame = hand_02.frame + 12
	_update_urgency_label()


func _update_urgency_label() -> void:
	if not _urgency_label or hp < 1:
		return
	var elapsed := float( Time.get_ticks_msec() - _fight_start_ms ) / 1000.0
	if elapsed >= 40.0:
		_urgency_label.visible = false
		return
	_urgency_label.visible = true
	var next_t : float
	var msg : String
	if elapsed < 20.0:
		next_t = 20.0
		msg = "Enrages in %ds"
	elif elapsed < 30.0:
		next_t = 30.0
		msg = "RAGE in %ds"
	else:
		next_t = 40.0
		msg = "BERSERK in %ds"
	var remaining := ceili( next_t - elapsed )
	_urgency_label.text = msg % remaining
	if remaining <= 5:
		_urgency_label.add_theme_color_override( "font_color", Color( 1.0, 0.15, 0.1 ) )
		_urgency_label.modulate.a = 0.5 + 0.5 * sin( Time.get_ticks_msec() * 0.008 )
	else:
		_urgency_label.add_theme_color_override( "font_color", Color( 1.0, 0.72, 0.1 ) )
		_urgency_label.modulate.a = 1.0



func teleport( _location : int ) -> void:
	animation_player.play( "disappear" )
	enable_hit_boxes( false )
	_check_urgency_notifications()

	var in_phase2 := hp * 2 <= max_hp
	if in_phase2:
		PlayerManager.shake_camera( 1.0 )

	boss_node.global_position = positions[ _location ]
	current_position = _location
	update_animations()

	if _phase3_entered:
		await get_tree().create_timer( 0.25 ).timeout
		boss_node.modulate = Color( 0.65, 0.8, 1.0, 0.6 )
		idle()
		return

	await get_tree().create_timer( 0.7 / _get_urgency() if in_phase2 else 1.3 / _get_urgency() ).timeout
	boss_node.modulate = Color.WHITE
	animation_player.play( "appear" )
	await animation_player.animation_finished
	idle()


func _shoot_phase_orbs() -> void:
	if _defeated:
		return
	var count := 3 if hp * 2 <= max_hp else 1
	play_audio( audio_shoot )
	for i in count:
		var eb : Node2D = ENERGY_BALL_SCENE.instantiate()
		var offset_x := float(i - 1) * 52.0 if count > 1 else 0.0
		eb.global_position = boss_node.global_position + Vector2( offset_x, -34 )
		get_parent().add_child.call_deferred( eb )



func idle() -> void:
	enable_hit_boxes()

	if _coverage_pending:
		_coverage_pending = false
		await coverage_attack()
	else:
		if _get_urgency() < 2.0 and randf() <= float(hp) / float(max_hp):
			animation_player.play( "idle" )
			await animation_player.animation_finished
			if hp < 1:
				return

		animation_player.play( "cast_spell" )
		await _do_attack()

		# Pauza vulnerabila dupa atac — boss-ul ramane pe loc ca jucatorul sa aiba
		# fereastra sa-l loveasca inainte sa se teleporteze. Scaleaza invers cu urgency
		# (la urgency mare se misca mai rapid). Phase 3: pauza mai scurta.
		var post_atk : float = 0.4 if _phase3_entered else ( 0.7 / _get_urgency() )
		await get_tree().create_timer( post_atk ).timeout

	if hp < 1:
		return

	var _t : int = current_position
	while _t == current_position:
		_t = randi_range( 0, 3 )
	teleport( _t )
	pass


func _do_attack() -> void:
	var below_75 := hp <= int(max_hp * 0.50)   # Run8b: 0.75→0.50, ramane beam-only mai mult timp
	var in_phase2 := hp * 2 <= max_hp

	var attacks := ["beam"]
	if below_75:
		attacks.append_array( ["orb_burst", "barrage"] )
	if in_phase2:
		attacks.append( "ground_slam" )

	match attacks[ randi() % attacks.size() ]:
		"beam":
			await energy_beam_attack()
		"orb_burst":
			await orb_burst_attack()
		"barrage":
			await barrage_attack()
		"ground_slam":
			await ground_slam_attack()


func update_animations() -> void:
	boss_node.scale = Vector2( 1, 1 )
	
	hand_01.visible = false
	hand_02.visible = false
	hand_01_up.visible = false
	hand_02_up.visible = false
	hand_01_side.visible = false
	hand_02_side.visible = false
	
	if current_position == 0:
		cloak_animation_player.play( "down" )
		hand_01.visible = true
		hand_02.visible = true
	elif current_position == 2:
		cloak_animation_player.play( "up" )
		hand_01_up.visible = true
		hand_02_up.visible = true
	else:
		cloak_animation_player.play( "side" )
		hand_01_side.visible = true
		hand_02_side.visible = true
		if current_position == 1:
			boss_node.scale = Vector2( -1, 1 )
	pass



func _beam_dist_to_player( idx : int ) -> float:
	var beam := beam_attacks[ idx ]
	var player_pos := PlayerManager.player.global_position
	if absf( beam.rotation ) < 0.1:
		return absf( beam.global_position.y - player_pos.y )
	else:
		return absf( beam.global_position.x - player_pos.x )


func energy_beam_attack() -> void:
	if not PlayerManager.player:
		return

	var in_phase2 := hp * 2 <= max_hp
	var below_75  := hp <= int( max_hp * 0.75 )
	var urgency      := _get_urgency()
	var base_count   := 7 if in_phase2 else ( 5 if below_75 else 3 )
	var urgency_bonus := 0
	if urgency >= 3.0:   urgency_bonus = 6
	elif urgency >= 2.0: urgency_bonus = 4
	elif urgency >= 1.5: urgency_bonus = 2
	var count := mini( base_count + urgency_bonus, beam_attacks.size() )

	var sorted_indices : Array = range( beam_attacks.size() )
	sorted_indices.sort_custom( func( a, b ):
		return _beam_dist_to_player( a ) < _beam_dist_to_player( b )
	)

	var _b : Array[ int ] = []
	for i in mini( count, sorted_indices.size() ):
		_b.append( sorted_indices[ i ] )

	if below_75:
		var spd := minf( 1.5 * urgency, 3.5 )
		var i := 0
		while i < _b.size():
			var group_end := mini( i + 3, _b.size() )
			for j in range( i, group_end - 1 ):
				beam_attacks[ _b[ j ] ].attack( spd )
			await beam_attacks[ _b[ group_end - 1 ] ].attack( spd )
			i = group_end
	else:
		var spd := minf( urgency, 3.0 )
		for i in _b.size() - 1:
			beam_attacks[ _b[ i ] ].attack( spd )
		await beam_attacks[ _b[ -1 ] ].attack( spd )


func orb_burst_attack() -> void:
	var waves := 3 if hp * 2 <= max_hp else 2
	var count := 8
	for w in waves:
		if _defeated:
			return
		play_audio( audio_shoot )
		var offset := ( TAU / count / 2.0 ) * w
		for i in count:
			var angle := ( TAU / count ) * i + offset
			var eb : EnergyOrb = ENERGY_BALL_SCENE.instantiate()
			eb.custom_direction = Vector2.from_angle( angle )
			eb.global_position = boss_node.global_position + Vector2( 0, -34 )
			get_parent().add_child.call_deferred( eb )
		await get_tree().create_timer( 0.55 ).timeout


func barrage_attack() -> void:
	if not PlayerManager.player:
		return
	for _wave in 3:
		if _defeated:
			return
		play_audio( audio_shoot )
		var to_player := ( PlayerManager.player.global_position - boss_node.global_position ).normalized()
		for i in 3:
			var spread := deg_to_rad( ( i - 1 ) * 20.0 )
			var eb : EnergyOrb = ENERGY_BALL_SCENE.instantiate()
			eb.custom_direction = to_player.rotated( spread )
			if _phase3_entered:
				eb.homing = true
				eb.homing_duration = 2.2
			eb.global_position = boss_node.global_position + Vector2( 0, -34 )
			get_parent().add_child.call_deferred( eb )
		await get_tree().create_timer( 0.35 ).timeout


func ground_slam_attack() -> void:
	if not PlayerManager.player:
		return
	var target := PlayerManager.player.global_position

	var warning := _make_circle( target, 28.0, Color( 1.0, 0.2, 0.1, 0.55 ) )
	get_parent().add_child( warning )
	PlayerManager.shake_camera( 0.4 )
	await get_tree().create_timer( 0.75 ).timeout
	warning.queue_free()

	if hp < 1 or _defeated:
		return
	var e : Node2D = ENERGY_EXPLOSION_SCENE.instantiate()
	e.global_position = target
	get_parent().add_child.call_deferred( e )

	var hb_host := Node2D.new()
	hb_host.global_position = target
	var hb := HURTBOX_SCENE.instantiate() as HurtBox
	hb.damage = 3
	var shape := CollisionShape2D.new()
	var circle := CircleShape2D.new()
	circle.radius = 32.0
	shape.shape = circle
	hb.add_child( shape )
	hb_host.add_child( hb )
	get_parent().add_child( hb_host )
	await get_tree().create_timer( 0.5 ).timeout
	hb_host.queue_free()


func _make_circle( pos : Vector2, radius : float, color : Color ) -> Polygon2D:
	var poly := Polygon2D.new()
	var pts  := PackedVector2Array()
	for i in 24:
		var a := TAU * i / 24
		pts.append( Vector2( cos(a), sin(a) ) * radius )
	poly.polygon = pts
	poly.color   = color
	poly.global_position = pos
	return poly


func coverage_attack() -> void:
	animation_player.play( "disappear" )
	enable_hit_boxes( false )
	await get_tree().create_timer( 0.6 ).timeout
	boss_node.global_position = positions[ 0 ]
	current_position = 0
	update_animations()
	animation_player.play( "appear" )
	await animation_player.animation_finished

	# Damage in coverage_attack e EXCLUSIV position-based (vezi loop-ul cu dummy_hb).
	# Hurtbox-urile beam-urilor sunt visual-only. Animatia "attack" are keyframe la t=2.0
	# care reactiveaza HurtBox:monitoring → fara damage=0 pe toate, beam-urile vecine
	# (spacing 32px in zona V6/V1/V11/V7) loveau jucatorul prin overlap chiar daca era
	# fix in centrul safe circle (radius 42px > spacing 32px).
	for beam in beam_attacks:
		beam.cancel_attack()
		var hb := beam.get_node_or_null( "HurtBox" ) as HurtBox
		if hb:
			hb.monitoring = false
			hb.damage = 0

	var used_h : Array[int] = []
	var used_v : Array[int] = []

	PlayerManager.coverage_attack_active = true

	var canvas_layer := CanvasLayer.new()
	canvas_layer.layer = 90
	get_parent().add_child( canvas_layer )
	var arrow := _make_safe_arrow( canvas_layer )

	# Min distanta intre safe_pos si boss — boss-ul sta la positions[0] tot atacul,
	# daca safe_pos cade aproape de el playerul nu poate intra (collider boss + hitbox).
	# 60px = safe_radius (42) + buffer pentru boss collider.
	const SAFE_MIN_DIST_FROM_BOSS : float = 60.0
	# Run9: 4 SAFE ZONES simultane in loc de 1 — AI-ul nu apuca sa gaseasca singura zona.
	# Plasate SPREAD (departe una de alta + departe de boss) ca sa fie MEREU una aproape.
	# Damage ramane EXCLUSIV position-based: safe daca esti in raza ORICAREI zone verzi.
	const N_SAFE_ZONES : int   = 4
	const MIN_ZONE_SEP : float = 200.0   # separare dorita intre zone (relaxata daca nu incap)
	const SAFE_RADIUS  : float = 48.0    # raza safe (42→48, putin mai iertator cu 4 zone)

	# 1) Toate intersectiile valide (gap_orizontal × gap_vertical), departe de boss
	var candidates : Array = []
	for hi in _h_beam_indices:
		for vi in _v_beam_indices:
			var cpos := Vector2(
				beam_attacks[ vi ].global_position.x,
				beam_attacks[ hi ].global_position.y
			)
			if cpos.distance_to( boss_node.global_position ) >= SAFE_MIN_DIST_FROM_BOSS:
				candidates.append( { "pos": cpos, "h": hi, "v": vi } )
	candidates.shuffle()

	# 2) Alege N zone SPREAD (greedy): fiecare pe rand/coloana distincta + departe de cele alese.
	#    Daca nu gaseste destule la separarea ceruta, o relaxeaza treptat.
	var safe_zones : Array = []
	var sep := MIN_ZONE_SEP
	while safe_zones.size() < N_SAFE_ZONES and sep > 30.0:
		for c in candidates:
			if safe_zones.size() >= N_SAFE_ZONES:
				break
			if (c["h"] in used_h) or (c["v"] in used_v):
				continue
			var ok := true
			for z in safe_zones:
				if z.distance_to( c["pos"] ) < sep:
					ok = false
					break
			if ok:
				safe_zones.append( c["pos"] )
				used_h.append( c["h"] )
				used_v.append( c["v"] )
		sep -= 40.0
	if safe_zones.is_empty():
		safe_zones.append( boss_node.global_position + Vector2( 0, 150 ) )

	PlayerManager.coverage_safe_positions = safe_zones
	PlayerManager.coverage_safe_pos = safe_zones[ 0 ]

	# 3) Un cerc verde la fiecare zona safe
	var indicators : Array = []
	for z in safe_zones:
		var ind := _make_circle( z, 38.0, Color( 0.1, 1.0, 0.1, 0.65 ) )
		get_parent().add_child( ind )
		indicators.append( ind )

	# 4) Beam-urile care nu trec prin nicio zona safe se aprind rosu (gap vizual la fiecare zona)
	for i in range( beam_attacks.size() ):
		if (i in used_h) or (i in used_v):
			continue
		beam_attacks[ i ].modulate = Color( 1.5, 0.1, 0.1, 1.0 )

	# 5) Avertizare 3s — sageata catre cea mai apropiata zona (se actualizeaza in timp real)
	var warn_start := Time.get_ticks_msec()
	while Time.get_ticks_msec() - warn_start < 3000:
		if _defeated:
			break
		PlayerManager.coverage_safe_pos = _nearest_safe_zone( safe_zones )
		_update_safe_arrow( arrow, PlayerManager.coverage_safe_pos )
		await get_tree().process_frame
	arrow.visible = false

	if hp < 1 or _defeated or _run_ended:
		_reset_coverage_beams()
		PlayerManager.coverage_safe = false
		PlayerManager.coverage_attack_active = false
		PlayerManager.coverage_safe_pos = Vector2.ZERO
		PlayerManager.coverage_safe_positions = []
		for ind in indicators:
			ind.queue_free()
		canvas_layer.queue_free()
		return

	# Beams fire visual-only (damage e position-based mai jos)
	for i in range( beam_attacks.size() ):
		if (i in used_h) or (i in used_v):
			continue
		beam_attacks[ i ].attack( 1.0 )

	await get_tree().create_timer( 2.0 ).timeout   # charge-up 2s, fara damage

	if hp < 1 or _defeated or _run_ended:
		_reset_coverage_beams()
		PlayerManager.coverage_safe = false
		PlayerManager.coverage_safe_positions = []
		for ind in indicators:
			ind.queue_free()
		canvas_layer.queue_free()
		return

	var dummy_hb := HURTBOX_SCENE.instantiate() as HurtBox
	dummy_hb.damage = 99   # instakill INTENTIONAT — player trebuie sa stea pe o zona verde (dodge)
	add_child( dummy_hb )

	# Damage 1.7s: safe daca e in raza ORICAREI zone verzi (cea mai apropiata)
	var beam_end := Time.get_ticks_msec() + 1700
	while Time.get_ticks_msec() < beam_end:
		if _defeated or _run_ended:
			break
		if PlayerManager.player and is_instance_valid( PlayerManager.player ):
			if PlayerManager.player.hp <= 0:
				break   # player mort → nu mai aplica damage (altfel omoara si respawn-ul)
			var nz := _nearest_safe_zone( safe_zones )
			var dist := PlayerManager.player.global_position.distance_to( nz )
			PlayerManager.coverage_safe = dist <= SAFE_RADIUS
			PlayerManager.coverage_safe_pos = nz   # reward dodge trage spre cea mai apropiata
			if not PlayerManager.coverage_safe and not PlayerManager.player.invulnerable:
				PlayerManager.player._take_damage( dummy_hb )
		await get_tree().process_frame
	PlayerManager.coverage_safe = false
	dummy_hb.queue_free()

	_reset_coverage_beams()
	for ind in indicators:
		ind.queue_free()

	canvas_layer.queue_free()
	PlayerManager.coverage_attack_active = false
	PlayerManager.coverage_safe_pos = Vector2.ZERO
	PlayerManager.coverage_safe_positions = []

	if _coverage_25_done and not _phase3_entered and hp > 0:
		_phase3_entered = true
		PlayerHud.queue_notification( "Dark Wizard", "The wizard transcends reality!" )


func _nearest_safe_zone( zones: Array ) -> Vector2:
	# Run9: cea mai apropiata zona safe de player (pt sageata, damage check si reward dodge)
	if zones.is_empty():
		return Vector2.ZERO
	var p := PlayerManager.player
	if not p or not is_instance_valid( p ):
		return zones[ 0 ]
	var best : Vector2 = zones[ 0 ]
	var best_d := INF
	for z in zones:
		var d : float = p.global_position.distance_to( z )
		if d < best_d:
			best_d = d
			best = z
	return best


func _make_safe_arrow( canvas: CanvasLayer ) -> Polygon2D:
	var arrow := Polygon2D.new()
	arrow.polygon = PackedVector2Array([
		Vector2( 0, -18 ),
		Vector2( -13, 13 ),
		Vector2( 13, 13 ),
	])
	arrow.color = Color( 0.1, 1.0, 0.1, 0.95 )
	arrow.visible = false
	canvas.add_child( arrow )
	return arrow


func _update_safe_arrow( arrow: Polygon2D, world_pos: Vector2 ) -> void:
	if not is_instance_valid( arrow ):
		return
	var camera := get_viewport().get_camera_2d()
	if not camera:
		arrow.visible = false
		return
	var vp_size   := get_viewport().get_visible_rect().size
	var center    := vp_size * 0.5
	var screen_pos := center + ( world_pos - camera.get_screen_center_position() )
	var margin    := 48.0
	var in_bounds := ( screen_pos.x >= margin and screen_pos.x <= vp_size.x - margin and
					   screen_pos.y >= margin and screen_pos.y <= vp_size.y - margin )
	arrow.visible = not in_bounds
	if not in_bounds:
		var dir := ( screen_pos - center ).normalized()
		arrow.rotation = dir.angle() + PI * 0.5
		arrow.position = Vector2(
			clampf( screen_pos.x, margin, vp_size.x - margin ),
			clampf( screen_pos.y, margin, vp_size.y - margin )
		)


func _reset_coverage_beams() -> void:
	PlayerManager.coverage_safe = false
	for i in range( beam_attacks.size() ):
		beam_attacks[ i ].cancel_attack()
		beam_attacks[ i ].modulate = Color.WHITE
		var hb := beam_attacks[ i ].get_node_or_null( "HurtBox" ) as HurtBox
		if hb:
			hb.damage = 3
			hb.monitoring = false



func shoot_orb() -> void:
	if _defeated:
		return
	var eb : Node2D = ENERGY_BALL_SCENE.instantiate()
	eb.global_position = boss_node.global_position + Vector2( 0, -34 )
	get_parent().add_child.call_deferred( eb )
	play_audio( audio_shoot )



func damage_taken( _hurt_box : HurtBox ) -> void:
	# Permite re-damage daca animatia damaged a trecut de 0.15s (nu blocheaza tot ciclul)
	if _hurt_box.damage == 0:
		return
	if animation_player_damaged.current_animation == "damaged" and animation_player_damaged.current_animation_position < 0.15:
		return
	play_audio( audio_hurt )
	hp = clampi( hp - _hurt_box.damage, debug_min_hp, max_hp )
	PlayerHud.update_boss_health( hp, max_hp )
	animation_player_damaged.play( "damaged" )
	animation_player_damaged.seek( 0 )
	animation_player_damaged.queue( "default" )
	_flash_damage_screen()

	if not _coverage_50_done and hp <= max_hp / 2 and hp > 0:
		_coverage_50_done = true
		_coverage_pending = true
	elif not _coverage_25_done and hp <= max_hp / 4 and hp > 0:
		_coverage_25_done = true
		_coverage_pending = true

	if hp < 1:
		defeat()


func play_audio( _a : AudioStream ) -> void:
	audio.stream = _a
	audio.play()



func defeat() -> void:
	_defeated = true
	_reset_coverage_beams()
	if _urgency_label:
		_urgency_label.visible = false
	boss_node.modulate = Color.WHITE
	animation_player.play( "destroy" )
	enable_hit_boxes( false )
	PlayerHud.hide_boss_health()
	await animation_player.animation_finished
	$ItemDropper.position = boss_node.position
	$ItemDropper.drop_item()
	$ItemDropper.drop_collected.connect( open_dungeon )


func open_dungeon() -> void:
	persistent_data_handler.set_value()
	door_block.enabled = false
	PlayerManager.run_completed.emit( PlayerHud.quest_time )


func _get_urgency() -> float:
	# Run8b: mai BLAND pt AI — baza mai lenta (0.8 = atacuri mai rare) + escaladare mult mai
	# lenta, cap jos (1.5 in loc de 3.0). Boss-ul nu mai devine coplesitor de repede.
	var elapsed := float( Time.get_ticks_msec() - _fight_start_ms ) / 1000.0
	if elapsed > 120.0: return 1.5
	if elapsed > 70.0:  return 1.2
	return 0.8


func _check_urgency_notifications() -> void:
	var elapsed := float( Time.get_ticks_msec() - _fight_start_ms ) / 1000.0
	var level := 0
	if elapsed > 40.0:   level = 3
	elif elapsed > 30.0: level = 2
	elif elapsed > 20.0: level = 1
	if level > _last_urgency:
		_last_urgency = level
		match level:
			1: PlayerHud.queue_notification( "Dark Wizard", "The wizard grows impatient!" )
			2: PlayerHud.queue_notification( "Dark Wizard", "ENRAGED!" )
			3: PlayerHud.queue_notification( "Dark Wizard", "UNSTOPPABLE!" )
		_spawn_urgency_skeletons()


func _spawn_urgency_skeletons() -> void:
	# Run8b: DEZACTIVAT — fara inamici suplimentari cand boss-ul se enerveaza (prea greu pt AI).
	return


func _flash_damage_screen() -> void:
	var canvas := CanvasLayer.new()
	canvas.layer = 95
	get_parent().add_child( canvas )
	var rect := ColorRect.new()
	rect.color = Color( 1.0, 0.1, 0.05, 0.38 )
	rect.set_anchors_preset( Control.PRESET_FULL_RECT )
	canvas.add_child( rect )
	var tween := create_tween()
	tween.tween_property( rect, "color", Color( 1.0, 0.1, 0.05, 0.0 ), 0.28 )
	tween.chain().tween_callback( canvas.queue_free )



func enable_hit_boxes( _v : bool = true ) -> void:
	hit_box.set_deferred( "monitorable", _v )
	hurt_box.set_deferred( "monitoring", _v )


func explosion( _p : Vector2 = Vector2.ZERO ) -> void:
	var e : Node2D = ENERGY_EXPLOSION_SCENE.instantiate()
	e.global_position = boss_node.global_position + _p
	get_parent().add_child.call_deferred( e )
	pass
