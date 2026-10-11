from django.urls import path
from . import views


urlpatterns = [

    path(
        '',
        views.check_in_details_list,
        name='check_in_details_list'
    ),

     path(
        'add/',
        views.check_in_details_add,
        name='check_in_details_add'
    ),

    path(
        'save-check-in/',
        views.save_check_in_details,
        name='save_check_in_details'
    ),

    path(
        'update-check-in/',
        views.update_check_in_details,
        name='update_check_in_details'
    ),

    path(
        'load-check-in/',
        views.get_check_in_details,
        name='get_check_in_details'
    ),

    path(
        'delete-check-in/',
        views.remove_check_in_details,
        name='remove_check_in_details'
    ),

    path(
        'load-guests/',
        views.get_hotel_guests,
        name='get_hotel_guests'
    ),

    path(
        'guest-info/',
        views.get_guest_check_in_info,
        name='get_guest_check_in_info'
    ),

]