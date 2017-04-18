from django import template

register = template.Library()

@register.filter
def fabricSum(tower):
    total = 0
    for shelf in tower.shelf_set.all():
        total += shelf.fabrics.count()
    
    return total