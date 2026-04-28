from django import template
from django.utils.safestring import mark_safe
from projects.common_lib import get_folder_path_link

register = template.Library()


@register.simple_tag()
def get_folder_pathway(folder, project_id):
    return mark_safe(get_folder_path_link(folder, folder, project_id))

