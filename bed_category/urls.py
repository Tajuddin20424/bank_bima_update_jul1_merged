
from django.urls import path
from . import views


urlpatterns = [

    # Pages
    path(
        '',
        views.bed_category_list,
        name='bed_category_list'
    ),

    path(
        'add/',
        views.bed_category_add,
        name='bed_category_add'
    ),

    path(
        'edit/<int:id>/',
        views.bed_category_edit,
        name='bed_category_edit'
    ),

    # APIs
    path(
        'get/',
        views.get_bed_categories,
        name='get_bed_categories'
    ),

    path(
        'save/',
        views.save_bed_category,
        name='save_bed_category'
    ),

    path(
        'update/',
        views.update_bed_category,
        name='update_bed_category'
    ),

    path(
        'remove/',
        views.remove_bed_category,
        name='remove_bed_category'
    ),

]