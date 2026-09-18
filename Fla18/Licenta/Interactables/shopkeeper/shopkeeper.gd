class_name Shopkeeper extends Node2D

signal shop_entered

@export var shop_inventory : Array[ ItemData ]

@onready var dialog_branch_yes: DialogBranch = $NPC/DialogInteraction/DialogChoice/DialogBranch
@onready var dialog_interaction: DialogInteraction = $NPC/DialogInteraction


func _ready() -> void:
	add_to_group("shopkeepers")
	dialog_branch_yes.selected.connect( show_shop_menu )
	# Run5j fix: dezactiveaza dialog complet dupa cumparare → AI nu mai poate initia chiar deloc
	ShopMenu.purchase_made.connect( _on_purchase_disable_dialog )
	PlayerManager.run_failed.connect( _enable_dialog )
	PlayerManager.run_completed.connect( func(_t): _enable_dialog() )
	pass


func show_shop_menu() -> void:
	# Run5j: daca a cumparat deja, nu mai deschide shop (safety)
	if not ShopMenu._purchased_items.is_empty():
		return
	shop_entered.emit()
	ShopMenu.show_menu( shop_inventory )
	pass


func _on_purchase_disable_dialog(_item_name: String) -> void:
	if is_instance_valid(dialog_interaction):
		dialog_interaction.enabled = false


func _enable_dialog() -> void:
	if is_instance_valid(dialog_interaction):
		dialog_interaction.enabled = true
